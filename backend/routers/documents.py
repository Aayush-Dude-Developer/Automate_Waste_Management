from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import ValidationError
from typing import Optional
from ..auth import get_restaurant_id
from ..schemas.documents import (
    AmendRecordsRequest,
    AmendRecordsResponse,
    ExtractionPreviewResponse,
    ConfirmImportRequest,
)
from ..services import document_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.post("/upload", response_model=ExtractionPreviewResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type_hint: Optional[str] = Form(None),
    restaurant_id: str = Depends(get_restaurant_id)
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        return document_service.process_document_upload(
            content, file.filename or "upload", document_type_hint, restaurant_id
        )
    except document_service.DocumentExtractionUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except document_service.DocumentExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/amend-records", response_model=AmendRecordsResponse)
def amend_records(request: AmendRecordsRequest, _restaurant_id: str = Depends(get_restaurant_id)):
    try:
        return document_service.amend_document_records(request)
    except document_service.DocumentExtractionUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except document_service.DocumentExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/confirm-import")
def confirm_import(request: ConfirmImportRequest, restaurant_id: str = Depends(get_restaurant_id)):
    if not request.confirmed_records:
        raise HTTPException(status_code=400, detail="There are no confirmed records to import.")
    try:
        count = document_service.confirm_document_import(restaurant_id, request)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors()) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "success", "imported_records": count}
