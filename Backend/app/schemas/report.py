from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


def get_current_utc():
    return datetime.now(timezone.utc)


class ReportAnalysisResponse(BaseModel):
    """
    Structured preliminary response for medical report processing.
    Note: Temporary upload files are purged immediately after processing.
    """
    filename: str
    file_size_kb: float
    content_type: str
    status: str = "Completed"
    is_medical: bool = True
    summary_title: str
    key_observations: List[str]
    extracted_findings: List[str] = Field(default_factory=list)
    extraction_method: str = "pdf_text_parser"
    suggested_questions_for_doctor: List[str]
    disclaimer: str = (
        "Preliminary summary generated for educational guidance only. "
        "This tool is NOT a diagnostic medical device and does not substitute "
        "for a qualified physician's consultation."
    )
    temporary_file_cleaned: bool = True
    processed_at: datetime = Field(default_factory=get_current_utc)


class ReportAuditResponse(BaseModel):
    id: int
    filename: str
    file_size_kb: float
    content_type: str
    processing_status: str
    temporary_file_cleaned: bool
    processed_at: datetime

    model_config = ConfigDict(from_attributes=True)
