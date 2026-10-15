import random

import pytest

from rps import cli
from rps.ai import Strategy
from rps.cli import Session, Style, format_stats, main
from rps.game import CLASSIC, EXTENDED, Move
from rps.stats import Stats


class Scripted(Strategy):
    """A computer opponent that plays a fixed list of moves."""

    name = "scripted"

    def __init__(self, ruleset, moves):
        super().__init__(ruleset, random.Random(0))
        self._moves = iter(moves)
        self.seen = []

    def choose(self):
        return next(self._moves)

    def observe(self, player_move):
        self.seen.append(player_move)


def play(inputs, computer_moves, *, ruleset=CLASSIC, target_wins=None, save_path=None):
    """Run a session with scripted input; return (output text, session)."""
    typed = iter(inputs)
    out = []

    def fake_input(prompt):
        out.append(prompt)
        try:
            return next(typed)
        except StopIteration:
            raise EOFError

    strategy = Scripted(ruleset, computer_moves)
    session = Session(
        ruleset,
        strategy,
        Stats(),
        target_wins,
        save_path=save_path,
        input_fn=fake_input,
        print_fn=lambda *a, **k: out.append(" ".join(map(str, a))),
        style=Style(False),
    )
    session.run()
    return "\n".join(out), session


class TestSession:
    def test_win_loss_tie_in_endless_mode(self):
        text, session = play(
            ["rock", "rock", "rock", "quit"],
            [Move.SCISSORS, Move.PAPER, Move.ROCK],
        )
        assert "Rock crushes Scissors" in text
        assert "Paper covers Rock" in text
        assert "Both chose Rock" in text
        s = session.stats
        assert (s.rounds_won, s.rounds_lost, s.rounds_tied) == (1, 1, 1)

    def test_best_of_three_player_wins(self):
        text, session = play(
            ["r", "r", "n"],
            [Move.SCISSORS, Move.SCISSORS],
            target_wins=2,
        )
        assert "You win the match 2-0" in text
        assert session.stats.matches_won == 1

    def test_computer_wins_match(self):
        text, session = play(
            ["rock", "rock", "n"],
            [Move.PAPER, Move.PAPER],
            target_wins=2,
        )
        assert "Computer wins the match 0-2" in text
        assert session.stats.matches_lost == 1

    def test_play_again_starts_a_new_match(self):
        text, session = play(
            ["r", "", "r", "no"],  # blank answer to "play again" means yes
            [Move.SCISSORS, Move.SCISSORS],
            target_wins=1,
        )
        assert "Match 1" in text and "Match 2" in text
        assert session.stats.matches_won == 2

    def test_unclear_play_again_answer_is_asked_again(self):
        text, session = play(
            ["r", "r", "maybe", "r", "yes", "r", "r", "n"],
            [Move.SCISSORS] * 6,
            target_wins=2,
        )
        # Match 1 (2 rounds), "maybe" is rejected, "r" is rejected, "yes" starts
        # match 2 (2 rounds), then "n" ends the session.
        assert text.count("Please answer 'y' or 'n'") == 2
        assert "Match 2" in text and "Match 3" not in text
        assert session.stats.matches_won == 2

    def test_invalid_input_is_rejected_without_consuming_a_round(self):
        text, session = play(
            ["banana", "", "lizard", "rock", "quit"], [Move.SCISSORS]
        )
        assert text.count("isn't a move") == 3
        assert session.stats.rounds_played == 1

    def test_help_and_stats_commands(self):
        text, session = play(["help", "stats", "rock", "stats", "quit"], [Move.SCISSORS])
        assert "Commands" in text
        assert "No rounds played yet" in text
        assert "win rate 100%" in text
        assert session.stats.rounds_played == 1 

    def test_eof_ends_the_game_cleanly(self):
        text, _ = play([], [])
        assert "Thanks for playing" in text

    def test_ai_observes_each_player_move(self):
        _, session = play(["r", "p", "quit"], [Move.ROCK, Move.ROCK])
        assert session.strategy.seen == [Move.ROCK, Move.PAPER]

    def test_extended_mode(self):
        text, session = play(
            ["lizard", "5", "quit"],
            [Move.SPOCK, Move.SCISSORS],
            ruleset=EXTENDED,
        )
        assert "Lizard poisons Spock" in text
        assert "Spock smashes Scissors" in text
        assert session.stats.rounds_won == 2

    def test_stats_are_saved_on_quit(self, tmp_path):
        path = tmp_path / "stats.json"
        play(["rock", "quit"], [Move.SCISSORS], save_path=path)
        assert Stats.load(path).rounds_won == 1

    def test_stats_are_saved_even_if_input_ends_abruptly(self, tmp_path):
        path = tmp_path / "stats.json"
        play(["rock"], [Move.SCISSORS], save_path=path)  # then EOF
        assert Stats.load(path).rounds_won == 1

    def test_save_failure_is_reported_not_raised(self, tmp_path):
        blocker = tmp_path / "file"
        blocker.write_text("x")
        text, _ = play(["rock", "quit"], [Move.SCISSORS], save_path=blocker / "s.json")
        assert "could not save statistics" in text


