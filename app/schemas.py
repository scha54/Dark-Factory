from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Table Schemas ---
class TableBase(BaseModel):
    table_number: int
    capacity: int
    location_type: str = "indoor"


class TableCreate(TableBase):
    pass


class TableOut(TableBase):
    id: int
    restaurant_id: int

    model_config = ConfigDict(from_attributes=True)


# --- TimeSlot Schemas ---
class TimeSlotBase(BaseModel):
    slot_time: str


class TimeSlotOut(TimeSlotBase):
    id: int
    restaurant_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Restaurant Schemas ---
class RestaurantBase(BaseModel):
    name: str
    cuisine: str
    city: str
    address: str
    phone: str
    description: Optional[str] = None


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantOut(RestaurantBase):
    id: int
    created_at: datetime
    tables: List[TableOut] = []
    time_slots: List[TimeSlotOut] = []

    model_config = ConfigDict(from_attributes=True)


# --- Availability Schemas ---
class TableAvailability(BaseModel):
    table_id: int
    table_number: int
    capacity: int
    location_type: str
    available: bool


class SlotAvailabilityOut(BaseModel):
    date: str
    time_slot: str
    available_tables: List[TableAvailability]


# --- Reservation Schemas ---
class ReservationCreate(BaseModel):
    restaurant_id: int
    table_id: int
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    guests: int = Field(gt=0, description="Number of guests must be at least 1")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Format YYYY-MM-DD")
    time_slot: str = Field(pattern=r"^\d{2}:\d{2}$", description="Format HH:MM")


class ReservationUpdate(BaseModel):
    guests: Optional[int] = Field(default=None, gt=0)
    date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_slot: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    table_id: Optional[int] = None


class ReservationOut(BaseModel):
    id: int
    booking_reference: str
    restaurant_id: int
    table_id: int
    customer_name: str
    customer_email: str
    customer_phone: str
    guests: int
    date: str
    time_slot: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
