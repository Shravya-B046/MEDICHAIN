from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ResourceBase(BaseModel):
    resource_type: str = Field(..., max_length=50, description="Resource classification")
    total: int = Field(default=0, ge=0)
    available: int = Field(default=0, ge=0)
    occupied: int = Field(default=0, ge=0)
    status: str = Field(default="Available", max_length=20)


class ResourceUpdate(BaseModel):
    total: Optional[int] = Field(None, ge=0)
    available: Optional[int] = Field(None, ge=0)
    occupied: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=20)


class ResourceResponse(ResourceBase):
    id: int
    hospital_id: Optional[int] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceSummaryResponse(BaseModel):
    """Aggregated resource statistics matching the dashboard cards."""
    total_beds: int
    available_beds: int
    occupied_beds: int
    icu_beds: int
    doctors_on_duty: int
    available_ambulances: int
    is_demo_data: bool = True
    disclaimer: str = (
        "Demonstration data only. Hospital availability must be verified with facilities."
    )

