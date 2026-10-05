import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Reservation, Restaurant, Table, TimeSlot
from app.schemas import ReservationCreate, ReservationUpdate, RestaurantCreate


def get_restaurants(
    db: Session,
    cuisine: Optional[str] = None,
    city: Optional[str] = None,
    min_capacity: Optional[int] = None,
) -> List[Restaurant]:
    query = db.query(Restaurant)
    if cuisine:
        query = query.filter(Restaurant.cuisine.ilike(f"%{cuisine}%"))
    if city:
        query = query.filter(Restaurant.city.ilike(f"%{city}%"))
    if min_capacity:
        query = query.join(Table).filter(Table.capacity >= min_capacity).distinct()
    return query.all()


def get_restaurant_by_id(db: Session, restaurant_id: int) -> Optional[Restaurant]:
    return db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()


def check_table_availability(
    db: Session, restaurant_id: int, date: str, time_slot: str, guests: Optional[int] = None
) -> List[dict]:
    tables_query = db.query(Table).filter(Table.restaurant_id == restaurant_id)
    if guests:
        tables_query = tables_query.filter(Table.capacity >= guests)
    tables = tables_query.all()

    # Get booked table IDs for the given date, time_slot, and status='CONFIRMED'
    booked_table_ids = set(
        r.table_id
        for r in db.query(Reservation.table_id)
        .filter(
            Reservation.restaurant_id == restaurant_id,
            Reservation.date == date,
            Reservation.time_slot == time_slot,
            Reservation.status == "CONFIRMED",
        )
        .all()
    )

    availability = []
    for table in tables:
        availability.append(
            {
                "table_id": table.id,
                "table_number": table.table_number,
                "capacity": table.capacity,
                "location_type": table.location_type,
                "available": table.id not in booked_table_ids,
            }
        )
    return availability


def create_reservation(db: Session, reservation_in: ReservationCreate) -> Reservation:
    """Atomic creation of a reservation with double-booking race condition protection."""
    # 1. Verify table exists and belongs to the restaurant
    table = (
        db.query(Table)
        .filter(Table.id == reservation_in.table_id, Table.restaurant_id == reservation_in.restaurant_id)
        .first()
    )
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specified table does not exist at this restaurant.",
        )

    # 2. Verify table capacity
    if table.capacity < reservation_in.guests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Table capacity ({table.capacity}) is insufficient for {reservation_in.guests} guests.",
        )

    # 3. Check existing active reservation
    existing = (
        db.query(Reservation)
        .filter(
            Reservation.table_id == reservation_in.table_id,
            Reservation.date == reservation_in.date,
            Reservation.time_slot == reservation_in.time_slot,
            Reservation.status == "CONFIRMED",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Table is already reserved for the selected date and time slot.",
        )

    # 4. Generate unique booking reference & attempt database write
    booking_ref = f"RES-{uuid.uuid4().hex[:6].upper()}"
    new_res = Reservation(
        booking_reference=booking_ref,
        restaurant_id=reservation_in.restaurant_id,
        table_id=reservation_in.table_id,
        customer_name=reservation_in.customer_name,
        customer_email=reservation_in.customer_email,
        customer_phone=reservation_in.customer_phone,
        guests=reservation_in.guests,
        date=reservation_in.date,
        time_slot=reservation_in.time_slot,
        status="CONFIRMED",
    )

    try:
        db.add(new_res)
        db.commit()
        db.refresh(new_res)
        return new_res
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Double-booking detected! Another customer reserved this slot simultaneously.",
        )


def get_reservation_by_ref(db: Session, booking_ref: str) -> Optional[Reservation]:
    return db.query(Reservation).filter(Reservation.booking_reference == booking_ref).first()


def update_reservation(db: Session, booking_ref: str, update_in: ReservationUpdate) -> Reservation:
    res = get_reservation_by_ref(db, booking_ref)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")

    if res.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot amend a cancelled reservation."
        )

    new_date = update_in.date or res.date
    new_slot = update_in.time_slot or res.time_slot
    new_table_id = update_in.table_id or res.table_id
    new_guests = update_in.guests or res.guests

    # Check if table capacity is sufficient
    table = db.query(Table).filter(Table.id == new_table_id).first()
    if not table or table.capacity < new_guests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected table is invalid or capacity is insufficient for guests.",
        )

    # Check for slot conflict if slot/date/table changing
    if (new_date != res.date) or (new_slot != res.time_slot) or (new_table_id != res.table_id):
        conflict = (
            db.query(Reservation)
            .filter(
                Reservation.table_id == new_table_id,
                Reservation.date == new_date,
                Reservation.time_slot == new_slot,
                Reservation.status == "CONFIRMED",
                Reservation.id != res.id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Target table and time slot are already reserved.",
            )

    res.date = new_date
    res.time_slot = new_slot
    res.table_id = new_table_id
    res.guests = new_guests

    try:
        db.commit()
        db.refresh(res)
        return res
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Slot collision during amendment commit."
        )


def cancel_reservation(db: Session, booking_ref: str) -> Reservation:
    res = get_reservation_by_ref(db, booking_ref)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
    res.status = "CANCELLED"
    db.commit()
    db.refresh(res)
    return res


def seed_demo_data(db: Session):
    """Seed initial sample restaurants, tables, and time slots if database is empty."""
    if db.query(Restaurant).first():
        return

    r1 = Restaurant(
        name="The Golden Spoon",
        cuisine="Italian",
        city="San Francisco",
        address="123 Market St, San Francisco, CA",
        phone="+1-415-555-0199",
        description="Authentic handmade pasta and wood-fired pizza in a cozy fine-dining setting.",
    )
    r2 = Restaurant(
        name="Sakura Sushi House",
        cuisine="Japanese",
        city="New York",
        address="456 5th Ave, New York, NY",
        phone="+1-212-555-0144",
        description="Fresh omakase sushi and artisanal ramen crafted by master chefs.",
    )
    r3 = Restaurant(
        name="El Sabor Bistro",
        cuisine="Mexican",
        city="Austin",
        address="789 Congress Ave, Austin, TX",
        phone="+1-512-555-0188",
        description="Vibrant modern Mexican cuisine featuring craft mezcal cocktails and street tacos.",
    )

    db.add_all([r1, r2, r3])
    db.commit()

    # Tables for Golden Spoon
    t1 = Table(restaurant_id=r1.id, table_number=1, capacity=2, location_type="window")
    t2 = Table(restaurant_id=r1.id, table_number=2, capacity=4, location_type="indoor")
    t3 = Table(restaurant_id=r1.id, table_number=3, capacity=6, location_type="patio")

    # Tables for Sakura
    t4 = Table(restaurant_id=r2.id, table_number=1, capacity=2, location_type="sushi bar")
    t5 = Table(restaurant_id=r2.id, table_number=2, capacity=4, location_type="indoor")

    # Tables for El Sabor
    t6 = Table(restaurant_id=r3.id, table_number=1, capacity=4, location_type="outdoor")
    t7 = Table(restaurant_id=r3.id, table_number=2, capacity=8, location_type="indoor")

    db.add_all([t1, t2, t3, t4, t5, t6, t7])

    # Time slots
    slots = ["17:00", "18:00", "19:00", "20:00", "21:00"]
    for r in [r1, r2, r3]:
        for s in slots:
            db.add(TimeSlot(restaurant_id=r.id, slot_time=s))

    db.commit()
