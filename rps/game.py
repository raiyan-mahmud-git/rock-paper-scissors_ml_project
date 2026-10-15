"""Core rules for Rock Paper Scissors (plus the Lizard-Spock extension).

Nothing in this module does any I/O, which keeps it trivial to test and easy
to reuse from a different front end (GUI, web app, chat bot, ...).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Tuple


class Move(str, Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"
    LIZARD = "lizard"
    SPOCK = "spock"

    @property
    def label(self) -> str:
        """Human-friendly name, e.g. ``"Rock"``."""
        return self.value.capitalize()


class Outcome(Enum):
    """Result of a round from the player's point of view."""

    WIN = "win"
    LOSE = "lose"
    TIE = "tie"


# Short aliases accepted when typing a move.
SHORTCUTS: Dict[Move, str] = {
    Move.ROCK: "r",
    Move.PAPER: "p",
    Move.SCISSORS: "s",
    Move.LIZARD: "l",
    Move.SPOCK: "sp",
}

# (winner, loser) -> the verb used to describe the win.
VERBS: Dict[Tuple[Move, Move], str] = {
    (Move.ROCK, Move.SCISSORS): "crushes",
    (Move.ROCK, Move.LIZARD): "crushes",
    (Move.PAPER, Move.ROCK): "covers",
    (Move.PAPER, Move.SPOCK): "disproves",
    (Move.SCISSORS, Move.PAPER): "cuts",
    (Move.SCISSORS, Move.LIZARD): "decapitates",
    (Move.LIZARD, Move.SPOCK): "poisons",
    (Move.LIZARD, Move.PAPER): "eats",
    (Move.SPOCK, Move.SCISSORS): "smashes",
    (Move.SPOCK, Move.ROCK): "vaporizes",
}


@dataclass(frozen=True)
class RuleSet:
    """A named set of moves and which moves each one beats."""

    name: str
    moves: Tuple[Move, ...]
    beats: Dict[Move, FrozenSet[Move]]

    def decide(self, player: Move, computer: Move) -> Outcome:
        """Return the outcome of ``player`` versus ``computer``."""
        if player == computer:
            return Outcome.TIE
        if computer in self.beats[player]:
            return Outcome.WIN
        return Outcome.LOSE

    def counters(self, move: Move) -> Tuple[Move, ...]:
        """All moves in this rule set that beat ``move``."""
        return tuple(m for m in self.moves if move in self.beats[m])


CLASSIC = RuleSet(
    name="classic",
    moves=(Move.ROCK, Move.PAPER, Move.SCISSORS),
    beats={
        Move.ROCK: frozenset({Move.SCISSORS}),
        Move.PAPER: frozenset({Move.ROCK}),
        Move.SCISSORS: frozenset({Move.PAPER}),
    },
)

EXTENDED = RuleSet(
    name="extended",
    moves=(Move.ROCK, Move.PAPER, Move.SCISSORS, Move.LIZARD, Move.SPOCK),
    beats={
        Move.ROCK: frozenset({Move.SCISSORS, Move.LIZARD}),
        Move.PAPER: frozenset({Move.ROCK, Move.SPOCK}),
        Move.SCISSORS: frozenset({Move.PAPER, Move.LIZARD}),
        Move.LIZARD: frozenset({Move.PAPER, Move.SPOCK}),
        Move.SPOCK: frozenset({Move.SCISSORS, Move.ROCK}),
    },
)

RULESETS: Dict[str, RuleSet] = {CLASSIC.name: CLASSIC, EXTENDED.name: EXTENDED}


def parse_move(text: str, ruleset: RuleSet) -> Optional[Move]:
    """Turn user input into a move, or ``None`` if it isn't one.

    Accepts the full name (``rock``), a shortcut (``r``, ``sp``), the move's
    number in the menu (``1``) or any unique prefix (``sci``).
    """
    token = text.strip().lower()
    if not token:
        return None

    for move in ruleset.moves:
        if token in (move.value, SHORTCUTS[move]):
            return move

    if token.isdecimal():
        index = int(token) - 1
        if 0 <= index < len(ruleset.moves):
            return ruleset.moves[index]
        return None

    matches = [m for m in ruleset.moves if m.value.startswith(token)]
    return matches[0] if len(matches) == 1 else None


@dataclass(frozen=True)
class RoundResult:
    player: Move
    computer: Move
    outcome: Outcome

    @property
    def description(self) -> str:
        """Plain-English summary, e.g. ``"Rock crushes Scissors"``."""
        if self.outcome is Outcome.TIE:
            return f"Both chose {self.player.label}"
        if self.outcome is Outcome.WIN:
            winner, loser = self.player, self.computer
        else:
            winner, loser = self.computer, self.player
        return f"{winner.label} {VERBS[(winner, loser)]} {loser.label}"


@dataclass
class Match:
    """Score-keeping for a series of rounds.

    ``target_wins`` is the number of round wins needed to take the match;
    ``None`` makes an endless match that never finishes on its own.
    """

    ruleset: RuleSet
    target_wins: Optional[int] = None
    player_score: int = 0
    computer_score: int = 0
    ties: int = 0
    rounds: List[RoundResult] = field(default_factory=list)

    @classmethod
    def best_of(cls, ruleset: RuleSet, games: int) -> "Match":
        """Create a best-of-``games`` match (``games`` must be odd)."""
        if games < 1 or games % 2 == 0:
            raise ValueError("best-of length must be a positive odd number")
        return cls(ruleset, target_wins=games // 2 + 1)

    @property
    def is_over(self) -> bool:
        if self.target_wins is None:
            return False
        return max(self.player_score, self.computer_score) >= self.target_wins

    @property
    def player_won(self) -> Optional[bool]:
        """``True``/``False`` once the match is over, ``None`` before that."""
        if not self.is_over:
            return None
        return self.player_score > self.computer_score

    def play(self, player: Move, computer: Move) -> RoundResult:
        """Play one round and update the score."""
        if self.is_over:
            raise ValueError("this match is already over")
        for move in (player, computer):
            if move not in self.ruleset.moves:
                raise ValueError(
                    f"{move.value!r} is not a move in {self.ruleset.name} mode"
                )

        outcome = self.ruleset.decide(player, computer)
        if outcome is Outcome.WIN:
            self.player_score += 1
        elif outcome is Outcome.LOSE:
            self.computer_score += 1
        else:
            self.ties += 1

        result = RoundResult(player, computer, outcome)
        self.rounds.append(result)
        return result
