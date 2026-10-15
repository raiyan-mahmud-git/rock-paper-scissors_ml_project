"""Computer opponents.

Every strategy follows the same two-step protocol, which guarantees the AI
never "peeks" at the move it is about to play against:

1. ``choose()``  - pick a move without knowing the player's move this round.
2. ``observe()`` - learn from the player's move once the round is decided.
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from collections import Counter, defaultdict, deque
from typing import Deque, Dict, Optional, Tuple

from .game import Move, RuleSet

DIFFICULTIES = ("easy", "medium", "hard")


class Strategy(ABC):
    """Base class for computer opponents."""

    name = "strategy"

    def __init__(self, ruleset: RuleSet, rng: Optional[random.Random] = None) -> None:
        self.ruleset = ruleset
        self.rng = rng if rng is not None else random.Random()

    @abstractmethod
    def choose(self) -> Move:
        """Return the computer's move for the coming round."""

    def observe(self, player_move: Move) -> None:
        """Record the player's move after a round. Default: ignore it."""

    # helpers shared by the concrete strategies

    def _random_move(self) -> Move:
        return self.rng.choice(self.ruleset.moves)

    def _counter(self, predicted: Move) -> Move:
        """A move that beats ``predicted`` (random pick if several do)."""
        return self.rng.choice(self.ruleset.counters(predicted))


class RandomStrategy(Strategy):
    """Plays uniformly at random. Can't be exploited, but can't exploit you."""

    name = "random"

    def choose(self) -> Move:
        return self._random_move()


class FrequencyStrategy(Strategy):
    """Counters whichever move the player has used most, favouring recent rounds.

    Each observed move adds 1 to its weight after all weights are multiplied by
    ``decay``. ``decay=1.0`` is a plain all-time frequency count; smaller values
    forget old habits faster, so the AI adapts when you change your style.
    """

    name = "frequency"

    def __init__(
        self,
        ruleset: RuleSet,
        rng: Optional[random.Random] = None,
        decay: float = 0.9,
    ) -> None:
        super().__init__(ruleset, rng)
        if not 0 < decay <= 1:
            raise ValueError("decay must be in the range (0, 1]")
        self.decay = decay
        self.weights: Dict[Move, float] = {m: 0.0 for m in ruleset.moves}

    def observe(self, player_move: Move) -> None:
        for move in self.weights:
            self.weights[move] *= self.decay
        self.weights[player_move] += 1.0

    def predict(self) -> Optional[Move]:
        """The player's most likely next move, or ``None`` with no history."""
        best = max(self.weights.values())
        if best <= 0:
            return None
        candidates = [m for m, w in self.weights.items() if math.isclose(w, best)]
        return self.rng.choice(candidates)

    def choose(self) -> Move:
        predicted = self.predict()
        if predicted is None:
            return self._random_move()
        return self._counter(predicted)


class MarkovStrategy(Strategy):
    """Looks for patterns in the player's last ``order`` moves.

    It remembers what the player played after every sequence of ``order``
    moves and predicts the most common follow-up. When it hasn't seen the
    current sequence before it falls back to :class:`FrequencyStrategy`.
    ``epsilon`` is the chance of playing a random move instead, so the AI
    can't be predicted perfectly in return.
    """

    name = "markov"

    def __init__(
        self,
        ruleset: RuleSet,
        rng: Optional[random.Random] = None,
        order: int = 2,
        epsilon: float = 0.1,
    ) -> None:
        super().__init__(ruleset, rng)
        if order < 1:
            raise ValueError("order must be at least 1")
        if not 0 <= epsilon <= 1:
            raise ValueError("epsilon must be between 0 and 1")
        self.order = order
        self.epsilon = epsilon
        self.history: Deque[Move] = deque(maxlen=order)
        self.table: Dict[Tuple[Move, ...], Counter] = defaultdict(Counter)
        self._fallback = FrequencyStrategy(ruleset, self.rng)

    def observe(self, player_move: Move) -> None:
        if len(self.history) == self.order:
            self.table[tuple(self.history)][player_move] += 1
        self.history.append(player_move)
        self._fallback.observe(player_move)

    def predict(self) -> Optional[Move]:
        if len(self.history) == self.order:
            counts = self.table.get(tuple(self.history))
            if counts:
                best = max(counts.values())
                return self.rng.choice([m for m, c in counts.items() if c == best])
        return self._fallback.predict()

    def choose(self) -> Move:
        if self.rng.random() < self.epsilon:
            return self._random_move()
        predicted = self.predict()
        if predicted is None:
            return self._random_move()
        return self._counter(predicted)


def create_strategy(
    difficulty: str, ruleset: RuleSet, rng: Optional[random.Random] = None
) -> Strategy:
    """Build the opponent for a difficulty level."""
    if difficulty == "easy":
        return RandomStrategy(ruleset, rng)
    if difficulty == "medium":
        return FrequencyStrategy(ruleset, rng, decay=0.9)
    if difficulty == "hard":
        return MarkovStrategy(ruleset, rng, order=2, epsilon=0.1)
    raise ValueError(
        f"unknown difficulty {difficulty!r}; choose from {', '.join(DIFFICULTIES)}"
    )
