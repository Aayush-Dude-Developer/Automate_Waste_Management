import uuid
import hashlib
from ..schemas.documents import ExtractionPreviewResponse, ConfirmImportRequest
from ..schemas.inventory import InventoryItemCreate
from ..schemas.waste import WasteRecordCreate, StaffMealRecordCreate
from ..repositories.database import db
from . import inventory_service, waste_service

def hash_file_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def process_document_upload(content: bytes, filename: str, hint: str = None, restaurant_id: str = "taiken_kharadi") -> ExtractionPreviewResponse:
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    file_hash = hash_file_content(content)
    collection_path = f"restaurants/{restaurant_id}/documents"
    existing_docs = db.get_collection(collection_path)
    is_duplicate = any(d.get("hash") == file_hash for d in existing_docs)
    db.add_document(collection_path, doc_id, {
        "id": doc_id,
        "filename": filename,
        "hash": file_hash,
        "status": "ocr_unavailable"
    })
    
    return ExtractionPreviewResponse(
        document_id=doc_id,
        document_type_hint=hint,
        extracted_records=[],
        confidence_score=0.0,
        ambiguous_fields=["Automatic OCR is not implemented; no records were extracted."],
        duplicate_warning=is_duplicate,
        message="The file was received, but automatic OCR is not available yet. Nothing was imported."
    )

def confirm_document_import(restaurant_id: str, request: ConfirmImportRequest) -> int:
    model_by_target = {
        "waste_records": WasteRecordCreate,
        "staff_meal_records": StaffMealRecordCreate,
        "inventory_items": InventoryItemCreate,
    }
    model = model_by_target.get(request.target_entity)
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
