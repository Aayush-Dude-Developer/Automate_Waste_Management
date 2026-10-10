from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from ..schemas.documents import ExtractionPreviewResponse, ConfirmImportRequest
from ..services import document_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.post("/upload", response_model=ExtractionPreviewResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type_hint: Optional[str] = Form(None)
):
    content = await file.read()
    return document_service.process_document_upload(content, file.filename, document_type_hint)

@router.post("/confirm-import")
def confirm_import(request: ConfirmImportRequest):
    # Depending on target_entity, route to correct service
    # E.g. waste_service.log_waste_record, etc.
    return {"status": "success", "imported_records": len(request.confirmed_records)}
