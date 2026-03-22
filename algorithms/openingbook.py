"""
Polyglot Opening Book
=====================
Loads a Polyglot‐format opening book (.bin) and provides a function
to look up the best (or a weighted‐random) book move for any position.
"""

import chess
import chess.polyglot
import os
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Resolve book path relative to project root ──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOOK_PATHS = [
    os.path.join(_PROJECT_ROOT, "data", "opening_book", "gm2001.bin"),
    os.path.join(_PROJECT_ROOT, "data", "opening_book", "book.bin"),
]

_reader = None
_book_path = None
for p in BOOK_PATHS:
    if os.path.isfile(p):
        try:
            _reader = chess.polyglot.open_reader(p)
            _book_path = p
            logger.info("Opening book loaded from: %s", p)
            break
        except Exception as e:
            logger.warning("Failed to load opening book %s: %s", p, e)
            _reader = None

if _reader is None:
    logger.warning("No opening book found in: %s", BOOK_PATHS)


def is_book_loaded() -> bool:
    return _reader is not None


def get_book_path() -> Optional[str]:
    return _book_path


def book_move(board: chess.Board, weighted_random: bool = True) -> Optional[chess.Move]:
    """Return a book move for the position, or None if not in the book.

    Args:
        board: Current board position.
        weighted_random: If True, pick a random move weighted by the
            book's frequency weights (more natural, varied play).
            If False, always return the move with the highest weight
            (strongest / most popular move).
    """
    if _reader is None:
        return None

    try:
        entries = list(_reader.find_all(board))
    except Exception:
        return None

    if not entries:
        return None

    # Filter to only legal moves (safety check)
    entries = [e for e in entries if e.move in board.legal_moves]
    if not entries:
        return None

    if weighted_random:
        # Pick a move weighted by book frequency
        total_weight = sum(e.weight for e in entries)
        if total_weight <= 0:
            return entries[0].move

        r = random.randint(1, total_weight)
        cumulative = 0
        for entry in entries:
            cumulative += entry.weight
            if r <= cumulative:
                return entry.move
        return entries[0].move
    else:
        # Return the highest-weight (most popular) move
        entries.sort(key=lambda e: e.weight, reverse=True)
        return entries[0].move
