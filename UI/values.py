# Centralized configurable values for the chess UI

import chess
import pieces
import sys

# Board defaults
ROWS = 8
COLS = 8
SQUARE_SIZE = 70
MARGIN = 28

# Side panel (move log)
PANEL_WIDTH = 240

# Evaluation info box (rendered to the right of the side panel)
EVAL_BOX_WIDTH = 260
EVAL_BOX_HEIGHT = 230
EVAL_BOX_MARGIN = 12
EVAL_BOX_BG = (22, 22, 26)
EVAL_BOX_BORDER = (40, 40, 44)
EVAL_BOX_TITLE_COLOR = (220, 220, 220)
EVAL_BOX_TEXT_COLOR = (190, 190, 200)

# Evaluation bar (vertical) rendered to the left of the board
EVAL_BAR_WIDTH = 22
EVAL_BAR_GAP = 8
EVAL_BAR_MAX_CP = 5000.0  # clamp mapping range (+/- centipawns)
# Extreme-evaluation handling: when absolute centipawn is in the
# EXTREME range map the bar to a near-full fill (but not completely
# to the edge). If a mate is detected, fill fully.
EVAL_BAR_EXTREME_MIN_CP = 2600.0  # lower bound (inclusive) for extreme mapping
EVAL_BAR_EXTREME_MAX_CP = 7000.0  # upper bound for extreme mapping
EVAL_BAR_EXTREME_FILL = 0.98     # fraction of full bar to fill for extreme CPs
EVAL_BAR_MATE_FILL = 1.0         # fraction for mate (full fill)
EVAL_BAR_BG = (28, 28, 32)
EVAL_BAR_WHITE_COLOR = (84, 196, 129)  # green for White advantage
EVAL_BAR_BLACK_COLOR = (231, 76, 60)   # red for Black advantage
EVAL_BAR_TEXT_COLOR = (200, 200, 200)

# Window defaults – computed so board + panel + gaps fit nicely
_BOARD_W = COLS * SQUARE_SIZE + 2 * MARGIN
_BOARD_H = ROWS * SQUARE_SIZE + 2 * MARGIN
_CAPTURED_ROW_H = 32  # height reserved for captured-pieces strip above/below board
PANEL_MARGIN = 20

WINDOW_WIDTH = PANEL_MARGIN + EVAL_BAR_WIDTH + EVAL_BAR_GAP + _BOARD_W + PANEL_MARGIN + PANEL_WIDTH + PANEL_MARGIN + EVAL_BOX_MARGIN + EVAL_BOX_WIDTH
WINDOW_HEIGHT = PANEL_MARGIN + _CAPTURED_ROW_H + _BOARD_H + _CAPTURED_ROW_H + PANEL_MARGIN

# Eval label (mate) styling — used to render the M{N} badge beside the bar
EVAL_LABEL_PAD_X = 6
EVAL_LABEL_PAD_Y = 4
EVAL_LABEL_BG = (28, 28, 32)
EVAL_LABEL_BORDER = (70, 70, 76)
EVAL_LABEL_TEXT = (255, 245, 200)

# Colors — unified dark charcoal theme
BG_COLOR = (18, 18, 22)
LIGHT_COLOR = (235, 215, 180)
DARK_COLOR = (175, 132, 96)
LABEL_COLOR = (170, 170, 170)
PIECE_COLOR = (40, 30, 20)
HIGHLIGHT_COLOR = (186, 202, 68, 100)  # RGBA for translucent highlight
CHECK_GLOW_COLOR = (220, 50, 47)
MOVE_DOT_COLOR = (100, 160, 80, 180)

# Premove visualization (translucent blue)
PREMOVE_COLOR = (80, 140, 220, 120)

# Last-move highlight (source + destination) — pale yellow with transparency
LAST_MOVE_COLOR = (246, 246, 110, 120)

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
# Resign button height (moved from UI/main.py)
RESIGN_BUTTON_H = 42

# Game-over popup — matching dark charcoal theme
POPUP_BG = (28, 28, 32)
POPUP_BORDER = (60, 60, 66)
POPUP_SHADOW = (0, 0, 0, 140)
POPUP_ACCENT = (230, 188, 151)

# Captured pieces bar
CAPTURED_BG = (24, 24, 28)

# Clock styling and spacing
# When active the clock should invert: light background + dark text.
CLOCK_WIDTH = 100
CLOCK_HEIGHT = 40
CLOCK_RADIUS = 5
CLOCK_MARGIN = 5
CLOCK_ACTIVE_BG = LIGHT_COLOR
CLOCK_ACTIVE_TEXT = (64, 47, 33)
CLOCK_INACTIVE_BG = CAPTURED_BG
CLOCK_INACTIVE_TEXT = PANEL_TEXT_COLOR

# Engine clock: when False the engine's clock is hidden/disabled
ENGINE_HAS_CLOCK = False

# Clock visibility toggles (changed at runtime via UI buttons)
SHOW_PLAYER_CLOCK = True
SHOW_ENGINE_CLOCK = False

# Clock toggle button styling
CLOCK_TOGGLE_W = 22
CLOCK_TOGGLE_H = 22
CLOCK_TOGGLE_ON_BG = (70, 140, 90)
CLOCK_TOGGLE_OFF_BG = (55, 55, 60)
CLOCK_TOGGLE_BORDER = (80, 80, 88)
CLOCK_TOGGLE_TEXT_COLOR = (220, 220, 220)

# Runtime-assigned toggle button rects (set by main.py rendering loop)
_top_clock_toggle_rect = None
_bot_clock_toggle_rect = None

# General UI spacing
PANEL_PADDING = 14
ELEMENT_GAP = 5

# Landing page UI defaults
LANDING_WINDOW_WIDTH = 640
LANDING_WINDOW_HEIGHT = 520
LANDING_BG_COLOR = BG_COLOR
LANDING_TITLE_COLOR = (245, 245, 245)
LANDING_SUBTITLE_COLOR = (180, 180, 180)
LANDING_BUTTON_BG = (70, 140, 90)
LANDING_BUTTON_HOVER = (196, 161, 132)
LANDING_BUTTON_INACTIVE = (60, 60, 66)
LANDING_BUTTON_TEXT = (255, 255, 255)
LANDING_TITLE_FONT_SIZE = 44
LANDING_BODY_FONT_SIZE = 20
LANDING_BUTTON_WIDTH = 260
LANDING_BUTTON_HEIGHT = 64
LANDING_BUTTON_RADIUS = 12

# Landing page checkbox (clock toggles) dimensions
LANDING_CHECKBOX_SIZE = 26
LANDING_CHECKBOX_RADIUS = 4
LANDING_CHECKBOX_LABEL_GAP = 10
LANDING_CHECKBOX_Y1 = 280    # first checkbox Y position
LANDING_CHECKBOX_Y2 = 316    # second checkbox Y position
LANDING_CLOCKS_LABEL_Y = 258 # "Clocks:" label Y position

# Font / rendering
if sys.platform == 'darwin':
    # Prefer Apple Symbols on macOS (monochrome glyphs for chess symbols)
    FONT_NAME = 'Apple Symbols'
elif sys.platform.startswith('win'):
    # Windows default
    FONT_NAME = 'Segoe UI Symbol'
else:
    # Linux / other: try DejaVu Sans which usually contains chess glyphs
    FONT_NAME = 'DejaVu Sans'

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
