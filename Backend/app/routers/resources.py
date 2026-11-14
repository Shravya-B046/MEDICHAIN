from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.resource import ResourceResponse, ResourceSummaryResponse, ResourceUpdate
from app.services.resource_service import get_all_resources, get_resource_summary, update_resource

router = APIRouter(prefix="/api/resources", tags=["Hospital Resource Dashboard"])


@router.get("", response_model=List[ResourceResponse], summary="List all hospital resources")
def list_resources(db: Session = Depends(get_db)):
    """Retrieve tabular bed, ICU, doctor, and ambulance resource status."""
    return get_all_resources(db)


@router.get("/summary", response_model=ResourceSummaryResponse, summary="Get aggregated resource dashboard totals")
def read_resource_summary(db: Session = Depends(get_db)):
    """Retrieve aggregated bed counts, ICU counts, and staff for frontend cards."""
    return get_resource_summary(db)


@router.put("/{resource_id}", response_model=ResourceResponse, summary="Update resource counts")
def modify_resource(resource_id: int, update_in: ResourceUpdate, db: Session = Depends(get_db)):
    """Update available/occupied numbers for a specific resource."""
    updated = update_resource(db, resource_id=resource_id, update_in=update_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource row with ID {resource_id} not found.",
        )
    return updated

