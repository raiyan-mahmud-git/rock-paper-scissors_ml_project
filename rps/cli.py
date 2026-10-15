"""Command-line interface for the Rock Paper Scissors game."""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from . import __version__
from .ai import DIFFICULTIES, Strategy, create_strategy
from .game import RULESETS, SHORTCUTS, Match, Move, Outcome, RuleSet, parse_move
from .stats import Stats, default_stats_path

QUIT_WORDS = {"quit", "exit", "q"}
HELP_WORDS = {"help", "h", "?"}
STATS_WORDS = {"stats", "statistics"}
YES_WORDS = {"", "y", "yes"}
NO_WORDS = {"n", "no"} | QUIT_WORDS


class Style:
    """Tiny ANSI colour helper that turns into a no-op when disabled."""

    _CODES = {
        "bold": "1",
        "dim": "2",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "cyan": "36",
    }

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def __call__(self, text: str, *styles: str) -> str:
        if not self.enabled or not styles:
            return text
        codes = ";".join(self._CODES[name] for name in styles)
        return f"\033[{codes}m{text}\033[0m"


def format_stats(stats: Stats, style: Style, title: str = "Statistics") -> str:
    """Render statistics as a few aligned lines of text."""
    lines = [style(title, "bold")]
    if stats.rounds_played == 0:
        lines.append("  No rounds played yet.")
        return "\n".join(lines)

    lines.append(f"  Matches   won {stats.matches_won}, lost {stats.matches_lost}")
    lines.append(
        f"  Rounds    played {stats.rounds_played}: won {stats.rounds_won}, "
        f"lost {stats.rounds_lost}, tied {stats.rounds_tied} "
        f"(win rate {stats.win_rate:.0%})"
    )
    lines.append(
        f"  Streak    current {stats.current_streak}, best {stats.best_streak}"
    )
    favourite = stats.favourite_move
    if favourite is not None:
        name, count = favourite
        plural = "time" if count == 1 else "times"
        lines.append(f"  Favourite move: {name} ({count} {plural})")
    return "\n".join(lines)


def help_text(ruleset: RuleSet, style: Style) -> str:
    lines = [style("Moves", "bold")]
    for number, move in enumerate(ruleset.moves, start=1):
        beaten = sorted(ruleset.beats[move], key=ruleset.moves.index)
        lines.append(
            f"  {number}. {move.label:<9} type '{move.value}', "
            f"'{SHORTCUTS[move]}' or '{number}'   beats "
            + " and ".join(m.value for m in beaten)
        )
    lines.append(style("Commands", "bold"))
    lines.append("  stats   show your statistics")
    lines.append("  help    show this message")
    lines.append("  quit    leave the game")
    return "\n".join(lines)


class Session:
    """One play session: a sequence of matches against a single opponent.

    All input and output goes through ``input_fn`` / ``print_fn`` so tests can
    drive a whole game without a terminal.
    """

    def __init__(
        self,
        ruleset: RuleSet,
        strategy: Strategy,
        stats: Stats,
        target_wins: Optional[int] = None,
        *,
        save_path: Optional[Path] = None,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
        style: Optional[Style] = None,
        difficulty: Optional[str] = None,
    ) -> None:
        self.ruleset = ruleset
        self.strategy = strategy
        self.stats = stats
        self.session_stats = Stats()
        self.target_wins = target_wins
        self.save_path = save_path
        self.input_fn = input_fn
        self.print = print_fn
        self.style = style or Style(False)
        self.difficulty = difficulty
        self._match_number = 0

    # public API

    def run(self) -> None:
        self._print_welcome()
        try:
            while True:
                result = self._play_match()
                if result is None:  # player quit
                    break
                if not self._ask_play_again():
                    break
        finally:
            self._save()
        self._print_goodbye()

    # one match

    def _play_match(self) -> Optional[bool]:
        """Play a match. Returns ``True``/``False`` for win/loss, ``None`` on quit."""
        self._match_number += 1
        match = Match(self.ruleset, self.target_wins)
        s = self.style

        self.print("")
        self.print(s(f"--- Match {self._match_number} ---", "bold"))
        self.print(
            "Moves: "
            + ", ".join(f"{m.value} ({SHORTCUTS[m]})" for m in self.ruleset.moves)
        )

        while not match.is_over:
            move = self._read_move(len(match.rounds) + 1)
            if move is None:
                return None

            computer = self.strategy.choose()  # decided before seeing `move`
            result = match.play(move, computer)
            self.strategy.observe(move)
            for record in (self.stats, self.session_stats):
                record.record_round(move, result.outcome)
            self._show_round(result, match)

        won = bool(match.player_won)
        for record in (self.stats, self.session_stats):
            record.record_match(won)
        score = f"{match.player_score}-{match.computer_score}"
        self.print("")
        if won:
            self.print(s(f"*** You win the match {score}! ***", "green", "bold"))
        else:
            self.print(s(f"*** Computer wins the match {score}. ***", "red", "bold"))
        return won

    def _read_move(self, round_number: int) -> Optional[Move]:
        """Prompt until the player enters a move. ``None`` means quit."""
        prompt = f"[Round {round_number}] Your move > "
        while True:
            try:
                raw = self.input_fn(prompt)
            except (EOFError, KeyboardInterrupt):
                self.print("")
                return None

            token = raw.strip().lower()
            if token in QUIT_WORDS:
                return None
            if token in HELP_WORDS:
                self.print(help_text(self.ruleset, self.style))
                continue
            if token in STATS_WORDS:
                self.print(format_stats(self.stats, self.style))
                continue

            move = parse_move(token, self.ruleset)
            if move is not None:
                return move
            self.print(
                self.style(
                    f"Sorry, '{raw.strip()}' isn't a move. "
                    "Type 'help' to see what you can play.",
                    "yellow",
                )
            )

    def _show_round(self, result, match: Match) -> None:
        s = self.style
        verdicts = {
            Outcome.WIN: s("You win the round!", "green"),
            Outcome.LOSE: s("Computer wins the round.", "red"),
            Outcome.TIE: s("It's a tie.", "yellow"),
        }
        self.print(
            f"  You: {result.player.label:<9} Computer: {result.computer.label}"
        )
        self.print(f"  {result.description} - {verdicts[result.outcome]}")
        score = f"  Score: You {match.player_score} - {match.computer_score} Computer"
        if match.ties:
            score += f" ({match.ties} tied)"
        self.print(s(score, "dim"))

    def _ask_play_again(self) -> bool:
        """Ask until the answer is clearly yes or no (EOF counts as no)."""
        while True:
            try:
                answer = self.input_fn("Play another match? [Y/n] ")
            except (EOFError, KeyboardInterrupt):
                self.print("")
                return False
            token = answer.strip().lower()
            if token in YES_WORDS:
                return True
            if token in NO_WORDS:
                return False
            self.print(self.style("Please answer 'y' or 'n'.", "yellow"))

    # banners and persistence

    def _print_welcome(self) -> None:
        s = self.style
        title = f"Rock Paper Scissors ({self.ruleset.name})"
        if self.difficulty:
            title += f" - AI difficulty: {self.difficulty}"
        self.print(s(title, "bold", "cyan"))
        if self.target_wins is None:
            self.print("Endless mode: play as many rounds as you like.")
        else:
            self.print(
                f"First to {self.target_wins} round wins takes the match "
                f"(best of {self.target_wins * 2 - 1})."
            )
        self.print("Type 'help' for the rules and commands, or 'quit' to leave.")

    def _print_goodbye(self) -> None:
        self.print("")
        if self.session_stats.rounds_played:
            self.print(format_stats(self.session_stats, self.style, "This session"))
            self.print("")
        self.print("Thanks for playing!")

    def _save(self) -> None:
        if self.save_path is None:
            return
        try:
            self.stats.save(self.save_path)
        except OSError as exc:
            self.print(f"Warning: could not save statistics to {self.save_path}: {exc}")


