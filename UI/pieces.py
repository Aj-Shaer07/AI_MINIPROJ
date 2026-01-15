# Unicode piece symbols mapping (organized by piece name and color)
"""Chess piece symbols and helpers.

Keep the mapping small and logical (piece name -> {color: symbol}).
Provide a safe `get()` helper that returns a sensible placeholder when
the requested piece or color isn't found.
"""

PIECES = {
    'king': {'black': '♔', 'white': '♚'},
    'queen': {'black': '♕', 'white': '♛'},
    'rook': {'black': '♖', 'white': '♜'},
    'bishop': {'black': '♗', 'white': '♝'},
    'knight': {'black': '♘', 'white': '♞'},
    'pawn': {'black': '♙', 'white': '♟'},
}


def get(piece_name: str, color: str, fallback: str = '?') -> str:
    """Return the unicode symbol for `piece_name` and `color`.

    If the piece name or color is unknown, return `fallback` instead of
    raising an exception. This makes the UI robust to missing data.
    """
    try:
        return PIECES[piece_name][color]
    except Exception:
        return fallback


def available_pieces() -> list:
    """Return a sorted list of available piece names."""
    return sorted(PIECES.keys())
