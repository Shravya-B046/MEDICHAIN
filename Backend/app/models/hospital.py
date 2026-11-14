from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Hospital(Base):
    """Hospital entity for administration and resource mapping."""
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    location = Column(String(150), nullable=False)
    contact = Column(String(50), nullable=False)
    is_sample = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    resources = relationship("Resource", back_populates="hospital", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Hospital(id={self.id}, name='{self.name}', location='{self.location}')>"
