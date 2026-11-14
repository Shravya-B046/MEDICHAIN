from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.emergency import Emergency
from app.schemas.emergency import EmergencyCreate, EmergencyStatusUpdate, EmergencySummaryResponse


DEFAULT_EMERGENCY_SEEDS = [
    {
        "case_id": "EMG001",
        "emergency_type": "Road Accident",
        "location": "Mangaluru",
        "hospital_name": "City Hospital",
        "priority": "Critical",
        "status": "In Progress",
    },
    {
        "case_id": "EMG002",
        "emergency_type": "Cardiac Emergency",
        "location": "Bantwal",
        "hospital_name": "General Hospital",
        "priority": "Critical",
        "status": "Ambulance Sent",
    },
    {
        "case_id": "EMG003",
        "emergency_type": "Medical Emergency",
        "location": "Udupi",
        "hospital_name": "District Hospital",
        "priority": "Medium",
        "status": "Resolved",
    },
    {
        "case_id": "EMG004",
        "emergency_type": "Accident",
        "location": "Surathkal",
        "hospital_name": "City Hospital",
        "priority": "High",
        "status": "In Progress",
    },
]


def get_all_emergencies(db: Session) -> List[Emergency]:
    """Retrieve all emergency coordination cases."""
    emergencies = db.query(Emergency).order_by(Emergency.id.asc()).all()
    if not emergencies:
        seed_default_emergencies(db)
        emergencies = db.query(Emergency).order_by(Emergency.id.asc()).all()
    return emergencies


def get_emergency_by_case_id(db: Session, case_id: str) -> Optional[Emergency]:
    """Find case by unique case ID."""
    return db.query(Emergency).filter(Emergency.case_id == case_id).first()


def create_emergency_case(db: Session, case_in: EmergencyCreate) -> Emergency:
    """Create a new emergency case."""
    emergency = Emergency(
        case_id=case_in.case_id,
        emergency_type=case_in.emergency_type,
        location=case_in.location,
        hospital_name=case_in.hospital_name,
        priority=case_in.priority,
        status=case_in.status,
    )
    db.add(emergency)
    db.commit()
    db.refresh(emergency)
    return emergency


def update_emergency_status(db: Session, case_id: str, status_in: EmergencyStatusUpdate) -> Optional[Emergency]:
    """Update case status and/or priority."""
    case = get_emergency_by_case_id(db, case_id)
    if not case:
        return None

    case.status = status_in.status
    if status_in.priority:
        case.priority = status_in.priority

    db.commit()
    db.refresh(case)
    return case


def get_emergency_summary(db: Session) -> EmergencySummaryResponse:
    """Compute active, dispatched, and resolved counts for overview cards."""
    emergencies = get_all_emergencies(db)

    total = len(emergencies)
    active = sum(1 for e in emergencies if e.status.lower() in ["in progress", "active"])
    dispatched = sum(1 for e in emergencies if "ambulance" in e.status.lower() or "sent" in e.status.lower() or "dispatched" in e.status.lower())
    resolved = sum(1 for e in emergencies if e.status.lower() in ["resolved", "completed", "closed"])

    return EmergencySummaryResponse(
        total_emergencies=total,
        active_emergencies=active,
        ambulances_dispatched=dispatched,
        resolved_cases=resolved,
        is_demo_data=True,
    )


def seed_default_emergencies(db: Session) -> None:
    """Seed synthetic demonstration emergencies."""
    if db.query(Emergency).count() == 0:
        for seed_data in DEFAULT_EMERGENCY_SEEDS:
            case = Emergency(**seed_data)
            db.add(case)
        db.commit()

