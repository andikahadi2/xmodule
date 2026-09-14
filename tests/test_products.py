from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

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


def test_create_and_list_product():
    resp = client.post(
        "/api/products",
        json={"name": "Botol Minum", "price": 25000, "affiliate_url": "https://example.com/p/1"},
    )
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    resp = client.get("/api/products")
    assert resp.status_code == 200
    assert any(p["id"] == product_id for p in resp.json())


def test_get_update_delete_product():
    resp = client.post(
        "/api/products",
        json={"name": "Kabel USB", "price": 15000, "affiliate_url": "https://example.com/p/2"},
    )
    product_id = resp.json()["id"]

    resp = client.get(f"/api/products/{product_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Kabel USB"

    resp = client.put(f"/api/products/{product_id}", json={"price": 18000})
    assert resp.status_code == 200
    assert resp.json()["price"] == 18000

    resp = client.delete(f"/api/products/{product_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/products/{product_id}")
    assert resp.status_code == 404


def test_get_missing_product_404():
    resp = client.get("/api/products/999999")
    assert resp.status_code == 404
