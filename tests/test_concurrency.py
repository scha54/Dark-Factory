import concurrent.futures
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app import models

# Use file-based SQLite database with WAL mode for concurrency test
TEST_DB_URL = "sqlite:///./test_concurrency.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def test_concurrent_double_booking_prevention():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    from app import crud
    with TestingSessionLocal() as db:
        crud.seed_demo_data(db)

    client = TestClient(app)

    target_date = "2026-10-15"
    target_slot = "19:00"
    target_table_id = 1
    target_restaurant_id = 1

    def make_booking_request(thread_id):
        payload = {
            "restaurant_id": target_restaurant_id,
            "table_id": target_table_id,
            "customer_name": f"Concurrent User {thread_id}",
            "customer_email": f"user{thread_id}@example.com",
            "customer_phone": f"+1-555-000{thread_id}",
            "guests": 2,
            "date": target_date,
            "time_slot": target_slot,
        }
        return client.post("/api/reservations", json=payload)

    num_threads = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(make_booking_request, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    status_codes = [r.status_code for r in results]
    successes = [code for code in status_codes if code == 201]
    conflicts = [code for code in status_codes if code == 409]

    # Verify atomic protection guarantees: Exactly 1 success, rest conflicts
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(conflicts) == num_threads - 1, f"Expected {num_threads - 1} conflicts, got {len(conflicts)}"

    # Database state verification
    with TestingSessionLocal() as db:
        active_res = (
            db.query(models.Reservation)
            .filter(
                models.Reservation.table_id == target_table_id,
                models.Reservation.date == target_date,
                models.Reservation.time_slot == target_slot,
                models.Reservation.status == "CONFIRMED",
            )
            .all()
        )
        assert len(active_res) == 1, "Database contains duplicate active bookings!"
