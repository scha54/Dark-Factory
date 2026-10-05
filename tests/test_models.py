import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_restaurant(db_session):
    rest = models.Restaurant(
        name="Bistro Paris",
        cuisine="French",
        city="Paris",
        address="10 Rue de la Paix",
        phone="+33-1-4000-0000",
    )
    db_session.add(rest)
    db_session.commit()

    saved = db_session.query(models.Restaurant).filter_by(name="Bistro Paris").first()
    assert saved is not None
    assert saved.cuisine == "French"
    assert saved.city == "Paris"


def test_create_table_relationship(db_session):
    rest = models.Restaurant(
        name="Taco Palace",
        cuisine="Mexican",
        city="San Diego",
        address="100 Ocean Blvd",
        phone="+1-619-555-0100",
    )
    db_session.add(rest)
    db_session.commit()

    table = models.Table(
        restaurant_id=rest.id, table_number=1, capacity=4, location_type="patio"
    )
    db_session.add(table)
    db_session.commit()

    assert len(rest.tables) == 1
    assert rest.tables[0].capacity == 4
