"""Web backend for Rock Paper Scissors using FastAPI."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rps.ai import DIFFICULTIES, Strategy, create_strategy
from rps.game import (
    CLASSIC,
    EXTENDED,
    Move,
    Outcome,
    RuleSet,
    VERBS,
    RULESETS,
)
from rps.stats import Stats

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Rock Paper Scissors AI Arena",
    description="Interactive Rock-Paper-Scissors (and Lizard-Spock) powered by Markov Chain AI.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlayRequest(BaseModel):
    session_id: Optional[str] = None
    move: str
    difficulty: str = "hard"
    ruleset: str = "classic"


class ResetRequest(BaseModel):
    session_id: Optional[str] = None
    difficulty: str = "hard"
    ruleset: str = "classic"


class GameSession:
    """Maintains a single visitor's game state and AI memory."""

    def __init__(self, ruleset_name: str = "classic", difficulty: str = "hard") -> None:
        self.ruleset_name = ruleset_name if ruleset_name in RULESETS else "classic"
        self.difficulty = difficulty if difficulty in DIFFICULTIES else "hard"
        self.ruleset: RuleSet = RULESETS[self.ruleset_name]
        self.strategy: Strategy = create_strategy(self.difficulty, self.ruleset)
        self.stats: Stats = Stats()
        self.history: List[Dict[str, Any]] = []
        self.last_active: float = time.time()

    def update_config(self, ruleset_name: str, difficulty: str) -> None:
        changed = False
        if ruleset_name in RULESETS and ruleset_name != self.ruleset_name:
            self.ruleset_name = ruleset_name
            self.ruleset = RULESETS[self.ruleset_name]
            changed = True
        if difficulty in DIFFICULTIES and difficulty != self.difficulty:
            self.difficulty = difficulty
            changed = True
        if changed:
            self.strategy = create_strategy(self.difficulty, self.ruleset)


# In-memory store for visitor sessions with automatic TTL cleanup
_SESSIONS: Dict[str, GameSession] = {}
SESSION_TTL_SECONDS = 3600 * 4  # 4 hours per inactive session


def _get_or_create_session(session_id: Optional[str], ruleset: str, difficulty: str) -> tuple[str, GameSession]:
    now = time.time()
    # Periodic sweep of expired sessions
    if len(_SESSIONS) > 500:
        expired = [sid for sid, sess in _SESSIONS.items() if now - sess.last_active > SESSION_TTL_SECONDS]
        for sid in expired:
            _SESSIONS.pop(sid, None)

    if not session_id or session_id not in _SESSIONS:
        session_id = str(uuid.uuid4())
        session = GameSession(ruleset_name=ruleset, difficulty=difficulty)
        _SESSIONS[session_id] = session
    else:
        session = _SESSIONS[session_id]
        session.update_config(ruleset, difficulty)

    session.last_active = now
    return session_id, session


def _describe_result(player: Move, computer: Move, outcome: Outcome) -> str:
    if outcome is Outcome.TIE:
        return f"Both players chose {player.label}. It's a tie!"
    if outcome is Outcome.WIN:
        verb = VERBS.get((player, computer), "beats")
        return f"{player.label} {verb} {computer.label}. You win!"
    verb = VERBS.get((computer, player), "beats")
    return f"{computer.label} {verb} {player.label}. AI wins!"


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/play")
def play_round(req: PlayRequest) -> Dict[str, Any]:
    session_id, session = _get_or_create_session(req.session_id, req.ruleset, req.difficulty)

    # Validate player move
    try:
        player_move = Move(req.move.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid move: {req.move!r}")

    if player_move not in session.ruleset.moves:
        raise HTTPException(
            status_code=400,
            detail=f"{player_move.label} is not permitted in {session.ruleset_name} mode",
        )

    # 1. AI chooses WITHOUT peeking
    computer_move = session.strategy.choose()

    # 2. Decide outcome
    outcome = session.ruleset.decide(player_move, computer_move)

    # 3. AI observes the player's move to adapt
    session.strategy.observe(player_move)

    # 4. Record statistics
    session.stats.record_round(player_move, outcome)

    # 5. Build friendly commentary
    commentary = _describe_result(player_move, computer_move, outcome)

    # Record in history
    round_record = {
        "round": session.stats.rounds_played,
        "player_move": player_move.value,
        "computer_move": computer_move.value,
        "outcome": outcome.value,
        "commentary": commentary,
    }
    session.history.append(round_record)
    if len(session.history) > 50:
        session.history.pop(0)

    # AI strategy insight for UI
    ai_status = "Observing your patterns"
    if session.difficulty == "hard":
        ai_status = f"Markov Order 2 ({len(session.history)} moves analyzed)"
    elif session.difficulty == "medium":
        ai_status = "Frequency Decay (weighting your recent moves)"
    else:
        ai_status = "Pure Random (unexploitable)"

    return {
        "session_id": session_id,
        "player_move": player_move.value,
        "computer_move": computer_move.value,
        "outcome": outcome.value,
        "commentary": commentary,
        "ai_status": ai_status,
        "stats": {
            "rounds_played": session.stats.rounds_played,
            "rounds_won": session.stats.rounds_won,
            "rounds_lost": session.stats.rounds_lost,
            "rounds_tied": session.stats.rounds_tied,
            "win_rate": round(session.stats.win_rate * 100, 1),
            "current_streak": session.stats.current_streak,
            "best_streak": session.stats.best_streak,
            "move_counts": session.stats.move_counts,
        },
    }


@app.post("/api/reset")
def reset_game(req: ResetRequest) -> Dict[str, Any]:
    session_id = req.session_id or str(uuid.uuid4())
    session = GameSession(ruleset_name=req.ruleset, difficulty=difficulty) if 'difficulty' in locals() else GameSession(ruleset_name=req.ruleset, difficulty=req.difficulty)
    _SESSIONS[session_id] = session
    return {
        "session_id": session_id,
        "message": "Game reset successfully",
        "stats": {
            "rounds_played": 0,
            "rounds_won": 0,
            "rounds_lost": 0,
            "rounds_tied": 0,
            "win_rate": 0.0,
            "current_streak": 0,
            "best_streak": 0,
            "move_counts": {},
        },
    }


# Serve static web frontend
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index() -> Any:
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h2>Rock Paper Scissors API running. Frontend static files pending.</h2>")
