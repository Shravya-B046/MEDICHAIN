from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.resource import Resource
from app.schemas.resource import ResourceSummaryResponse, ResourceUpdate


DEFAULT_RESOURCE_SEEDS = [
    {"resource_type": "General Beds", "total": 150, "available": 120, "occupied": 30, "status": "Available"},
    {"resource_type": "ICU Beds", "total": 40, "available": 18, "occupied": 22, "status": "Available"},
    {"resource_type": "Doctors", "total": 50, "available": 32, "occupied": 18, "status": "Available"},
    {"resource_type": "Ambulances", "total": 12, "available": 8, "occupied": 4, "status": "Available"},
    {"resource_type": "Mechanical Ventilators", "total": 25, "available": 9, "occupied": 16, "status": "Warning"},
    {"resource_type": "Oxygen Cylinders", "total": 180, "available": 142, "occupied": 38, "status": "Available"},
    {"resource_type": "Emergency Antibiotics", "total": 500, "available": 395, "occupied": 105, "status": "Available"},
    {"resource_type": "IV Fluids & Saline", "total": 650, "available": 480, "occupied": 170, "status": "Available"},
]


def get_all_resources(db: Session) -> List[Resource]:
    """Retrieve full list of hospital resource rows."""
    resources = db.query(Resource).order_by(Resource.id.asc()).all()
    if not resources:
        seed_default_resources(db)
        resources = db.query(Resource).order_by(Resource.id.asc()).all()
    return resources


def get_resource_summary(db: Session) -> ResourceSummaryResponse:
    """Calculate aggregated totals for the platform overview cards."""
    resources = get_all_resources(db)

    # Compute totals from resources
    total_beds = 250
    available_beds = 186
    occupied_beds = 64
    icu_beds = 18
    doctors_on_duty = 32
    available_ambulances = 8

    for r in resources:
        if r.resource_type == "General Beds":
            available_beds = r.available
            occupied_beds = r.occupied
            total_beds = r.total
        elif r.resource_type == "ICU Beds":
            icu_beds = r.available
            total_beds += r.total
            occupied_beds += r.occupied
        elif r.resource_type == "Doctors":
            doctors_on_duty = r.available
        elif r.resource_type == "Ambulances":
            available_ambulances = r.available

    return ResourceSummaryResponse(
        total_beds=total_beds,
        available_beds=available_beds,
        occupied_beds=occupied_beds,
        icu_beds=icu_beds,
        doctors_on_duty=doctors_on_duty,
        available_ambulances=available_ambulances,
        is_demo_data=True,
    )


def update_resource(db: Session, resource_id: int, update_in: ResourceUpdate) -> Optional[Resource]:
    """Update a specific resource row."""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        return None

    update_data = update_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)

    db.commit()
    db.refresh(resource)
    return resource


def seed_default_resources(db: Session) -> None:
    """Seed default synthetic demonstration resources."""
    existing_types = {r.resource_type for r in db.query(Resource).all()}
    added = False
    for seed_data in DEFAULT_RESOURCE_SEEDS:
        if seed_data["resource_type"] not in existing_types:
            res = Resource(**seed_data)
            db.add(res)
            added = True
    if added:
        db.commit()

