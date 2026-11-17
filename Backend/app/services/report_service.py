import logging
import os
import re
import uuid
from pathlib import Path
from typing import List, Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.report import ReportAudit
from app.schemas.report import ReportAnalysisResponse
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


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


def extract_pdf_data(pdf_path: Path) -> Tuple[str, List[str]]:
    """
    Extracts text from a PDF file using pypdf and identifies clinical findings.
    Returns: (full_extracted_text, list_of_detected_findings)
    """
    extracted_text = ""
    findings = []

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        page_texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                page_texts.append(text)

        extracted_text = "\n".join(page_texts).strip()

        if extracted_text:
            # Look for lines containing lab parameters, numerical values, or reference ranges
            # Common medical lab metrics
            markers = [
                r"hemoglobin|hgb",
                r"wbc|white blood cell",
                r"rbc|red blood cell",
                r"platelet",
                r"glucose|sugar",
                r"cholesterol",
                r"creatinine",
                r"blood pressure|bp",
                r"triglycerides",
                r"bilirubin",
                r"urea|bun",
                r"sodium|potassium",
                r"calcium",
                r"sgot|sgpt|alt|ast",
            ]
            combined_pattern = re.compile("|".join(markers), re.IGNORECASE)

            lines = extracted_text.splitlines()
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if combined_pattern.search(stripped):
                    # Clean up multiple whitespaces
                    clean_line = re.sub(r"\s+", " ", stripped)
                    if len(clean_line) <= 120 and clean_line not in findings:
                        findings.append(clean_line)

            # Limit to top 8 findings for clear presentation
            findings = findings[:8]

    except Exception as e:
        logger.warning(f"pypdf extraction error on {pdf_path}: {e}")

    return extracted_text, findings


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

        extracted_text = ""
        findings = []
        if ext == "pdf":
            extracted_text, findings = extract_pdf_data(temp_path)

        # Perform AI analysis
        analysis_data = ai_service.analyze_medical_document(
            filename=filename,
            file_size_kb=file_size_kb,
            content_type=content_type,
            extracted_text=extracted_text,
            extracted_findings=findings,
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
            extracted_findings=analysis_data.get("extracted_findings", []),
            extraction_method=analysis_data.get("extraction_method", "pypdf_parser"),
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
