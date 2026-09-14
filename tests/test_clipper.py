import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.clipper.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.models  # noqa: F401 ensure all tables are registered on Base.metadata
from app.clipper.services import clip_service
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


def test_create_job_persists_defaults(db):
    job = clip_service.create_job(
        db,
        source_file_path="/tmp/fake.mp4",
        original_filename="fake.mp4",
    )

    assert job.id is not None
    assert job.status == "uploaded"
    assert job.segment_seconds == 120
    assert job.auto_caption is True
    assert job.reformat_vertical is False


def test_process_job_marks_failed_when_source_missing(db):
    job = clip_service.create_job(
        db,
        source_file_path="/tmp/does_not_exist.mp4",
        original_filename="does_not_exist.mp4",
    )

    result = clip_service.process_job(db, job)

    assert result.status == "failed"
    assert result.error
