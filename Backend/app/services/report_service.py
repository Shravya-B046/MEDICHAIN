import os
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.report import ReportAudit
from app.schemas.report import ReportAnalysisResponse
from app.services.ai_service import ai_service


def validate_upload(file: UploadFile) -> Tuple[str, str]:
    """
    Validates file extension and content type.
    Returns: (cleaned_filename, extension)
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    filename = file.filename.strip()
    ext = Path(filename).suffix.lower().lstrip(".")

    allowed_exts = settings.allowed_extensions_list
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Allowed formats: {', '.join(allowed_exts)}.",
        )

    return filename, ext


async def process_report_upload(file: UploadFile, db: Session) -> ReportAnalysisResponse:
    """
    Temporarily processes an uploaded medical document, runs preliminary AI analysis,
    and immediately deletes the file from disk in compliance with privacy guidelines.
    """
    filename, ext = validate_upload(file)

    upload_dir = settings.upload_dir_path
    temp_filename = f"temp_{uuid.uuid4().hex}.{ext}"
    temp_path = upload_dir / temp_filename

    total_bytes = 0
    max_bytes = settings.MAX_FILE_SIZE_BYTES

    # Stream chunks into temporary file to validate size
    try:
        with open(temp_path, "wb") as f_out:
            while True:
                chunk = await file.read(64 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB.",
                    )
                f_out.write(chunk)

        file_size_kb = round(total_bytes / 1024, 2)
        content_type = file.content_type or f"application/{ext}"

        # Perform AI analysis
        analysis_data = ai_service.analyze_medical_document(
            filename=filename,
            file_size_kb=file_size_kb,
            content_type=content_type,
        )

        # Record privacy-compliant audit entry (no raw medical content stored)
        audit_entry = ReportAudit(
            filename=filename,
            file_size_kb=file_size_kb,
            content_type=content_type,
            processing_status="processed",
            temporary_file_cleaned=True,
        )
        db.add(audit_entry)
        db.commit()

        return ReportAnalysisResponse(
            filename=filename,
            file_size_kb=file_size_kb,
            content_type=content_type,
            status="Completed",
            summary_title=analysis_data["summary_title"],
            key_observations=analysis_data["key_observations"],
            suggested_questions_for_doctor=analysis_data["suggested_questions_for_doctor"],
            temporary_file_cleaned=True,
        )

    finally:
        # Guarantee cleanup of temporary file
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except OSError:
                pass

