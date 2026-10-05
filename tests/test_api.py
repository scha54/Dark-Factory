import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app import crud, models

# Create SQLite test database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_tablekeeper.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        crud.seed_demo_data(db)
    yield


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_restaurants():
    response = client.get("/api/restaurants")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


def test_filter_restaurants_by_city():
    response = client.get("/api/restaurants?city=San%20Francisco")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "The Golden Spoon"


def test_check_availability():
    response = client.get("/api/restaurants/1/availability?date=2026-10-10&time_slot=18:00")
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-10-10"
    assert len(data["available_tables"]) >= 3
    assert all(t["available"] is True for t in data["available_tables"])


def test_create_and_get_reservation():
    booking_payload = {
        "restaurant_id": 1,
        "table_id": 1,
        "customer_name": "Alice Smith",
        "customer_email": "alice@example.com",
        "customer_phone": "+1-555-0199",
        "guests": 2,
        "date": "2026-10-10",
        "time_slot": "18:00",
    }
    response = client.post("/api/reservations", json=booking_payload)
    assert response.status_code == 201
    booking_data = response.json()
    assert "booking_reference" in booking_data
    ref = booking_data["booking_reference"]

    # Fetch reservation
    get_res = client.get(f"/api/reservations/{ref}")
    assert get_res.status_code == 200
    assert get_res.json()["customer_name"] == "Alice Smith"


def test_double_booking_conflict():
    booking_payload = {
        "restaurant_id": 1,
        "table_id": 1,
        "customer_name": "User 1",
        "customer_email": "u1@example.com",
        "customer_phone": "+1-555-0100",
        "guests": 2,
        "date": "2026-10-10",
        "time_slot": "19:00",
    }
    res1 = client.post("/api/reservations", json=booking_payload)
    assert res1.status_code == 201

    # Second booking for identical table & slot
    booking_payload["customer_name"] = "User 2"
    res2 = client.post("/api/reservations", json=booking_payload)
    assert res2.status_code == 409
    assert "already reserved" in res2.json()["detail"].lower()


def test_cancel_reservation():
    booking_payload = {
        "restaurant_id": 1,
        "table_id": 2,
        "customer_name": "Bob Johnson",
        "customer_email": "bob@example.com",
        "customer_phone": "+1-555-0200",
        "guests": 3,
        "date": "2026-10-11",
        "time_slot": "20:00",
    }
    res = client.post("/api/reservations", json=booking_payload)
    assert res.status_code == 201
    ref = res.json()["booking_reference"]

    # Cancel booking
    cancel_res = client.delete(f"/api/reservations/{ref}")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
