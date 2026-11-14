from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.emergency import (
    EmergencyCreate,
    EmergencyResponse,
    EmergencyStatusUpdate,
    EmergencySummaryResponse,
)
from app.services.emergency_service import (
    create_emergency_case,
    get_all_emergencies,
    get_emergency_by_case_id,
    get_emergency_summary,
    update_emergency_status,
)

router = APIRouter(prefix="/api/emergency", tags=["Emergency Coordination"])


@router.get("", response_model=List[EmergencyResponse], summary="List all emergency coordination cases")
def list_emergencies(db: Session = Depends(get_db)):
    """Retrieve all current and past emergency coordination cases."""
    return get_all_emergencies(db)


@router.get("/summary", response_model=EmergencySummaryResponse, summary="Get emergency overview metrics")
def read_emergency_summary(db: Session = Depends(get_db)):
    """Retrieve counts for total, active, dispatched, and resolved emergencies."""
    return get_emergency_summary(db)


@router.get("/{case_id}", response_model=EmergencyResponse, summary="Get emergency case by case code")
def read_emergency(case_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific emergency case (e.g. EMG001)."""
    case = get_emergency_by_case_id(db, case_id=case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency case '{case_id}' not found.",
        )
    return case


@router.post("", response_model=EmergencyResponse, status_code=status.HTTP_201_CREATED, summary="Log a new emergency request")
def log_emergency(case_in: EmergencyCreate, db: Session = Depends(get_db)):
    """Record a new emergency case to coordinate with hospitals."""
    existing = get_emergency_by_case_id(db, case_id=case_in.case_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Case ID '{case_in.case_id}' already exists.",
        )
    return create_emergency_case(db, case_in=case_in)


@router.patch("/{case_id}/status", response_model=EmergencyResponse, summary="Update emergency status")
def modify_emergency_status(case_id: str, status_in: EmergencyStatusUpdate, db: Session = Depends(get_db)):
    """Update case status (In Progress, Ambulance Sent, Resolved)."""
    updated = update_emergency_status(db, case_id=case_id, status_in=status_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency case '{case_id}' not found.",
        )
    return updated

