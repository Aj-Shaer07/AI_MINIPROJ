import pygame
from typing import List, Optional, Tuple
import values


Color = Tuple[int, int, int]


def _get_font(size: int) -> pygame.font.Font:
	"""Return a pygame Font capable of rendering chess Unicode glyphs.

	Tries `values.FONT_NAME` first (if set), then a few common Unicode fonts.
	Falls back to the default pygame font if none found.
	"""
	# Only use the configured FONT_NAME (user-specified). If not available,
	# fall back to the default pygame font.
	if values.FONT_NAME:
		try:
			path = pygame.font.match_font(values.FONT_NAME)
			if path:
				return pygame.font.Font(path, size)
		except Exception:
			pass

	return pygame.font.SysFont(None, size)


class ChessBoard:
	"""A drawable, resizable chessboard model.

	Responsibilities:
	- Maintain a simple `board` matrix storing pieces (or None).
	- Draw the board, pieces and coordinate labels to a `pygame.Surface`.

	The class keeps no pygame state; it accepts a Surface to draw onto.
	"""

	def __init__(
		self,
		rows: int = values.ROWS,
		cols: int = values.COLS,
		square_size: int = values.SQUARE_SIZE,
		margin: int = values.MARGIN,
		light_color: Color = values.LIGHT_COLOR,
		dark_color: Color = values.DARK_COLOR,
	) -> None:
		self.rows = rows
		self.cols = cols
		self.square_size = square_size
		self.margin = margin
		self.light_color = light_color
		self.dark_color = dark_color

		# board matrix storing either None, a symbol string, or (symbol, color_key)
		self.board: List[List[Optional[str]]] = [[None for _ in range(cols)] for _ in range(rows)]

		# optional highlighted square (row, col)
		self.highlight: Optional[Tuple[int, int]] = None

	@property
	def width(self) -> int:
		return self.cols * self.square_size + 2 * self.margin

	@property
	def height(self) -> int:
		return self.rows * self.square_size + 2 * self.margin

	def draw(self, surface: pygame.Surface, top_left: Tuple[int, int] = (0, 0)) -> None:
		tx, ty = top_left
		coord_font = _get_font(max(12, self.square_size // 4))

		# draw squares
		for r in range(self.rows):
			for c in range(self.cols):
				rect = pygame.Rect(
					tx + self.margin + c * self.square_size,
					ty + self.margin + r * self.square_size,
					self.square_size,
					self.square_size,
				)
				color = self.light_color if (r + c) % 2 == 0 else self.dark_color
				pygame.draw.rect(surface, color, rect)

		# highlight square (drawn above squares)
		if self.highlight is not None:
			rh, ch = self.highlight
			rect = pygame.Rect(
				tx + self.margin + ch * self.square_size,
				ty + self.margin + rh * self.square_size,
				self.square_size,
				self.square_size,
			)
			s = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
			s.fill(values.HIGHLIGHT_COLOR)
			surface.blit(s, rect.topleft)

		# draw pieces
		piece_font = _get_font(max(12, int(self.square_size * 0.8)))
		for r in range(self.rows):
			for c in range(self.cols):
				piece = self.board[r][c]
				if not piece:
					continue
				# piece stored as symbol or (symbol, color_key)
				if isinstance(piece, (list, tuple)):
					symbol, color_key = piece[0], piece[1]
				else:
					symbol, color_key = piece, None
				render_color = values.PIECE_COLORS.get(color_key, values.PIECE_COLOR)
				text = piece_font.render(str(symbol), True, render_color)
				px = tx + self.margin + c * self.square_size + self.square_size // 2 - text.get_width() // 2
				py = ty + self.margin + r * self.square_size + self.square_size // 2 - text.get_height() // 2
				surface.blit(text, (px, py))

		# draw coordinate labels
		files = [chr(ord('a') + i) for i in range(self.cols)]
		for c, label in enumerate(files):
			text = coord_font.render(label, True, values.LABEL_COLOR)
			fx = tx + self.margin + c * self.square_size + self.square_size // 2 - text.get_width() // 2
			fy = ty + self.margin + self.rows * self.square_size + max(2, (self.margin - text.get_height()) // 2)
			surface.blit(text, (fx, fy))

		ranks = [str(self.rows - r) for r in range(self.rows)]
		for r, label in enumerate(ranks):
			text = coord_font.render(label, True, values.LABEL_COLOR)
			rx = tx + max(2, (self.margin - text.get_width()) // 2)
			ry = ty + self.margin + r * self.square_size + self.square_size // 2 - text.get_height() // 2
			surface.blit(text, (rx, ry))

	def set_piece(self, row: int, col: int, piece: Optional[str]) -> None:
		"""Set a piece at (row,col).

		`piece` may be either:
		- None to clear the square
		- a symbol string (e.g. '♔')
		- a tuple/list (symbol, color_key) where color_key is 'white' or 'black'
		"""
		if 0 <= row < self.rows and 0 <= col < self.cols:
			self.board[row][col] = piece

	def clear(self) -> None:
		self.board = [[None for _ in range(self.cols)] for _ in range(self.rows)]

	def pixel_to_square(self, x: int, y: int, top_left: Tuple[int, int] = (0, 0)) -> Optional[Tuple[int, int]]:
		tx, ty = top_left
		local_x = x - (tx + self.margin)
		local_y = y - (ty + self.margin)
		if local_x < 0 or local_y < 0:
			return None
		c = local_x // self.square_size
		r = local_y // self.square_size
		if 0 <= r < self.rows and 0 <= c < self.cols:
			return int(r), int(c)
		return None


def create_chessboard(rows: int = values.ROWS, cols: int = values.COLS, square_size: int = values.SQUARE_SIZE, margin: int = values.MARGIN,
					  light_color: Color = values.LIGHT_COLOR, dark_color: Color = values.DARK_COLOR) -> ChessBoard:
	return ChessBoard(rows=rows, cols=cols, square_size=square_size, margin=margin,
					  light_color=light_color, dark_color=dark_color)

