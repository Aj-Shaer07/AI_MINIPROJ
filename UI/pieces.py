"""Chess piece mappings and SVG helpers.

Keep the unicode mapping small and logical (piece name -> {color: symbol}).
Provide helpers for loading SVG assets with optional styling and caching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

PIECES = {
    'king': {'white': '♔', 'black': '♚'},
    'queen': {'white': '♕', 'black': '♛'},
    'rook': {'white': '♖', 'black': '♜'},
    'bishop': {'white': '♗', 'black': '♝'},
    'knight': {'white': '♘', 'black': '♞'},
    'pawn': {'white': '♙', 'black': '♟'},
}
# SVG assets removed — the UI uses Unicode glyphs only.

UNICODE_TO_PIECE = {symbol: name for name, colors in PIECES.items() for symbol in colors.values()}
UNICODE_TO_COLOR = {symbol: color for name, colors in PIECES.items() for color, symbol in colors.items()}

# macOS style support: keep mappings separate so a future macOS asset set
# can provide different glyphs or SVGs. For now we mirror the unicode set
# so the API works on macOS as well.
MACOS_PIECES = {name: colors.copy() for name, colors in PIECES.items()}

# Styles registry: callers may request a style by name when asking for
# a piece symbol. The default (and backwards-compatible) style is
# 'unicode'.
STYLES = {
    'unicode': PIECES,
    'macos': MACOS_PIECES,
}


def get(piece_name: str, color: str, fallback: str = '?', style: str = 'unicode') -> str:
    """Return the piece symbol for `piece_name` and `color` in `style`.

    The `style` parameter selects a named style (for example 'unicode'
    or 'macos'). If the piece name, color, or style is unknown, return
    `fallback` instead of raising an exception to keep the UI robust.
    """
    try:
        pieces = STYLES.get(style, STYLES['unicode'])
        return pieces.get(piece_name, {}).get(color, fallback)
    except Exception:
        return fallback


def name_from_symbol(symbol: str) -> Optional[str]:
    """Return the piece name for a unicode symbol, or None if unknown."""
    return UNICODE_TO_PIECE.get(symbol)


def color_from_symbol(symbol: str) -> Optional[str]:
    """Return the color for a unicode symbol, or None if unknown."""
    return UNICODE_TO_COLOR.get(symbol)


def get_svg_path(piece_name: str, color: str) -> Optional[Path]:
    """Return the SVG path for the given piece name and color."""
    try:
        # SVG assets removed — no file path available
        return None
    except Exception:
        return None


def clear_svg_cache() -> None:
    """No-op: SVG caching removed (kept for API compatibility)."""
    return None

def available_pieces() -> list:
    """Return a sorted list of available piece names."""
    return sorted(PIECES.keys())


def available_styles() -> list:
    """Return a list of available piece styles (e.g. `unicode`, `macos`)."""
    return sorted(STYLES.keys())


def available_pieces_for_style(style: str = 'unicode') -> list:
    """Return a sorted list of available piece names for `style`.

    This mirrors `available_pieces()` but allows callers to query a
    specific style explicitly.
    """
    pieces = STYLES.get(style, STYLES['unicode'])
    return sorted(pieces.keys())


def get_piece_surface(piece_name: Optional[str], color: Optional[str], size_px: int):
    """Compatibility stub: image assets removed, return None so UI uses Unicode rendering."""
    return None


def get_piece_surface_for_symbol(symbol: Optional[str], size_px: int):
    """Compatibility stub: maps symbol -> (name,color) then returns None.

    UI code should fall back to rendering Unicode glyphs when this returns None.
    """
    if not symbol:
        return None
    name = name_from_symbol(str(symbol))
    color = color_from_symbol(str(symbol))
    return get_piece_surface(name, color, size_px)
