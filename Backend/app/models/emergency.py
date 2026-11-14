from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Emergency(Base):
    """Emergency coordination case entity."""
    __tablename__ = "emergencies"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(20), unique=True, index=True, nullable=False)  # e.g., EMG001
    emergency_type = Column(String(100), nullable=False)  # e.g., Road Accident, Cardiac Emergency
    location = Column(String(150), nullable=False)
    hospital_name = Column(String(150), nullable=False)
    priority = Column(String(20), nullable=False)  # Critical, High, Medium, Low
    status = Column(String(30), nullable=False)  # In Progress, Ambulance Sent, Resolved
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Emergency(case_id='{self.case_id}', type='{self.emergency_type}', status='{self.status}')>"
