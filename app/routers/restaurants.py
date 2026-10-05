from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/restaurants", tags=["Restaurants"])


@router.get("", response_model=List[schemas.RestaurantOut])
def list_restaurants(
    cuisine: Optional[str] = Query(None, description="Filter by cuisine (e.g. Italian)"),
    city: Optional[str] = Query(None, description="Filter by city (e.g. San Francisco)"),
    min_capacity: Optional[int] = Query(None, description="Filter by minimum table capacity"),
    db: Session = Depends(get_db),
):
    """Search & filter restaurants by cuisine, city, or minimum capacity."""
    return crud.get_restaurants(db, cuisine=cuisine, city=city, min_capacity=min_capacity)


@router.get("/{restaurant_id}", response_model=schemas.RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a specific restaurant including tables and time slots."""
    res = crud.get_restaurant_by_id(db, restaurant_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found."
        )
    return res


@router.get("/{restaurant_id}/availability", response_model=schemas.SlotAvailabilityOut)
def check_availability(
    restaurant_id: int,
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date YYYY-MM-DD"),
    time_slot: str = Query(..., pattern=r"^\d{2}:\d{2}$", description="Time slot HH:MM"),
    guests: Optional[int] = Query(None, gt=0, description="Number of guests"),
    db: Session = Depends(get_db),
):
    """Check real-time table slot availability for a restaurant on a specific date & time."""
    res = crud.get_restaurant_by_id(db, restaurant_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found."
        )
    table_avail = crud.check_table_availability(
        db, restaurant_id=restaurant_id, date=date, time_slot=time_slot, guests=guests
    )
    return schemas.SlotAvailabilityOut(date=date, time_slot=time_slot, available_tables=table_avail)
