import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.clipper.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.video_ai.models  # noqa: F401 ensure all tables are registered on Base.metadata
from app.clipper.services import project_service
from app.core.database import Base

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


@pytest.fixture
def db():
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


def test_create_and_list_projects(db):
    project_service.create_project(db, "Campaign A")
    project_service.create_project(db, "Campaign B")

    projects = project_service.list_projects(db)

    assert [p.name for p in projects] == ["Campaign B", "Campaign A"]


def test_get_project_returns_none_when_missing(db):
    assert project_service.get_project(db, 999) is None


def test_get_project_returns_created_project(db):
    created = project_service.create_project(db, "Campaign C")

    fetched = project_service.get_project(db, created.id)

    assert fetched is not None
    assert fetched.name == "Campaign C"
