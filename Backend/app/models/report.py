from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ReportAudit(Base):
    """
    Audit log for temporary report processing.
    Note: As per privacy and safety requirements, raw medical files and extracted
    medical text are NOT permanently stored in the database.
    """
    __tablename__ = "report_audits"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_size_kb = Column(Float, nullable=False)
    content_type = Column(String(100), nullable=False)
    processing_status = Column(String(50), default="processed", nullable=False)
    temporary_file_cleaned = Column(Boolean, default=True, nullable=False)
    processed_at = Column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<ReportAudit(id={self.id}, file='{self.filename}', status='{self.processing_status}')>"
