from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EmergencyBase(BaseModel):
    case_id: str = Field(..., max_length=20, description="Unique case code, e.g. EMG001")
    emergency_type: str = Field(..., max_length=100, description="Nature of incident")
    location: str = Field(..., max_length=150, description="Incident location")
    hospital_name: str = Field(..., max_length=150, description="Assigned hospital")
    priority: str = Field(default="Critical", max_length=20, description="Critical / High / Medium / Low")
    status: str = Field(default="In Progress", max_length=30, description="In Progress / Ambulance Sent / Resolved")


class EmergencyCreate(BaseModel):
    case_id: Optional[str] = Field(None, max_length=20, description="Unique case code, or auto-generated if omitted")
    emergency_type: str = Field(..., max_length=100, description="Nature of incident")
    location: str = Field(..., max_length=150, description="Incident location")
    hospital_name: str = Field(..., max_length=150, description="Assigned hospital")
    priority: str = Field(default="Critical", max_length=20, description="Critical / High / Medium / Low")
    status: str = Field(default="In Progress", max_length=30, description="In Progress / Ambulance Sent / Resolved")


class EmergencyStatusUpdate(BaseModel):
    status: str = Field(..., max_length=30)
    priority: Optional[str] = Field(None, max_length=20)


class EmergencyResponse(EmergencyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmergencySummaryResponse(BaseModel):
    total_emergencies: int
    active_emergencies: int
    ambulances_dispatched: int
    resolved_cases: int
    is_demo_data: bool = True
    disclaimer: str = (
        "Demonstration data only. Not connected to live emergency dispatch. In India, dial 112."
    )

