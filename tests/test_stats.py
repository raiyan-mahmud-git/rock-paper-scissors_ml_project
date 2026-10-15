import json

import pytest

from rps.game import Move, Outcome
from rps.stats import ENV_VAR, Stats, default_stats_path


class TestRecording:
    def test_fresh_stats(self):
        stats = Stats()
        assert stats.rounds_played == 0
        assert stats.win_rate == 0.0
        assert stats.favourite_move is None

    def test_round_counts_and_win_rate(self):
        stats = Stats()
        stats.record_round(Move.ROCK, Outcome.WIN)
        stats.record_round(Move.ROCK, Outcome.LOSE)
        stats.record_round(Move.PAPER, Outcome.TIE)
        stats.record_round(Move.ROCK, Outcome.WIN)
        assert (stats.rounds_won, stats.rounds_lost, stats.rounds_tied) == (2, 1, 1)
        assert stats.rounds_played == 4
        assert stats.win_rate == 0.5
        assert stats.favourite_move == ("rock", 3)

    def test_streaks(self):
        stats = Stats()
        for outcome in (Outcome.WIN, Outcome.WIN, Outcome.TIE, Outcome.WIN):
            stats.record_round(Move.ROCK, outcome)
        assert stats.current_streak == 3  # a tie doesn't break the streak
        assert stats.best_streak == 3
        stats.record_round(Move.ROCK, Outcome.LOSE)
        assert stats.current_streak == 0
        assert stats.best_streak == 3

    def test_matches(self):
        stats = Stats()
        stats.record_match(True)
        stats.record_match(True)
        stats.record_match(False)
        assert (stats.matches_won, stats.matches_lost) == (2, 1)
        assert stats.matches_played == 3

    def test_favourite_move_ties_resolve_alphabetically(self):
        stats = Stats()
        stats.record_round(Move.SCISSORS, Outcome.TIE)
        stats.record_round(Move.PAPER, Outcome.TIE)
        assert stats.favourite_move == ("paper", 1)


class TestPersistence:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "stats.json"
        stats = Stats()
        stats.record_round(Move.ROCK, Outcome.WIN)
        stats.record_match(True)
        stats.save(path)
        assert Stats.load(path) == stats

    def test_save_creates_parent_directories(self, tmp_path):
        path = tmp_path / "a" / "b" / "stats.json"
        Stats().save(path)
        assert path.exists()

    def test_save_leaves_no_temp_file(self, tmp_path):
        path = tmp_path / "stats.json"
        Stats().save(path)
        assert [p.name for p in tmp_path.iterdir()] == ["stats.json"]

    def test_missing_file_gives_fresh_stats(self, tmp_path):
        assert Stats.load(tmp_path / "nope.json") == Stats()

    @pytest.mark.parametrize(
        "content",
        [
            "not json at all",
            "[]",
            "42",
            json.dumps({"rounds_won": -3}),
            json.dumps({"rounds_won": "lots"}),
            json.dumps({"rounds_won": True}),
            json.dumps({"move_counts": []}),
            json.dumps({"move_counts": {"rock": -1}}),
        ],
    )
    def test_corrupt_file_is_moved_aside(self, tmp_path, content):
        path = tmp_path / "stats.json"
        path.write_text(content, encoding="utf-8")
        assert Stats.load(path) == Stats()
        assert not path.exists()
        assert (tmp_path / "stats.json.corrupt").read_text(encoding="utf-8") == content

    def test_unknown_keys_are_ignored(self, tmp_path):
        path = tmp_path / "stats.json"
        path.write_text(json.dumps({"rounds_won": 2, "future": "x"}), encoding="utf-8")
        assert Stats.load(path).rounds_won == 2

    def test_default_path_honours_environment(self, monkeypatch, tmp_path):
        monkeypatch.setenv(ENV_VAR, str(tmp_path / "custom.json"))
        assert default_stats_path() == tmp_path / "custom.json"

    def test_default_path_without_environment(self, monkeypatch):
        monkeypatch.delenv(ENV_VAR, raising=False)
        assert default_stats_path().parts[-2:] == (".rps", "stats.json")
