"""Tests for the Flask API endpoints."""

import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_generate_valid_prompt(client):
    resp = client.post("/api/generate", json={"prompt": "dreamy and romantic"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["fallback_notes"]) > 0


def test_generate_empty_prompt_returns_400(client):
    resp = client.post("/api/generate", json={"prompt": ""})
    assert resp.status_code == 400


def test_midi_endpoint_returns_a_file(client):
    resp = client.post("/api/midi", json={"prompt": "upbeat and playful"})
    assert resp.status_code == 200
    assert resp.data[:4] == b"MThd"
