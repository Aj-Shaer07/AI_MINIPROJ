"""Chess piece mappings and SVG helpers.

Keep the unicode mapping small and logical (piece name -> {color: symbol}).
Provide helpers for loading SVG assets with optional styling and caching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple, List

import pygame
import sys

# Caches to avoid repeated expensive font lookups
# font_name -> resolved font path (or None if not found)
_font_match_cache: Dict[str, Optional[str]] = {}
# (symbol, size) -> selected font name (or None)
_symbol_font_cache: Dict[Tuple[str, int], Optional[str]] = {}

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
    """Return a pygame.Surface for the piece when running on macOS.

    On Windows we keep the behavior of returning None so the UI falls
    back to rendering Unicode glyphs directly. On macOS we attempt to
    pick a font that contains the glyph and render it into a surface so
    the font-specific glyphs are used.
    """
    if not piece_name or not color:
        return None
    symbol = PIECES.get(piece_name, {}).get(color)
    if not symbol:
        return None

    # macOS: try to render the symbol using a matched system font so
    # glyphs from the system font are used. On other platforms return
    # None so the UI renders the plain unicode character.
    if sys.platform.startswith("darwin"):
        try:
            font_name = get_font_for_symbol(symbol, size=size_px)
            if not font_name:
                return None
            font_path = pygame.font.match_font(font_name)
            if not font_path:
                return None
            pygame.font.init()
            font = pygame.font.Font(font_path, size_px)
            # Render in black by default; UI can blit/transform as needed.
            surf = font.render(symbol, True, (0, 0, 0))
            return surf
        except Exception:
            return None

    # Non-macOS: no surface (UI should render Unicode glyphs itself)
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


def _is_symbol_renderable_with_font(symbol: str, font_name: str, size: int = 32) -> bool:
    """Check whether `font_name` can render `symbol` using pygame.

    Returns True when the font is available and rendering the symbol
    produces a non-empty surface. This is a best-effort helper used by
    UI code to pick a font that actually contains the chess glyphs on
    the running system (useful on macOS where font fallback can vary).
    """
    try:
        pygame.font.init()
        # Use a simple cache for match_font results so we don't repeatedly
        # probe the system font registry which can be slow on some OSes.
        if font_name in _font_match_cache:
            font_path = _font_match_cache[font_name]
        else:
            font_path = pygame.font.match_font(font_name)
            _font_match_cache[font_name] = font_path
        if not font_path:
            return False
        font = pygame.font.Font(font_path, size)
        surf = font.render(symbol, True, (0, 0, 0))
        return surf.get_width() > 0 and surf.get_height() > 0
    except Exception:
        return False


def get_font_for_symbol(symbol: str, preferred_fonts: Optional[List[str]] = None, size: int = 32) -> Optional[str]:
    """Return the first preferred font name that can render `symbol`.

    - `preferred_fonts` is an ordered list of font family names to try.
      If omitted, a sensible set of common fonts will be attempted.
    - Returns the font family name (as passed) on success, otherwise None.

    Note: callers should use the returned font name with `pygame.font.match_font`
    or their own font API to obtain a usable font object/path.
    """
    if not symbol:
        return None
    # fast-path: cached result for this symbol+size
    cache_key = (symbol, size)
    if cache_key in _symbol_font_cache:
        return _symbol_font_cache[cache_key]
    # Prefer platform-specific sensible defaults first
    if sys.platform.startswith('win'):
        defaults = [
            "Segoe UI Symbol",
            "Segoe UI Emoji",
            "Segoe UI",
            "Arial Unicode MS",
            "Arial",
            "Tahoma",
            "Calibri",
            "Times New Roman",
            "Symbola",
            "DejaVu Sans",
            "Apple Color Emoji",
        ]
    elif sys.platform == 'darwin':
        defaults = [
            "Apple Symbols",
            "Apple Color Emoji",
            "Symbola",
            "DejaVu Sans",
            "Arial Unicode MS",
        ]
    else:
        defaults = [
            "DejaVu Sans",
            "DejaVuSans",
            "Symbola",
            "Arial Unicode MS",
            "Arial",
        ]
    fonts_to_try = preferred_fonts or defaults
    for fname in fonts_to_try:
        if _is_symbol_renderable_with_font(symbol, fname, size=size):
            _symbol_font_cache[cache_key] = fname
            return fname
    # If the explicit list didn't find a usable font, scan installed fonts
    # for plausible candidates (helps on Windows where family names differ).
    try:
        pygame.font.init()
        available = pygame.font.get_fonts() or []
    except Exception:
        available = []

    keywords = ("seg", "symbol", "emoji", "deja", "arial", "unicode", "times", "calibri", "tahoma", "ms")
    for af in available:
        # `af` returned by get_fonts() is usually lowercase and space-free;
        # check for known substrings before trying.
        if any(k in af for k in keywords):
            if _is_symbol_renderable_with_font(symbol, af, size=size):
                _symbol_font_cache[cache_key] = af
                return af

    _symbol_font_cache[cache_key] = None
    return None
