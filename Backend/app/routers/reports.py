from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.report import ReportAnalysisResponse
from app.services.report_service import process_report_upload

router = APIRouter(prefix="/api/reports", tags=["AI Preliminary Report Analysis"])


@router.post("/upload", response_model=ReportAnalysisResponse, summary="Upload medical report for preliminary AI summary")
async def analyze_medical_report(
    file: UploadFile = File(..., description="Medical report file (PDF, PNG, JPG, JPEG)"),
    db: Session = Depends(get_db),
):
    """
    Accepts a medical report document, runs format and clinical observation extraction,
    and returns an educational summary.

    **Privacy & Safety Note**:
    Uploaded files are stored temporarily in `Backend/uploads/` only for immediate processing,
    and are purged from the filesystem immediately upon completion. Raw report files are NOT
    permanently archived.
    """
    return await process_report_upload(file=file, db=db)