def _odd_positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a whole number")
    if number < 1 or number % 2 == 0:
        raise argparse.ArgumentTypeError(
            "must be a positive odd number (1, 3, 5, ...) so there is always a winner"
        )
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rps",
        description="Play Rock Paper Scissors against an AI that learns your habits.",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=sorted(RULESETS),
        default="classic",
        help="rule set: classic (3 moves) or extended, with lizard and spock "
        "(default: classic)",
    )
    parser.add_argument(
        "-d",
        "--difficulty",
        choices=DIFFICULTIES,
        default="medium",
        help="how smart the AI is (default: medium)",
    )
    length = parser.add_mutually_exclusive_group()
    length.add_argument(
        "-b",
        "--best-of",
        type=_odd_positive_int,
        default=3,
        metavar="N",
        help="rounds per match, must be odd (default: 3)",
    )
    length.add_argument(
        "--endless",
        action="store_true",
        help="no matches: keep playing rounds until you quit",
    )
    parser.add_argument(
        "--seed", type=int, help="seed the AI's random choices (reproducible games)"
    )
    parser.add_argument(
        "--stats", action="store_true", help="show saved statistics and exit"
    )
    parser.add_argument(
        "--reset-stats", action="store_true", help="erase saved statistics and exit"
    )
    parser.add_argument(
        "--no-save", action="store_true", help="don't write statistics to disk"
    )
    parser.add_argument(
        "--stats-file",
        metavar="PATH",
        help="where statistics are stored (default: $RPS_STATS_FILE or "
        "~/.rps/stats.json)",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="disable coloured output"
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def _use_color(args: argparse.Namespace) -> bool:
    if args.no_color or "NO_COLOR" in os.environ:
        return False
    return sys.stdout.isatty()


def main(
    argv: Optional[Sequence[str]] = None,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[..., None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    style = Style(_use_color(args))
    stats_path = (
        Path(args.stats_file).expanduser() if args.stats_file else default_stats_path()
    )

    if args.reset_stats:
        try:
            Stats().save(stats_path)
        except OSError as exc:
            print_fn(f"Could not reset statistics at {stats_path}: {exc}")
            return 1
        print_fn(f"Statistics reset ({stats_path}).")
        return 0

    if args.stats:
        print_fn(format_stats(Stats.load(stats_path), style))
        return 0

    ruleset = RULESETS[args.mode]
    strategy = create_strategy(args.difficulty, ruleset, random.Random(args.seed))
    stats = Stats() if args.no_save else Stats.load(stats_path)
    target_wins: Optional[int] = None if args.endless else args.best_of // 2 + 1

    Session(
        ruleset,
        strategy,
        stats,
        target_wins,
        save_path=None if args.no_save else stats_path,
        input_fn=input_fn,
        print_fn=print_fn,
        style=style,
        difficulty=args.difficulty,
    ).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
