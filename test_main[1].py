import os

os.environ["DATABASE_URL"] = "sqlite:///./test_notes.db"

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_db():
    main.Base.metadata.drop_all(main.engine)
    main.Base.metadata.create_all(main.engine)
    yield


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_read_note():
    r = client.post("/notes", json={"title": "Plan", "content": "Learn FastAPI"})
    assert r.status_code == 201
    note_id = r.json()["id"]
    assert client.get(f"/notes/{note_id}").json()["title"] == "Plan"
    assert len(client.get("/notes").json()) == 1


def test_validation_error():
    assert client.post("/notes", json={"title": "", "content": "x"}).status_code == 422


def test_missing_note_returns_404():
    assert client.get("/notes/999").status_code == 404


def test_delete_note():
    note_id = client.post("/notes", json={"title": "a", "content": "b"}).json()["id"]
    assert client.delete(f"/notes/{note_id}").status_code == 204
    assert client.get(f"/notes/{note_id}").status_code == 404


def test_summarize_uses_llm(monkeypatch):
    monkeypatch.setattr(main, "call_llm", lambda text: "A short summary.")
    note_id = client.post("/notes", json={"title": "a", "content": "long text"}).json()["id"]
    r = client.post(f"/notes/{note_id}/summarize")
    assert r.status_code == 200
    assert r.json()["summary"] == "A short summary."
