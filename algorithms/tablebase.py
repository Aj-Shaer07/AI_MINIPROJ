import chess
import chess.syzygy
from typing import Optional

# Possible locations (adjust if you downloaded elsewhere)
TB_PATHS = ["data/syzygy", "data/syzygy/regular", "data/syzygy/3-4"]

_tablebase = None
for p in TB_PATHS:
    try:
        _tablebase = chess.syzygy.open_tablebase(p)
        break
    except Exception:
        _tablebase = None


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

    Only consider positions meeting Syzygy preconditions and <= 4 pieces.
    """
    if _tablebase is None:
        return None
    # syzygy requires no castling rights and no en-passant square
    if board.castling_rights or board.ep_square:
        return None
    # respect user requirement: only probe when <= 4 pieces
    if chess.popcount(board.occupied) > 4:
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
            key = (score, -dtz)
            if key > best_key:
                best_key = key
                best_move = move
        finally:
            board.pop()
    return best_move
