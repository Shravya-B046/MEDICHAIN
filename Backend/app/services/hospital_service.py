from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.hospital import Hospital
from app.schemas.hospital import HospitalCreate, HospitalUpdate


def get_all_hospitals(db: Session, skip: int = 0, limit: int = 100) -> List[Hospital]:
    """Retrieve list of hospitals."""
    return db.query(Hospital).order_by(Hospital.id.asc()).offset(skip).limit(limit).all()


def get_hospital_by_id(db: Session, hospital_id: int) -> Optional[Hospital]:
    """Retrieve hospital by ID."""
    return db.query(Hospital).filter(Hospital.id == hospital_id).first()


def create_hospital(db: Session, hospital_in: HospitalCreate, is_sample: bool = False) -> Hospital:
    """Register a new hospital."""
    hospital = Hospital(
        name=hospital_in.name,
        location=hospital_in.location,
        contact=hospital_in.contact,
        is_sample=is_sample,
    )
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital


def update_hospital(db: Session, hospital_id: int, hospital_in: HospitalUpdate) -> Optional[Hospital]:
    """Update hospital details."""
    hospital = get_hospital_by_id(db, hospital_id)
    if not hospital:
        return None

    update_data = hospital_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(hospital, field, value)

    db.commit()
    db.refresh(hospital)
    return hospital


def delete_hospital(db: Session, hospital_id: int) -> bool:
    """Delete a hospital."""
    hospital = get_hospital_by_id(db, hospital_id)
    if not hospital:
        return False
    db.delete(hospital)
    db.commit()
    return True


def seed_sample_hospitals(db: Session) -> None:
    """Pre-seed sample hospital if database has no entries."""
    count = db.query(Hospital).count()
    if count == 0:
        sample = Hospital(
            name="City Hospital",
            location="Mangaluru",
            contact="9876543210",
            is_sample=True,
        )
        db.add(sample)
        db.commit()

