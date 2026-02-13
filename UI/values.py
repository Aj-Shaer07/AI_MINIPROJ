# Centralized configurable values for the chess UI

import chess
import pieces

# Window defaults
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 640

# Board defaults
ROWS = 8
COLS = 8
SQUARE_SIZE = 60
MARGIN = 40

# Colors
LIGHT_COLOR = (167, 141, 97)
DARK_COLOR = (91, 91, 91)
BG_COLOR = (30, 30, 30)
LABEL_COLOR = (255, 255, 255)
PIECE_COLOR = (0, 0, 0)
HIGHLIGHT_COLOR = (255, 255, 0, 80)  # RGBA for translucent highlight
CHECK_GLOW_COLOR = (220, 60, 60)
MOVE_DOT_COLOR = (55, 117, 58)

# Side panel (move log)
PANEL_BG_COLOR = (20, 20, 20)
PANEL_BORDER_COLOR = (80, 80, 80)
PANEL_TEXT_COLOR = (230, 230, 230)
PANEL_TITLE_COLOR = (255, 255, 255)
PANEL_WIDTH = 220

# (Demo piece settings removed)

# Font / rendering
FONT_NAME = 'Segoe UI Symbol'

# Per-piece render colors (map logical 'white'/'black' to RGB tuples)
PIECE_COLORS = {
	'white': (250, 250, 250),
	'black': (10, 10, 10),
}

# Piece symbol mapping (chess constant -> (black_symbol, white_symbol))
PIECE_SYMBOL_MAP = {
    chess.PAWN: (pieces.PIECES['pawn']['black'], pieces.PIECES['pawn']['white']),
    chess.KNIGHT: (pieces.PIECES['knight']['black'], pieces.PIECES['knight']['white']),
    chess.BISHOP: (pieces.PIECES['bishop']['black'], pieces.PIECES['bishop']['white']),
    chess.ROOK: (pieces.PIECES['rook']['black'], pieces.PIECES['rook']['white']),
    chess.QUEEN: (pieces.PIECES['queen']['black'], pieces.PIECES['queen']['white']),
    chess.KING: (pieces.PIECES['king']['black'], pieces.PIECES['king']['white']),
}
