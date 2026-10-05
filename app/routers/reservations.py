from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/reservations", tags=["Reservations"])


@router.post("", response_model=schemas.ReservationOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    reservation_in: schemas.ReservationCreate, db: Session = Depends(get_db)
):
    """Create a new table reservation with atomic double-booking protection."""
    return crud.create_reservation(db, reservation_in)


@router.get("/{booking_reference}", response_model=schemas.ReservationOut)
def get_booking(booking_reference: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific reservation by booking reference."""
    res = crud.get_reservation_by_ref(db, booking_reference)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation reference not found."
        )
    return res


@router.put("/{booking_reference}", response_model=schemas.ReservationOut)
def update_booking(
    booking_reference: str,
    update_in: schemas.ReservationUpdate,
    db: Session = Depends(get_db),
):
    """Amend an existing active reservation (date, time slot, table, or guest count)."""
    return crud.update_reservation(db, booking_reference, update_in)


@router.delete("/{booking_reference}", response_model=schemas.ReservationOut)
def cancel_booking(booking_reference: str, db: Session = Depends(get_db)):
    """Cancel an existing reservation."""
    return crud.cancel_reservation(db, booking_reference)
