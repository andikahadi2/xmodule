from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.audio import AudioAsset
from app.models.content import Content
from app.models.media import MediaAsset
from app.models.script import ContentScript
from app.models.video import Video

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _make_content_with_video(db, status="ready", error=None):
    content = Content(product_id=1)
    db.add(content)
    db.commit()
    db.refresh(content)

    db.add(MediaAsset(content_id=content.id, provider="local", query="q", file_path="/tmp/a.jpg", source_url="/tmp/a.jpg"))
    db.add(AudioAsset(content_id=content.id, provider="edge", voice="v", language="id", file_path="/tmp/a.mp3", duration=10.0))
    db.add(ContentScript(content_id=content.id, script_text="hi", hook="h", cta="c", duration=30, ai_provider="p", ai_model="m"))
    video = Video(content_id=content.id, status=status, error=error, file_path="/tmp/out.mp4" if status == "ready" else None)
    db.add(video)
    db.commit()
    db.refresh(content)
    db.refresh(video)
    return content, video


def test_get_video_exposes_status_and_error():
    db = TestSession()
    try:
        _, video = _make_content_with_video(db, status="failed", error="ffmpeg exploded")
    finally:
        db.close()

    resp = client.get(f"/api/contents/videos/{video.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error"] == "ffmpeg exploded"


def test_get_missing_video_404():
    resp = client.get("/api/contents/videos/999999")
    assert resp.status_code == 404


def test_content_out_includes_videos():
    db = TestSession()
    try:
        content, video = _make_content_with_video(db, status="ready")
    finally:
        db.close()

    resp = client.get(f"/api/contents/{content.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["videos"]) == 1
    assert body["videos"][0]["id"] == video.id
    assert body["videos"][0]["status"] == "ready"


def test_approve_requires_ready_status():
    db = TestSession()
    try:
        _, video = _make_content_with_video(db, status="processing")
    finally:
        db.close()

    resp = client.post(f"/api/contents/videos/{video.id}/approve")
    assert resp.status_code == 400
