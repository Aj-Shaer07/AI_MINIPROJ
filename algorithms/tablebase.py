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
            # Skip moves that cause repetition — never repeat positions
            if board.is_repetition(2):
                continue

            child_wdl = _tablebase.get_wdl(board, default=None)
            if child_wdl is None:
                continue
            try:
                dtz = _tablebase.probe_dtz_no_ep(board)
            except Exception:
                dtz = 9999
            score = -child_wdl

            # For winning moves (score > 0): dtz of child is negative
            # (opponent is losing). We want the FASTEST mate = smallest |dtz|.
            # For losing moves (score < 0): dtz of child is positive
            # (opponent is winning). We want the SLOWEST loss = largest dtz.
            # Using -abs(dtz) for wins (prefer smallest |dtz|) and
            # abs(dtz) for losses (prefer largest |dtz|).
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
