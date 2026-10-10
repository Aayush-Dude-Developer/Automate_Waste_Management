import uuid
import hashlib
from typing import Dict, Any
from ..schemas.documents import ExtractionPreviewResponse
from ..repositories.database import db

def hash_file_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def process_document_upload(content: bytes, filename: str, hint: str = None) -> ExtractionPreviewResponse:
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    file_hash = hash_file_content(content)
    
    # Check for duplicates in DB
    existing_docs = db.get_collection("documents")
    is_duplicate = any(d.get("hash") == file_hash for d in existing_docs)
    
    # In Phase 5, this will call Gemini Multimodal OCR
    # For Phase 3, we mock the extraction based on the hint
    extracted = []
    ambiguous = []
    
    if hint == "waste":
        extracted = [
            {"date": "2026-08-02", "item_name": "chinese noodles", "quantity": 400, "unit": "grm", "reason": "Broken", "checked_by": "Ritesh"}
        ]
    elif hint == "staff_meals":
        extracted = [
            {"date": "2026-09-29", "shift": "Lunch", "ingredient_name": "Rice", "quantity": 150, "unit": "gm"}
        ]
        ambiguous = ["Rice (150 gm for 13 people might be 1.5 kg)"]
        
    # Store document metadata
    db.add_document("documents", doc_id, {
        "id": doc_id,
        "filename": filename,
        "hash": file_hash,
        "status": "pending_review"
    })
    
    return ExtractionPreviewResponse(
        document_id=doc_id,
        document_type_hint=hint,
        extracted_records=extracted,
        confidence_score=0.85 if not ambiguous else 0.65,
        ambiguous_fields=ambiguous,
        duplicate_warning=is_duplicate
    )
