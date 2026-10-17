import hashlib
import json
import logging
import uuid
from typing import Any, Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from ..config import settings
from ..schemas.documents import (
    AmendRecordsRequest,
    AmendRecordsResponse,
    ExtractionPreviewResponse,
    ConfirmImportRequest,
)
from ..schemas.inventory import InventoryItemCreate
from ..schemas.waste import WasteRecordCreate, StaffMealRecordCreate
from ..repositories.database import db
from . import inventory_service, waste_service

logger = logging.getLogger(__name__)


class DocumentExtractionUnavailable(Exception):
    pass


class DocumentExtractionError(Exception):
    pass


SUPPORTED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".csv": "text/csv",
    ".txt": "text/plain",
}

MODEL_BY_TARGET = {
    "waste_records": WasteRecordCreate,
    "staff_meal_records": StaffMealRecordCreate,
    "inventory_items": InventoryItemCreate,
}
TARGET_BY_HINT = {
    "waste": "waste_records",
    "staff_meals": "staff_meal_records",
    "inventory_items": "inventory_items",
}
EXAMPLE_COLLECTION_BY_TARGET = {
    "waste_records": ("waste_records", "date"),
    "staff_meal_records": ("staff_meal_records", "date"),
    "inventory_items": ("inventory_items", "updated_at"),
}
EXAMPLE_OMITTED_FIELDS = {
    "id",
    "restaurant_id",
    "source_document_id",
    "inventory_item_id",
    "ingredient_id",
    "supplier_id",
    "recipe_id",
    "created_at",
    "updated_at",
    "status",
}


def _generate_json(prompt: str, contents: list[Any]) -> dict[str, Any]:
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        raise DocumentExtractionUnavailable(
            "Gemini processing is not configured. Set GEMINI_API_KEY on the backend and try again."
        )
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=300_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = json.loads(response.text or "")
        if not isinstance(result, dict):
            raise ValueError("Gemini returned an invalid response.")
        return result
    except genai_errors.APIError as error:
        logger.warning("Gemini document request failed with HTTP %s.", error.code)
        if error.code == 503:
            raise DocumentExtractionUnavailable(
                "Gemini is temporarily unavailable (503). Your request was not processed; please try again shortly."
            ) from error
        raise DocumentExtractionError(
            f"Gemini could not process this request (HTTP {error.code}). Please try again."
        ) from error
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        logger.exception("Gemini returned an invalid document response.")
        raise DocumentExtractionError(
            "Gemini returned invalid data. Please try again."
        ) from error
    except Exception as error:
        logger.exception("Gemini document request failed.")
        raise DocumentExtractionError(
            "Gemini could not process this request. Please try again."
        ) from error


def hash_file_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _get_format_examples(
    restaurant_id: Optional[str], target: str, model: type
) -> list[dict[str, Any]]:
    if not restaurant_id:
        return []

    collection, date_field = EXAMPLE_COLLECTION_BY_TARGET[target]
    records = db.query_collection(
        f"restaurants/{restaurant_id}/{collection}",
        order_by=(date_field, "DESCENDING"),
        limit=5,
    )
    allowed_fields = set(model.model_fields)

    def remove_identifiers(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: remove_identifiers(item)
                for key, item in value.items()
                if key not in EXAMPLE_OMITTED_FIELDS
            }
        if isinstance(value, list):
            return [remove_identifiers(item) for item in value]
        return value

    return [
        {
            key: remove_identifiers(value)
            for key, value in record.items()
            if key in allowed_fields
            and key not in EXAMPLE_OMITTED_FIELDS
            and value is not None
            and value != ""
        }
        for record in records
    ]


def extract_document_records(
    content: bytes, filename: str, hint: str, restaurant_id: Optional[str] = None
) -> tuple[list[dict[str, Any]], float, list[str]]:
    mime_type = SUPPORTED_MIME_TYPES.get("." + filename.rsplit(".", 1)[-1].lower())
    if not mime_type:
        raise ValueError("Supported files are PDF, JPG, PNG, CSV, and TXT.")

    target = TARGET_BY_HINT.get(hint)
    if target is None:
        raise ValueError(f"Unsupported document type: {hint}")
    model = MODEL_BY_TARGET[target]
    schema = model.model_json_schema()
    required_fields = schema.get("required", [])
    if target == "inventory_items":
        required_fields = [*required_fields, "unit_cost_inr or unit_cost"]
    format_examples = _get_format_examples(restaurant_id, target, model)

    prompt = f"""
Extract records from the attached restaurant document for the {target} table.
Map source column headings and labels to the closest matching canonical field names
in this JSON schema: {json.dumps(schema)}.
Source documents can use different names or contain fewer columns than the target
table. Match by meaning (for example, qty/amount to quantity, UOM to unit, item or
ingredient to item_name/ingredient_name). Return only fields supported by the schema.
For missing target fields, omit the value and list the canonical field name in
ambiguous_fields. Never invent missing values or add columns that are not in the schema.
Required fields are {json.dumps(required_fields)}. Return only a JSON object with:
- extracted_records: an array of record objects matching the schema
- confidence_score: a number from 0 to 1 representing extraction confidence
- ambiguous_fields: an array of strings describing unclear or missing values that need human review

Do not invent values. Omit fields that are absent or unreadable and list them in ambiguous_fields.
If no relevant records are present, return an empty extracted_records array and explain why in ambiguous_fields.

Existing records from this restaurant (format examples only; do not copy their
record-specific values) are:
{json.dumps(format_examples, ensure_ascii=False)}
When examples are available, follow their formatting for dates, units, category
labels, capitalization, and other repeated field values where the document's
meaning matches. Keep the schema's canonical field names. Do not copy identifiers
or generated metadata from examples, and do not force an example value when the
document contains different information.
"""

    try:
        result = _generate_json(prompt, [
            prompt,
            types.Part.from_bytes(data=content, mime_type=mime_type),
        ])
        records = result["extracted_records"]
        confidence = result["confidence_score"]
        ambiguous_fields = result["ambiguous_fields"]
        if (
            not isinstance(records, list)
            or any(not isinstance(record, dict) for record in records)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
            or not isinstance(ambiguous_fields, list)
            or any(not isinstance(field, str) for field in ambiguous_fields)
        ):
            raise ValueError("Gemini returned an invalid extraction response.")
        allowed_fields = set(model.model_fields)
        normalized_records = []
        for index, record in enumerate(records, start=1):
            unknown_fields = set(record) - allowed_fields
            if unknown_fields:
                ambiguous_fields.append(
                    f"Row {index}: unmapped fields were excluded: {', '.join(sorted(unknown_fields))}."
                )
            normalized_records.append({
                key: value for key, value in record.items() if key in allowed_fields
            })
        return normalized_records, float(confidence), ambiguous_fields
    except (KeyError, TypeError, ValueError) as error:
        logger.exception("Document extraction returned an invalid response.")
        raise DocumentExtractionError(
            "The document was uploaded, but extraction returned invalid data. Please try again."
        ) from error


