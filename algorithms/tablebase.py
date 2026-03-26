import chess
import chess.syzygy
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Resolve paths relative to the project root (parent of algorithms/) ──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Possible locations for Syzygy tablebase files
TB_PATHS = [
    os.path.join(_PROJECT_ROOT, "data", "syzygy", "3-4-5"),
    os.path.join(_PROJECT_ROOT, "data", "syzygy"),
    os.path.join(_PROJECT_ROOT, "data", "syzygy", "regular"),
    os.path.join(_PROJECT_ROOT, "data", "syzygy", "3-4"),
]

_tablebase = None
for p in TB_PATHS:
    try:
        _tablebase = chess.syzygy.open_tablebase(p)
        logger.info("Syzygy tablebase loaded from: %s", p)
        break
    except Exception:
        _tablebase = None

if _tablebase is None:
    logger.warning("Syzygy tablebase not found in any of: %s", TB_PATHS)


def is_tablebase_loaded() -> bool:
    return _tablebase is not None


def probe_wdl(board: chess.Board) -> Optional[int]:
    """Return WDL (2,1,0,-1,-2) or None if not available."""
    if _tablebase is None:
        return None
    try:
        return _tablebase.get_wdl(board, default=None)
    except Exception:
        return None


def probe_dtz_no_ep(board: chess.Board) -> Optional[int]:
    if _tablebase is None:
        return None
    try:
        return _tablebase.probe_dtz_no_ep(board)
    except Exception:
        return None


def tablebase_move_for_root(board: chess.Board):
    """Return a legal move chosen by tablebase (prefer wins), else None.

    Probes positions with <= 5 pieces (covers all 3-4-5 piece Syzygy tables).
    """
    if _tablebase is None:
        return None
    # syzygy requires no castling rights and no en-passant square
    if board.castling_rights or board.ep_square:
        return None
    # probe when <= 5 pieces (all available Syzygy tables)
    if chess.popcount(board.occupied) > 5:
        return None

    try:
        wdl = _tablebase.get_wdl(board, default=None)
    except Exception:
        return None
    if wdl is None:
        return None

    best_move = None
    best_key = (-999, 9999)
    for move in board.legal_moves:
        board.push(move)
        try:
            child_wdl = _tablebase.get_wdl(board, default=None)
            if child_wdl is None:
                continue
            try:
                dtz = _tablebase.probe_dtz_no_ep(board)
            except Exception:
                dtz = 9999
            score = -child_wdl

            # In WINNING positions, deprioritize moves that cause a
            # repetition so the engine makes progress instead of looping.
            # In DRAWN positions, repetitions are fine (draw by repetition
            # is the correct outcome).
            is_repeat = board.is_repetition(2)
            if is_repeat and score > 0:
                # Demote to "barely winning" so any non-repeating win
                # is preferred, but this is still better than a draw (0)
                # or a loss (-1/-2). We keep score > 0 so we don't
                # accidentally prefer a draw over a repeating win.
                score = 0  # treat repeating win as a draw-level move
                sort_dtz = 9998  # worst among equal-score moves
            else:
                # Normal DTZ sorting
                if score > 0:
                    sort_dtz = -abs(dtz)  # fastest win first
                else:
                    sort_dtz = abs(dtz)   # slowest loss first

            key = (score, sort_dtz)
            if key > best_key:
                best_key = key
                best_move = move
        finally:
            board.pop()
    return best_move
