"""Persistent player statistics, stored as a small JSON file."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from .game import Move, Outcome

ENV_VAR = "RPS_STATS_FILE"
FORMAT_VERSION = 1

_COUNTER_FIELDS = (
    "rounds_won",
    "rounds_lost",
    "rounds_tied",
    "matches_won",
    "matches_lost",
    "current_streak",
    "best_streak",
)


def default_stats_path() -> Path:
    """``$RPS_STATS_FILE`` if set, otherwise ``~/.rps/stats.json``."""
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".rps" / "stats.json"


def _check_count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")
    return value


@dataclass
class Stats:
    """Win/loss records plus how often each move was played.

    A tie neither extends nor breaks the current win streak.
    """

    rounds_won: int = 0
    rounds_lost: int = 0
    rounds_tied: int = 0
    matches_won: int = 0
    matches_lost: int = 0
    current_streak: int = 0
    best_streak: int = 0
    move_counts: Dict[str, int] = field(default_factory=dict)

    # -- derived values ------------------------------------------------------

    @property
    def rounds_played(self) -> int:
        return self.rounds_won + self.rounds_lost + self.rounds_tied

    @property
    def matches_played(self) -> int:
        return self.matches_won + self.matches_lost

    @property
    def win_rate(self) -> float:
        """Fraction of all rounds the player won (0.0 when none played)."""
        played = self.rounds_played
        return self.rounds_won / played if played else 0.0

    @property
    def favourite_move(self) -> Optional[Tuple[str, int]]:
        """``(move, times_played)`` for the most-played move, if any."""
        if not self.move_counts:
            return None
        # Sorting first makes ties resolve alphabetically, so output is stable.
        name = max(sorted(self.move_counts), key=lambda k: self.move_counts[k])
        return name, self.move_counts[name]

    # -- recording -----------------------------------------------------------

    def record_round(self, move: Move, outcome: Outcome) -> None:
        self.move_counts[move.value] = self.move_counts.get(move.value, 0) + 1
        if outcome is Outcome.WIN:
            self.rounds_won += 1
            self.current_streak += 1
            self.best_streak = max(self.best_streak, self.current_streak)
        elif outcome is Outcome.LOSE:
            self.rounds_lost += 1
            self.current_streak = 0
        else:
            self.rounds_tied += 1

    def record_match(self, player_won: bool) -> None:
        if player_won:
            self.matches_won += 1
        else:
            self.matches_lost += 1

    # -- persistence ---------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"version": FORMAT_VERSION}
        data.update({name: getattr(self, name) for name in _COUNTER_FIELDS})
        data["move_counts"] = dict(self.move_counts)
        return data

    @classmethod
    def from_dict(cls, data: Any) -> "Stats":
        """Build from parsed JSON, raising ``ValueError`` if it is malformed."""
        if not isinstance(data, dict):
            raise ValueError("statistics file must contain a JSON object")
        counters = {
            name: _check_count(data.get(name, 0), name) for name in _COUNTER_FIELDS
        }
        raw_moves = data.get("move_counts", {})
        if not isinstance(raw_moves, dict):
            raise ValueError("move_counts must be a JSON object")
        moves = {
            str(key): _check_count(value, f"move_counts[{key!r}]")
            for key, value in raw_moves.items()
        }
        return cls(move_counts=moves, **counters)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "Stats":
        """Load stats from ``path``; never raises for a missing or bad file.

        A missing file gives fresh stats. A corrupt file is moved aside to
        ``<name>.corrupt`` (so nothing is silently destroyed) and fresh stats
        are returned.
        """
        path = Path(path)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return cls()
        try:
            return cls.from_dict(json.loads(raw))
        except ValueError:  # includes json.JSONDecodeError
            try:
                os.replace(path, path.with_name(path.name + ".corrupt"))
            except OSError:
                pass
            return cls()

    def save(self, path: Union[str, Path]) -> None:
        """Write stats to ``path`` atomically (write a temp file, then rename)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        try:
            tmp.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise
