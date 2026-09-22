import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.clipper.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.video_ai.models  # noqa: F401 ensure all tables are registered on Base.metadata
from app.clipper.models.project import Project
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


@pytest.fixture
def project(db):
    p = Project(name="Test Project")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_create_job_persists_defaults(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/fake.mp4",
        original_filename="fake.mp4",
    )

    assert job.id is not None
    assert job.project_id == project.id
    assert job.mode == "auto"
    assert job.status == "uploaded"
    assert job.segment_seconds == 120
    assert job.auto_caption is True
    assert job.reformat_vertical is False
    assert job.subtitle_font == "anton"


def test_create_job_persists_chosen_subtitle_font(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/fake.mp4",
        original_filename="fake.mp4",
        subtitle_font="poppins-bold",
    )

    assert job.subtitle_font == "poppins-bold"


def test_create_manual_job_starts_as_draft(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/fake.mp4",
        original_filename="fake.mp4",
        mode="manual",
    )

    assert job.mode == "manual"
    assert job.status == "draft"


def test_process_job_marks_failed_when_source_missing(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/does_not_exist.mp4",
        original_filename="does_not_exist.mp4",
    )

    result = clip_service.process_job(db, job)

    assert result.status == "failed"
    assert result.error


def test_save_manual_segments_persists_planned_clips(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/fake.mp4",
        original_filename="fake.mp4",
        mode="manual",
    )

    result = clip_service.save_manual_segments(db, job, [(0.0, 5.0), (10.0, 12.5)])

    assert len(result.clips) == 2
    assert all(c.status == "planned" for c in result.clips)
    assert [c.start_seconds for c in result.clips] == [0.0, 10.0]
    assert [c.end_seconds for c in result.clips] == [5.0, 12.5]


def test_save_manual_segments_replaces_previous_segments(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/fake.mp4",
        original_filename="fake.mp4",
        mode="manual",
    )
    clip_service.save_manual_segments(db, job, [(0.0, 5.0)])

    result = clip_service.save_manual_segments(db, job, [(1.0, 2.0), (3.0, 4.0)])

    assert len(result.clips) == 2


def test_process_manual_job_fails_with_no_segments(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/does_not_exist.mp4",
        original_filename="does_not_exist.mp4",
        mode="manual",
    )

    result = clip_service.process_manual_job(db, job)

    assert result.status == "failed"
    assert result.error


def test_process_manual_job_marks_failed_when_source_missing(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/does_not_exist.mp4",
        original_filename="does_not_exist.mp4",
        mode="manual",
    )
    clip_service.save_manual_segments(db, job, [(0.0, 5.0)])

    result = clip_service.process_manual_job(db, job)

    assert result.status == "completed_with_errors"
    assert result.clips[0].status == "failed"


def test_delete_job_removes_row_and_files(db, project, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video")
    clip_file = tmp_path / "clip0.mp4"
    clip_file.write_bytes(b"fake clip")
    subtitle_file = tmp_path / "clip0.srt"
    subtitle_file.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")

    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path=str(source),
        original_filename="source.mp4",
        mode="manual",
    )
    clip_service.save_manual_segments(db, job, [(0.0, 5.0)])
    job.clips[0].file_path = str(clip_file)
    job.clips[0].subtitle_path = str(subtitle_file)
    job.clips[0].status = "ready"
    db.commit()
    job_id = job.id

    clip_service.delete_job(db, job)

    assert db.get(type(job), job_id) is None
    assert not source.exists()
    assert not clip_file.exists()
    assert not subtitle_file.exists()


def test_delete_job_does_not_error_when_files_already_missing(db, project):
    job = clip_service.create_job(
        db,
        project_id=project.id,
        source_file_path="/tmp/never_existed.mp4",
        original_filename="never_existed.mp4",
    )

    clip_service.delete_job(db, job)  # should not raise