class TestFormatting:
    def test_format_stats_empty(self):
        assert "No rounds played yet" in format_stats(Stats(), Style(False))

    def test_style_is_noop_when_disabled(self):
        assert Style(False)("hi", "red") == "hi"

    def test_style_adds_ansi_codes_when_enabled(self):
        assert Style(True)("hi", "red") == "\033[31mhi\033[0m"
        assert Style(True)("hi") == "hi"


class TestMain:
    def run(self, argv, inputs=(), tmp_path=None):
        typed = iter(inputs)
        out = []

        def fake_input(prompt):
            try:
                return next(typed)
            except StopIteration:
                raise EOFError

        code = main(
            list(argv),
            input_fn=fake_input,
            print_fn=lambda *a, **k: out.append(" ".join(map(str, a))),
        )
        return code, "\n".join(out)

    def test_plays_and_persists_stats(self, tmp_path):
        stats_file = tmp_path / "s.json"
        code, out = self.run(
            ["--stats-file", str(stats_file), "--seed", "1", "-d", "easy"],
            ["rock", "quit"],
        )
        assert code == 0
        assert "AI difficulty: easy" in out
        assert Stats.load(stats_file).rounds_played == 1

    def test_no_save_does_not_touch_disk(self, tmp_path):
        stats_file = tmp_path / "s.json"
        self.run(["--stats-file", str(stats_file), "--no-save"], ["rock", "quit"])
        assert not stats_file.exists()

    def test_stats_flag(self, tmp_path):
        stats_file = tmp_path / "s.json"
        s = Stats()
        s.rounds_won = 3
        s.save(stats_file)
        code, out = self.run(["--stats", "--stats-file", str(stats_file)])
        assert code == 0
        assert "won 3" in out

    def test_reset_stats(self, tmp_path):
        stats_file = tmp_path / "s.json"
        s = Stats()
        s.rounds_won = 3
        s.save(stats_file)
        code, out = self.run(["--reset-stats", "--stats-file", str(stats_file)])
        assert code == 0
        assert "reset" in out.lower()
        assert Stats.load(stats_file).rounds_played == 0

    def test_endless_flag(self, tmp_path):
        _, out = self.run(["--endless", "--no-save"], ["quit"])
        assert "Endless mode" in out

    def test_best_of_flag(self, tmp_path):
        _, out = self.run(["--best-of", "5", "--no-save"], ["quit"])
        assert "First to 3 round wins" in out

    def test_extended_mode_flag(self, tmp_path):
        _, out = self.run(["-m", "extended", "--no-save"], ["quit"])
        assert "extended" in out

    @pytest.mark.parametrize(
        "bad,message", [("2", "odd"), ("0", "odd"), ("-3", "odd"), ("abc", "whole number")]
    )
    def test_best_of_must_be_odd(self, bad, message, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--best-of", bad])
        assert exc.value.code == 2
        assert message in capsys.readouterr().err

    def test_unwritable_reset_path_returns_error(self, tmp_path):
        blocker = tmp_path / "file"
        blocker.write_text("x")
        code, out = self.run(["--reset-stats", "--stats-file", str(blocker / "s.json")])
        assert code == 1
        assert "Could not reset" in out

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert "2.0.0" in capsys.readouterr().out

    def test_no_color_when_not_a_tty(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        args = cli.build_parser().parse_args([])
        assert cli._use_color(args) is False  # pytest captures stdout

    def test_no_color_env_var(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        args = cli.build_parser().parse_args([])
        assert cli._use_color(args) is False
