import itertools

import pytest

from rps.game import (
    CLASSIC,
    EXTENDED,
    VERBS,
    Match,
    Move,
    Outcome,
    RoundResult,
    parse_move,
)


class TestRules:
    @pytest.mark.parametrize(
        "winner,loser",
        [("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")],
    )
    def test_classic_wins(self, winner, loser):
        assert CLASSIC.decide(Move(winner), Move(loser)) is Outcome.WIN
        assert CLASSIC.decide(Move(loser), Move(winner)) is Outcome.LOSE

    @pytest.mark.parametrize("ruleset", [CLASSIC, EXTENDED])
    def test_same_move_ties(self, ruleset):
        for move in ruleset.moves:
            assert ruleset.decide(move, move) is Outcome.TIE

    def test_extended_is_balanced(self):
        # Every move beats exactly two others and loses to exactly two others.
        for move in EXTENDED.moves:
            assert len(EXTENDED.beats[move]) == 2
            assert len(EXTENDED.counters(move)) == 2

    @pytest.mark.parametrize("ruleset", [CLASSIC, EXTENDED])
    def test_exactly_one_winner_per_pair(self, ruleset):
        for a, b in itertools.combinations(ruleset.moves, 2):
            first = ruleset.decide(a, b)
            second = ruleset.decide(b, a)
            assert {first, second} == {Outcome.WIN, Outcome.LOSE}

    def test_every_extended_win_has_a_verb(self):
        for winner, losers in EXTENDED.beats.items():
            for loser in losers:
                assert (winner, loser) in VERBS

    def test_counters(self):
        assert CLASSIC.counters(Move.ROCK) == (Move.PAPER,)
        assert set(EXTENDED.counters(Move.ROCK)) == {Move.PAPER, Move.SPOCK}


class TestParseMove:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("rock", Move.ROCK),
            ("  PAPER ", Move.PAPER),
            ("s", Move.SCISSORS),
            ("sci", Move.SCISSORS),
            ("1", Move.ROCK),
            ("3", Move.SCISSORS),
        ],
    )
    def test_classic_inputs(self, text, expected):
        assert parse_move(text, CLASSIC) is expected

    @pytest.mark.parametrize("text", ["", "   ", "banana", "0", "4", "-1", "ro ck"])
    def test_classic_rejects(self, text):
        assert parse_move(text, CLASSIC) is None

    def test_classic_does_not_accept_extended_moves(self):
        assert parse_move("lizard", CLASSIC) is None
        assert parse_move("spock", CLASSIC) is None

    def test_extended_shortcuts_are_unambiguous(self):
        assert parse_move("s", EXTENDED) is Move.SCISSORS
        assert parse_move("sp", EXTENDED) is Move.SPOCK
        assert parse_move("l", EXTENDED) is Move.LIZARD
        assert parse_move("5", EXTENDED) is Move.SPOCK

    def test_unique_prefixes_resolve(self):
        assert parse_move("sc", EXTENDED) is Move.SCISSORS
        assert parse_move("spo", EXTENDED) is Move.SPOCK

    def test_prefix_that_matches_nothing_is_rejected(self):
        assert parse_move("sx", EXTENDED) is None


class TestRoundResult:
    def test_description_win(self):
        result = RoundResult(Move.ROCK, Move.SCISSORS, Outcome.WIN)
        assert result.description == "Rock crushes Scissors"

    def test_description_loss_names_the_computer_move_first(self):
        result = RoundResult(Move.ROCK, Move.PAPER, Outcome.LOSE)
        assert result.description == "Paper covers Rock"

    def test_description_tie(self):
        result = RoundResult(Move.SPOCK, Move.SPOCK, Outcome.TIE)
        assert result.description == "Both chose Spock"


class TestMatch:
    def test_scoring(self):
        match = Match(CLASSIC)
        match.play(Move.ROCK, Move.SCISSORS)
        match.play(Move.ROCK, Move.PAPER)
        match.play(Move.ROCK, Move.ROCK)
        assert (match.player_score, match.computer_score, match.ties) == (1, 1, 1)
        assert len(match.rounds) == 3

    def test_endless_match_never_ends(self):
        match = Match(CLASSIC)
        for _ in range(50):
            match.play(Move.ROCK, Move.SCISSORS)
        assert not match.is_over
        assert match.player_won is None

    def test_best_of_three_ends_after_two_wins(self):
        match = Match.best_of(CLASSIC, 3)
        assert match.target_wins == 2
        match.play(Move.ROCK, Move.SCISSORS)
        assert not match.is_over
        match.play(Move.ROCK, Move.ROCK)  # ties don't count
        assert not match.is_over
        match.play(Move.ROCK, Move.SCISSORS)
        assert match.is_over
        assert match.player_won is True

    def test_computer_can_win(self):
        match = Match.best_of(CLASSIC, 1)
        match.play(Move.ROCK, Move.PAPER)
        assert match.is_over
        assert match.player_won is False

    @pytest.mark.parametrize("games", [0, -1, 2, 4])
    def test_best_of_requires_positive_odd(self, games):
        with pytest.raises(ValueError):
            Match.best_of(CLASSIC, games)

    def test_cannot_play_after_match_over(self):
        match = Match.best_of(CLASSIC, 1)
        match.play(Move.ROCK, Move.SCISSORS)
        with pytest.raises(ValueError, match="over"):
            match.play(Move.ROCK, Move.SCISSORS)

    def test_rejects_move_outside_ruleset(self):
        match = Match(CLASSIC)
        with pytest.raises(ValueError, match="classic"):
            match.play(Move.LIZARD, Move.ROCK)
        with pytest.raises(ValueError):
            match.play(Move.ROCK, Move.SPOCK)
        assert match.rounds == []  # a rejected move leaves no trace
