# Rock Paper Scissors

A terminal Rock Paper Scissors game with an opponent that **learns how you play**.

It started as a 40-line script where the computer picked moves at random. It is now a small, tested Python package with best-of-N matches, a Lizard-Spock mode, three AI difficulty levels and statistics that persist between sessions.

```
$ python -m rps -m extended -d hard
Rock Paper Scissors (extended) - AI difficulty: hard
First to 2 round wins takes the match (best of 3).
Type 'help' for the rules and commands, or 'quit' to leave.

--- Match 1 ---
Moves: rock (r), paper (p), scissors (s), lizard (l), spock (sp)
[Round 1] Your move > lizard
  You: Lizard    Computer: Paper
  Lizard eats Paper - You win the round!
  Score: You 1 - 0 Computer
```

## Features

- **Two rule sets**: classic (rock, paper, scissors) and extended (adds lizard and spock).
- **Best-of-N matches** (default best of 3) or an **endless** mode.
- **Three AI difficulties** that really are different (see [How the AI works](#how-the-ai-works)).
- **Persistent statistics**: win rate, streaks, favourite move, match record.
- **Forgiving input**: type `rock`, `r`, `1`, or any unique prefix like `sci`. Typos re-prompt instead of costing you a round.
- **Safe to interrupt**: Ctrl-C / Ctrl-D ends the game cleanly and still saves your stats.
- **Zero dependencies**: standard library only.
- **Tested**: 113 tests covering the rules, the AI, persistence and the full game loop.

## Quick start

You need Python 3.10 or newer (tested on 3.11, 3.12 and 3.13). Nothing to install:

```bash
git clone https://github.com/raiyan-mahmud-git/rock-paper-scissors_ml_project.git
cd rock-paper-scissors_ml_project
python -m rps
```

Or install the `rps` command:

```bash
pip install .
rps
```

## How to play

At the prompt, enter a move. You can type its full name, a shortcut, its menu number, or any unique prefix.

| Move     | Shortcut | Number |
|----------|----------|--------|
| rock     | `r`      | 1      |
| paper    | `p`      | 2      |
| scissors | `s`      | 3      |
| lizard   | `l`      | 4 (extended only) |
| spock    | `sp`     | 5 (extended only) |

Other commands: `help` (rules), `stats` (your statistics), `quit` (leave; `q` and `exit` work too).

### Rules

Classic: rock crushes scissors, scissors cuts paper, paper covers rock.

Extended mode adds two moves, and every move beats exactly two others:

| Move     | Beats                                   |
|----------|-----------------------------------------|
| rock     | scissors (crushes), lizard (crushes)    |
| paper    | rock (covers), spock (disproves)        |
| scissors | paper (cuts), lizard (decapitates)      |
| lizard   | spock (poisons), paper (eats)           |
| spock    | scissors (smashes), rock (vaporizes)    |

Ties don't count towards a match. In a best-of-3 the first side to **2 round wins** takes the match.

## Command-line options

| Option | Description |
|--------|-------------|
| `-m`, `--mode {classic,extended}` | Rule set (default `classic`) |
| `-d`, `--difficulty {easy,medium,hard}` | AI strength (default `medium`) |
| `-b`, `--best-of N` | Rounds per match; must be odd (default `3`) |
| `--endless` | No matches, just keep playing rounds until you quit |
| `--seed N` | Seed the AI's randomness for reproducible games |
| `--stats` | Print saved statistics and exit |
| `--reset-stats` | Erase saved statistics and exit |
| `--no-save` | Don't read or write the statistics file this session |
| `--stats-file PATH` | Use a different statistics file |
| `--no-color` | Disable colour (also honours the `NO_COLOR` environment variable) |
| `-V`, `--version` | Show the version |

Examples:

```bash
rps -m extended -b 5            # Lizard-Spock, best of 5
rps -d hard --endless           # no matches, toughest AI
rps --stats                     # how am I doing overall?
```

## How the AI works

The AI always picks its move **before** it sees yours, then learns from what you played. It never peeks. That separation is built into the code (`choose()` takes no arguments), and there is a test for it.

| Difficulty | Strategy | Behaviour |
|------------|----------|-----------|
| `easy`   | Random | Picks uniformly at random. Can't be exploited, but can't exploit you either. |
| `medium` | Frequency counter | Tracks which move you favour (recent rounds weigh more, so it adapts when you change style) and plays the move that beats it. |
| `hard`   | Markov chain | Learns what you tend to play *after* your last two moves, so it can catch cycles such as rock → paper → scissors. Falls back to the frequency counter on unfamiliar sequences, and plays randomly 10% of the time so it isn't predictable in return. |

If you play truly randomly, no strategy can beat you in the long run (you'd win about one round in three), so don't expect `hard` to crush you. It wins by exploiting habits, and nearly everyone has some.

## Statistics

Stats are saved when you quit, to `~/.rps/stats.json`. Override the location with `--stats-file PATH` or the `RPS_STATS_FILE` environment variable. They track rounds won/lost/tied, matches won/lost, your current and best win streak (a tie neither extends nor breaks a streak), and your most-played move.

The file is written atomically (temp file, then rename) so a crash can't leave it half-written. If it ever becomes corrupt, it is moved aside to `stats.json.corrupt` rather than deleted, and you start with fresh stats.

## Project layout

```
rock-paper-scissors/
├── rps/
│   ├── game.py      # Rules, moves, match scoring (no I/O)
│   ├── ai.py        # Random, frequency and Markov opponents
│   ├── stats.py     # Statistics and JSON persistence
│   ├── cli.py       # Command-line interface and game loop
│   └── __main__.py  # Enables `python -m rps`
├── tests/           # pytest suite
├── pyproject.toml
└── README.md
```

`game.py` does no printing or input, which keeps the rules easy to test and reuse. For example, from your own code:

```python
from rps.ai import create_strategy
from rps.game import CLASSIC, Match, Move

ai = create_strategy("hard", CLASSIC)
match = Match.best_of(CLASSIC, 3)

while not match.is_over:
    mine = Move.ROCK
    result = match.play(mine, ai.choose())
    ai.observe(mine)
    print(result.description)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## What changed from the original script

| Before | Now |
|--------|-----|
| One class mixing rules, randomness and printing | Rules, AI, stats and UI separated into modules |
| Computer picks at random | Three difficulty levels, including one that learns patterns |
| Endless loop, score lost on exit | Best-of-N matches, lifetime stats saved to disk |
| Win condition as a long chain of `or` clauses | Data-driven rule sets; adding a move means adding data, not logic |
| Exact lowercase words only | Shortcuts, numbers, prefixes; `help` and `stats` commands |
| `import random` inside the method | Seedable RNG, so games and tests are reproducible |
| Ctrl-C / Ctrl-D crashed with a traceback | Clean exit that still saves |
| No tests | 113 tests |

## License

MIT. See [LICENSE](LICENSE).
