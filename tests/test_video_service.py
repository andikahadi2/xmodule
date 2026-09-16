import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.clipper.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.video_ai.models  # noqa: F401 ensure all tables are registered on Base.metadata
from app.core.database import Base
from app.models.audio import AudioAsset
from app.models.content import Content
from app.models.media import MediaAsset
from app.models.script import ContentScript
from app.services import video_service

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


def test_create_pending_video_requires_media_audio_script(db):
    content = Content(product_id=1)
    db.add(content)
    db.commit()
    db.refresh(content)

    with pytest.raises(ValueError):
        video_service.create_pending_video(db, content)


def test_create_pending_video_sets_processing_status(db):
    content = Content(product_id=1)
    db.add(content)
    db.commit()
    db.refresh(content)

    db.add(MediaAsset(content_id=content.id, provider="local", query="q", file_path="/tmp/a.jpg", source_url="/tmp/a.jpg"))
    db.add(AudioAsset(content_id=content.id, provider="edge", voice="v", language="id", file_path="/tmp/a.mp3", duration=10.0))
    db.add(ContentScript(content_id=content.id, script_text="hi", hook="h", cta="c", duration=30, ai_provider="p", ai_model="m"))
    db.commit()
    db.refresh(content)

    video = video_service.create_pending_video(db, content)

    assert video.id is not None
    assert video.status == "processing"
    assert video.file_path is None
