"""Tests for FastAPI web interface."""

import pytest
from fastapi.testclient import TestClient

from rps.web.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_play_round_classic(client):
    response = client.post(
        "/api/play",
        json={
            "move": "rock",
            "difficulty": "hard",
            "ruleset": "classic",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["player_move"] == "rock"
    assert data["computer_move"] in ["rock", "paper", "scissors"]
    assert data["outcome"] in ["win", "lose", "tie"]
    assert data["stats"]["rounds_played"] == 1


def test_play_round_extended(client):
    response = client.post(
        "/api/play",
        json={
            "move": "spock",
            "difficulty": "medium",
            "ruleset": "extended",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["player_move"] == "spock"
    assert data["computer_move"] in ["rock", "paper", "scissors", "lizard", "spock"]


def test_invalid_move_rejected(client):
    response = client.post(
        "/api/play",
        json={
            "move": "fireball",
            "difficulty": "hard",
            "ruleset": "classic",
        },
    )
    assert response.status_code == 400


def test_extended_move_in_classic_rejected(client):
    response = client.post(
        "/api/play",
        json={
            "move": "lizard",
            "difficulty": "hard",
            "ruleset": "classic",
        },
    )
    assert response.status_code == 400


def test_reset_endpoint(client):
    play_resp = client.post(
        "/api/play",
        json={"move": "rock", "difficulty": "hard", "ruleset": "classic"},
    )
    sid = play_resp.json()["session_id"]

    reset_resp = client.post(
        "/api/reset",
        json={"session_id": sid, "difficulty": "hard", "ruleset": "classic"},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["stats"]["rounds_played"] == 0


def test_serve_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "RPS" in response.text
