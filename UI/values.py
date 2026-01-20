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

# (Demo piece settings removed)

# Font / rendering
FONT_NAME = 'Segoe UI Symbol'

# Per-piece render colors (map logical 'white'/'black' to RGB tuples)
PIECE_COLORS = {
	'white': (255, 255, 255),
	'black': (0, 0, 0),
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
