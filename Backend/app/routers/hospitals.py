from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.hospital import HospitalCreate, HospitalResponse, HospitalUpdate
from app.services.hospital_service import (
    create_hospital,
    delete_hospital,
    get_all_hospitals,
    get_hospital_by_id,
    update_hospital,
)

router = APIRouter(prefix="/api/hospitals", tags=["Hospitals & Administration"])


@router.get("", response_model=List[HospitalResponse], summary="List all registered hospitals")
def list_hospitals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve list of registered hospitals."""
    return get_all_hospitals(db, skip=skip, limit=limit)


@router.get("/{hospital_id}", response_model=HospitalResponse, summary="Get hospital by ID")
def read_hospital(hospital_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a specific hospital."""
    hospital = get_hospital_by_id(db, hospital_id=hospital_id)
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital with ID {hospital_id} not found.",
        )
    return hospital


@router.post("", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED, summary="Register a hospital")
def register_hospital(hospital_in: HospitalCreate, db: Session = Depends(get_db)):
    """Register a new hospital facility in the platform."""
    return create_hospital(db, hospital_in=hospital_in, is_sample=False)


@router.put("/{hospital_id}", response_model=HospitalResponse, summary="Update hospital details")
def modify_hospital(hospital_id: int, hospital_in: HospitalUpdate, db: Session = Depends(get_db)):
    """Update contact, name, or location for a hospital."""
    hospital = update_hospital(db, hospital_id=hospital_id, hospital_in=hospital_in)
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital with ID {hospital_id} not found.",
        )
    return hospital


@router.delete("/{hospital_id}", summary="Delete hospital registration")
def remove_hospital(hospital_id: int, db: Session = Depends(get_db)):
    """Remove a hospital from the registered directory."""
    success = delete_hospital(db, hospital_id=hospital_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital with ID {hospital_id} not found.",
        )
    return {"message": "Hospital registration deleted successfully.", "hospital_id": hospital_id}

