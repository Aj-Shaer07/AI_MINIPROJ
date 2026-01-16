# Centralized configurable values for the chess UI

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

# Demo test piece (use `pieces.py` to resolve the symbol)
# Use these to control the initial demo piece and its color. Keep values
# here simple and logical so adding new pieces remains easy.
DEMO_PIECE_NAME = 'king'   # logical piece name (key in `pieces.PIECES`)
DEMO_PIECE_COLOR = 'black' # 'white' or 'black'
# Default demo position (row, col) — placed near bottom center by default
DEMO_PIECE_POS = (ROWS - 1, COLS // 2)

# Font / rendering
FONT_NAME = 'Segoe UI Symbol'

# Per-piece render colors (map logical 'white'/'black' to RGB tuples)
PIECE_COLORS = {
	'white': (255, 255, 255),
	'black': (0, 0, 0),
}
