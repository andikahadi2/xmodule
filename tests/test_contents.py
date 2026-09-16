import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.clipper.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.models  # noqa: F401 ensure all tables are registered on Base.metadata
import app.video_ai.models  # noqa: F401 ensure all tables are registered on Base.metadata
from app.core.database import Base
from app.models.content import Content
from app.models.product import Product
from app.providers.ai.base import AIProvider, AIProviderError
from app.services import content_service, script_service

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


class FakeIdeaProvider(AIProvider):
    name = "fake"

    def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        return json.dumps(
            [
                {
                    "hook": "Kenapa masih buang uang buat ini?",
                    "angle": "problem",
                    "target_audience": "ibu rumah tangga",
                    "content_type": "problem_solution",
                    "estimated_duration": 30,
                },
                {
                    "hook": "Produk ini keren",
                    "angle": "generic",
                    "target_audience": "umum",
                    "content_type": "product_demo",
                    "estimated_duration": 25,
                },
            ]
        )


class FakeScriptProvider(AIProvider):
    name = "fake"

    def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "script_text": "Hook...\nMasalah...\nSolusi...\nBenefit...\nCTA...",
                "hook": "Kenapa masih buang uang buat ini?",
                "cta": "Cek link di bio.",
            }
        )


class FailingProvider(AIProvider):
    name = "fake"

    def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        raise AIProviderError("boom")


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
def product(db):
    p = Product(name="Botol Minum", price=25000, affiliate_url="https://example.com/p")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_generate_content_ideas_picks_best_and_persists(db, product, monkeypatch):
    monkeypatch.setattr(content_service, "get_ai_provider", lambda name: FakeIdeaProvider())

    content = content_service.generate_content_ideas(db, product)

    assert content.status == "IDEA"
    assert len(content.ideas) == 2
    selected = [i for i in content.ideas if i.status == "selected"]
    assert len(selected) == 1
    assert selected[0].content_type == "problem_solution"


def test_generate_content_ideas_raises_on_provider_error(db, product, monkeypatch):
    monkeypatch.setattr(content_service, "get_ai_provider", lambda name: FailingProvider())

    with pytest.raises(AIProviderError):
        content_service.generate_content_ideas(db, product)


def test_generate_script_from_selected_idea(db, product, monkeypatch):
    monkeypatch.setattr(content_service, "get_ai_provider", lambda name: FakeIdeaProvider())
    content = content_service.generate_content_ideas(db, product)
    selected_idea = next(i for i in content.ideas if i.status == "selected")

    monkeypatch.setattr(script_service, "get_ai_provider", lambda name: FakeScriptProvider())
    script = script_service.generate_script(db, content, selected_idea)

    assert script.version == 1
    assert script.cta == "Cek link di bio."
    db.refresh(content)
    assert content.status == "SCRIPT_GENERATED"


def test_generate_script_second_call_increments_version(db, product, monkeypatch):
    monkeypatch.setattr(content_service, "get_ai_provider", lambda name: FakeIdeaProvider())
    content = content_service.generate_content_ideas(db, product)
    selected_idea = next(i for i in content.ideas if i.status == "selected")

    monkeypatch.setattr(script_service, "get_ai_provider", lambda name: FakeScriptProvider())
    script_service.generate_script(db, content, selected_idea)
    db.refresh(content)
    second = script_service.generate_script(db, content, selected_idea)

    assert second.version == 2
