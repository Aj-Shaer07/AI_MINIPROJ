# Centralized configurable values for the chess UI

import chess
import pieces

# Board defaults
ROWS = 8
COLS = 8
SQUARE_SIZE = 70
MARGIN = 28

# Side panel (move log)
PANEL_WIDTH = 240

# Window defaults – computed so board + panel + gaps fit nicely
_BOARD_W = COLS * SQUARE_SIZE + 2 * MARGIN
_BOARD_H = ROWS * SQUARE_SIZE + 2 * MARGIN
_CAPTURED_ROW_H = 32  # height reserved for captured-pieces strip above/below board
PANEL_MARGIN = 14

WINDOW_WIDTH = PANEL_MARGIN + _BOARD_W + PANEL_MARGIN + PANEL_WIDTH + PANEL_MARGIN
WINDOW_HEIGHT = PANEL_MARGIN + _CAPTURED_ROW_H + _BOARD_H + _CAPTURED_ROW_H + PANEL_MARGIN

# Colors — unified dark charcoal theme
BG_COLOR = (18, 18, 22)
LIGHT_COLOR = (235, 215, 180)
DARK_COLOR = (175, 132, 96)
LABEL_COLOR = (170, 170, 170)
PIECE_COLOR = (40, 30, 20)
HIGHLIGHT_COLOR = (186, 202, 68, 100)  # RGBA for translucent highlight
CHECK_GLOW_COLOR = (220, 50, 47)
MOVE_DOT_COLOR = (100, 160, 80, 180)

# Panel colors – clean dark grey
PANEL_BG_COLOR = (26, 26, 30)
PANEL_BORDER_COLOR = (50, 50, 55)
PANEL_TEXT_COLOR = (210, 210, 215)
PANEL_TITLE_COLOR = (255, 255, 255)
PANEL_HEADER_BG = (34, 34, 38)

# Resign button
RESIGN_BTN_COLOR = (180, 50, 50)
RESIGN_BTN_HOVER = (210, 60, 60)
RESIGN_BTN_DISABLED = (50, 50, 55)

# Game-over popup — matching dark charcoal theme
POPUP_BG = (28, 28, 32)
POPUP_BORDER = (60, 60, 66)
POPUP_SHADOW = (0, 0, 0, 140)
POPUP_ACCENT = (200, 180, 140)

# Captured pieces bar
CAPTURED_BG = (24, 24, 28)

# (Demo piece settings removed)

# Font / rendering
FONT_NAME = 'Segoe UI Symbol'

# Per-piece render colors (map logical 'white'/'black' to RGB tuples)
PIECE_COLORS = {
	'white': (255, 248, 230),
	'black': (15, 12, 10),
}

# Piece outline colors for text rendering
PIECE_OUTLINE_COLORS = {
	'white': (120, 90, 50),
	'black': (160, 145, 110),
}

# Piece outline thickness
PIECE_OUTLINE_PX = 1

# Piece symbol mapping (chess constant -> (black_symbol, white_symbol))
PIECE_SYMBOL_MAP = {
    chess.PAWN: (pieces.PIECES['pawn']['black'], pieces.PIECES['pawn']['white']),
    chess.KNIGHT: (pieces.PIECES['knight']['black'], pieces.PIECES['knight']['white']),
    chess.BISHOP: (pieces.PIECES['bishop']['black'], pieces.PIECES['bishop']['white']),
    chess.ROOK: (pieces.PIECES['rook']['black'], pieces.PIECES['rook']['white']),
    chess.QUEEN: (pieces.PIECES['queen']['black'], pieces.PIECES['queen']['white']),
    chess.KING: (pieces.PIECES['king']['black'], pieces.PIECES['king']['white']),
}
