from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class HospitalBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Hospital facility name")
    location: str = Field(..., min_length=2, max_length=150, description="City or locality")
    contact: str = Field(..., min_length=5, max_length=50, description="Contact phone number")


class HospitalCreate(HospitalBase):
    pass


class HospitalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    location: Optional[str] = Field(None, min_length=2, max_length=150)
    contact: Optional[str] = Field(None, min_length=5, max_length=50)


class HospitalResponse(HospitalBase):
    id: int
    is_sample: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