def amend_document_records(request: AmendRecordsRequest) -> AmendRecordsResponse:
    model = MODEL_BY_TARGET.get(request.target_entity)
    if model is None:
        raise ValueError(f"Unsupported import target: {request.target_entity}")
    if not request.current_records:
        raise ValueError("Add or extract at least one row before requesting an amendment.")
    schema = model.model_json_schema()
    prompt = f"""
The customer is reviewing extracted data for the {request.target_entity} table.
The canonical fields and types are defined by this JSON schema: {json.dumps(schema)}.
Apply the customer's requested amendment to the current records below.
Preserve all existing values not explicitly changed. Map amendment terms to the
closest canonical schema fields. Do not invent values; if a request cannot be
fulfilled from the supplied data, leave the relevant value unchanged and explain
that in message. You may add, remove, or change rows only when the customer asks.
Return only JSON with updated_records (array of objects using schema fields) and
message (briefly describe what changed).

Current records:
{json.dumps(request.current_records, ensure_ascii=False)}

Customer amendment:
{request.amendment}
"""
    result = _generate_json(prompt, [prompt])
    updated_records = result.get("updated_records")
    message = result.get("message")
    if (
        not isinstance(updated_records, list)
        or len(updated_records) > 100
        or any(not isinstance(record, dict) for record in updated_records)
        or not isinstance(message, str)
    ):
        raise DocumentExtractionError("Gemini returned invalid amended data. Please try again.")
    allowed_fields = set(model.model_fields)
    if any(set(record) - allowed_fields for record in updated_records):
        raise DocumentExtractionError(
            "Gemini returned fields that do not belong to the selected table. Please retry the amendment."
        )
    return AmendRecordsResponse(updated_records=updated_records, message=message)


def process_document_upload(
    content: bytes,
    filename: str,
    hint: Optional[str] = None,
    restaurant_id: str = "taiken_kharadi",
) -> ExtractionPreviewResponse:
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    file_hash = hash_file_content(content)
    collection_path = f"restaurants/{restaurant_id}/documents"
    existing_docs = db.get_collection(collection_path)
    is_duplicate = any(d.get("hash") == file_hash for d in existing_docs)
    db.add_document(collection_path, doc_id, {
        "id": doc_id,
        "filename": filename,
        "hash": file_hash,
        "status": "processing"
    })

    try:
        records, confidence, ambiguous_fields = extract_document_records(
            content, filename, hint or "waste", restaurant_id
        )
    except (DocumentExtractionUnavailable, DocumentExtractionError):
        db.add_document(collection_path, doc_id, {
            "id": doc_id,
            "filename": filename,
            "hash": file_hash,
            "status": "extraction_failed",
        })
        raise

    message = (
        f"Extracted {len(records)} record(s). Review the fields and confirm to import."
        if records
        else "No records could be extracted. Review the document and try again."
    )
    db.add_document(collection_path, doc_id, {
        "id": doc_id,
        "filename": filename,
        "hash": file_hash,
        "status": "extracted",
    })
    return ExtractionPreviewResponse(
        document_id=doc_id,
        document_type_hint=hint or "waste",
        available_fields=list(
            MODEL_BY_TARGET[TARGET_BY_HINT[hint or "waste"]].model_fields
        ),
        extracted_records=records,
        confidence_score=confidence,
        ambiguous_fields=ambiguous_fields,
        duplicate_warning=is_duplicate,
        message=message,
    )

def confirm_document_import(restaurant_id: str, request: ConfirmImportRequest) -> int:
    model = MODEL_BY_TARGET.get(request.target_entity)
    if model is None:
        raise ValueError(f"Unsupported import target: {request.target_entity}")
    records = [model(**record) for record in request.confirmed_records]
    if request.target_entity == "waste_records":
        for record in records:
            waste_service.log_waste_record(restaurant_id, record)
    elif request.target_entity == "staff_meal_records":
        for record in records:
            waste_service.log_staff_meal(restaurant_id, record)
    else:
        for record in records:
            inventory_service.create_inventory_item(restaurant_id, record)
    return len(records)
