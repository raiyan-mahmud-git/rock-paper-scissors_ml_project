import random

import pytest

from rps.ai import (
    FrequencyStrategy,
    MarkovStrategy,
    RandomStrategy,
    create_strategy,
)
from rps.game import CLASSIC, EXTENDED, Move, Outcome


def rng(seed=0):
    return random.Random(seed)


def beats(winner, loser, ruleset=CLASSIC):
    return ruleset.decide(winner, loser) is Outcome.WIN


class TestRandomStrategy:
    def test_only_returns_legal_moves(self):
        ai = RandomStrategy(CLASSIC, rng())
        assert {ai.choose() for _ in range(200)} <= set(CLASSIC.moves)

    def test_uses_every_move_eventually(self):
        ai = RandomStrategy(EXTENDED, rng())
        assert {ai.choose() for _ in range(500)} == set(EXTENDED.moves)

    def test_same_seed_same_sequence(self):
        a = RandomStrategy(CLASSIC, rng(42))
        b = RandomStrategy(CLASSIC, rng(42))
        assert [a.choose() for _ in range(20)] == [b.choose() for _ in range(20)]


class TestFrequencyStrategy:
    def test_counters_a_habitual_move(self):
        ai = FrequencyStrategy(CLASSIC, rng())
        for _ in range(5):
            ai.observe(Move.ROCK)
        assert all(ai.choose() is Move.PAPER for _ in range(20))

    def test_counters_extended_move_with_either_counter(self):
        ai = FrequencyStrategy(EXTENDED, rng())
        for _ in range(5):
            ai.observe(Move.ROCK)
        choices = {ai.choose() for _ in range(100)}
        assert choices <= {Move.PAPER, Move.SPOCK}
        assert all(beats(c, Move.ROCK, EXTENDED) for c in choices)

    def test_no_history_means_random_but_legal(self):
        ai = FrequencyStrategy(CLASSIC, rng())
        assert ai.predict() is None
        assert ai.choose() in CLASSIC.moves

    def test_adapts_when_the_player_changes_habit(self):
        ai = FrequencyStrategy(CLASSIC, rng(), decay=0.8)
        for _ in range(10):
            ai.observe(Move.ROCK)
        for _ in range(10):
            ai.observe(Move.SCISSORS)
        assert ai.predict() is Move.SCISSORS
        assert all(ai.choose() is Move.ROCK for _ in range(20))

    def test_no_decay_is_a_plain_count(self):
        ai = FrequencyStrategy(CLASSIC, rng(), decay=1.0)
        for _ in range(10):
            ai.observe(Move.ROCK)
        for _ in range(5):
            ai.observe(Move.SCISSORS)
        assert ai.predict() is Move.ROCK

    @pytest.mark.parametrize("decay", [0, -0.5, 1.5])
    def test_rejects_bad_decay(self, decay):
        with pytest.raises(ValueError):
            FrequencyStrategy(CLASSIC, rng(), decay=decay)


class TestMarkovStrategy:
    def test_learns_a_repeating_cycle(self):
        ai = MarkovStrategy(CLASSIC, rng(), order=2, epsilon=0.0)
        cycle = [Move.ROCK, Move.PAPER, Move.SCISSORS]
        for i in range(30):
            ai.observe(cycle[i % 3])
        # History ends ...rock, paper, scissors, so the player plays rock next.
        assert ai.predict() is Move.ROCK
        assert all(ai.choose() is Move.PAPER for _ in range(20))

    def test_beats_a_cycle_over_a_whole_game(self):
        ai = MarkovStrategy(CLASSIC, rng(1), order=2, epsilon=0.0)
        cycle = [Move.ROCK, Move.PAPER, Move.SCISSORS]
        wins = 0
        for i in range(120):
            player = cycle[i % 3]
            computer = ai.choose()
            ai.observe(player)
            if i >= 20 and beats(computer, player):
                wins += 1
        assert wins == 100  # perfect once it has seen the pattern

    def test_falls_back_to_frequency_for_unseen_sequences(self):
        ai = MarkovStrategy(CLASSIC, rng(), order=2, epsilon=0.0)
        ai.observe(Move.ROCK)
        ai.observe(Move.ROCK)
        # Sequence (rock, rock) has never been followed by anything yet.
        assert ai.predict() is Move.ROCK

    def test_epsilon_one_is_fully_random(self):
        ai = MarkovStrategy(CLASSIC, rng(), epsilon=1.0)
        for _ in range(10):
            ai.observe(Move.ROCK)
        assert {ai.choose() for _ in range(200)} == set(CLASSIC.moves)

    def test_no_history_is_legal(self):
        ai = MarkovStrategy(CLASSIC, rng(), epsilon=0.0)
        assert ai.choose() in CLASSIC.moves

    def test_rejects_bad_parameters(self):
        with pytest.raises(ValueError):
            MarkovStrategy(CLASSIC, rng(), order=0)
        with pytest.raises(ValueError):
            MarkovStrategy(CLASSIC, rng(), epsilon=1.5)


class TestCreateStrategy:
    @pytest.mark.parametrize(
        "difficulty,cls",
        [("easy", RandomStrategy), ("medium", FrequencyStrategy), ("hard", MarkovStrategy)],
    )
    def test_difficulty_mapping(self, difficulty, cls):
        assert isinstance(create_strategy(difficulty, CLASSIC, rng()), cls)

    def test_unknown_difficulty(self):
        with pytest.raises(ValueError, match="unknown difficulty"):
            create_strategy("impossible", CLASSIC)

    def test_ai_cannot_see_the_current_move(self):
        # choose() takes no arguments, so peeking is impossible by construction.
        ai = create_strategy("hard", CLASSIC, rng())
        with pytest.raises(TypeError):
            ai.choose(Move.ROCK)
