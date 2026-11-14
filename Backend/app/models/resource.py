from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Resource(Base):
    """Hospital resource availability tracking entity."""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=True)
    resource_type = Column(String(50), nullable=False, index=True)  # General Beds, ICU Beds, Doctors, Ambulances
    total = Column(Integer, default=0, nullable=False)
    available = Column(Integer, default=0, nullable=False)
    occupied = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="Available", nullable=False)  # Available, Warning, Occupied
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    hospital = relationship("Hospital", back_populates="resources")

    def __repr__(self) -> str:
        return f"<Resource(id={self.id}, type='{self.resource_type}', available={self.available}/{self.total})>"
