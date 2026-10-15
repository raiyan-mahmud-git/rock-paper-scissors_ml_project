"""Allow running the game with ``python -m rps``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
