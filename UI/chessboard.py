import pygame
from typing import List, Optional, Tuple
import values


Color = Tuple[int, int, int]


def _get_font(size: int) -> pygame.font.Font:
	"""Return a pygame Font capable of rendering chess Unicode glyphs."""
	if values.FONT_NAME:
		try:
			path = pygame.font.match_font(values.FONT_NAME)
			if path:
				return pygame.font.Font(path, size)
		except Exception:
			pass
	return pygame.font.SysFont(None, size)


def _render_outlined_text(font: pygame.font.Font, text: str, fill_color, outline_color, outline_px: int = 1) -> pygame.Surface:
	"""Render text with a thin crisp outline for clean piece display."""
	base = font.render(text, True, fill_color)
	w, h = base.get_size()
	pad = outline_px * 2
	surf = pygame.Surface((w + pad, h + pad), pygame.SRCALPHA)
	# draw outline by blitting in 8 directions (single step for thin edge)
	outline_surf = font.render(text, True, outline_color)
	offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
	for ox, oy in offsets:
		surf.blit(outline_surf, (outline_px + ox * outline_px, outline_px + oy * outline_px))
	# draw fill on top
	surf.blit(base, (outline_px, outline_px))
	return surf


def draw_rounded_rect(surface: pygame.Surface, color, rect: pygame.Rect, radius: int, border: int = 0, border_color=None):
	"""Draw a rounded rectangle. If border > 0, draw only the border."""
	if border == 0:
		# filled
		pygame.draw.rect(surface, color, rect, border_radius=radius)
	else:
		pygame.draw.rect(surface, color, rect, border_radius=radius)
		if border_color:
			pygame.draw.rect(surface, border_color, rect, border, border_radius=radius)


class ChessBoard:
	"""A drawable, resizable chessboard model."""

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

		self.board: List[List[Optional[str]]] = [[None for _ in range(cols)] for _ in range(rows)]
		self.highlight: Optional[Tuple[int, int]] = None
		self.king_in_check: Optional[Tuple[int, int]] = None
		self.possible_moves: List[Tuple[int, int]] = []

	@property
	def width(self) -> int:
		return self.cols * self.square_size + 2 * self.margin

	@property
	def height(self) -> int:
		return self.rows * self.square_size + 2 * self.margin

	def draw(self, surface: pygame.Surface, top_left: Tuple[int, int] = (0, 0)) -> None:
		tx, ty = top_left
		coord_font = _get_font(max(12, self.square_size // 4))

		# board background with subtle rounded border
		board_rect = pygame.Rect(tx, ty, self.width, self.height)
		pygame.draw.rect(surface, (24, 24, 28), board_rect, border_radius=6)

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

		# highlight square
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

		# highlight king in check
		if self.king_in_check is not None:
			rk, ck = self.king_in_check
			rect = pygame.Rect(
				tx + self.margin + ck * self.square_size,
				ty + self.margin + rk * self.square_size,
				self.square_size,
				self.square_size,
			)
			glow = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
			center = (self.square_size // 2, self.square_size // 2)
			max_radius = self.square_size // 2
			steps = 6
			for i in range(steps, 0, -1):
				radius = max_radius * i // steps
				alpha = int(180 * (steps - i + 1) / steps)
				glow_color = (*values.CHECK_GLOW_COLOR, alpha)
				pygame.draw.circle(glow, glow_color, center, radius)
			surface.blit(glow, rect.topleft)

		# highlight possible moves
		for rm, cm in self.possible_moves:
			cx = tx + self.margin + cm * self.square_size + self.square_size // 2
			cy = ty + self.margin + rm * self.square_size + self.square_size // 2
			# check if target square has a piece (capture indicator: ring)
			target_piece = self.board[rm][cm]
			if target_piece:
				radius = self.square_size // 2 - 3
				s = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
				pygame.draw.circle(s, (100, 160, 80, 100), (self.square_size // 2, self.square_size // 2), radius, 4)
				sx = tx + self.margin + cm * self.square_size
				sy = ty + self.margin + rm * self.square_size
				surface.blit(s, (sx, sy))
			else:
				dot_surf = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
				radius = self.square_size // 6
				pygame.draw.circle(dot_surf, values.MOVE_DOT_COLOR, (self.square_size // 2, self.square_size // 2), radius)
				sx = tx + self.margin + cm * self.square_size
				sy = ty + self.margin + rm * self.square_size
				surface.blit(dot_surf, (sx, sy))

		# draw pieces with outlines and drop shadows
		piece_font_size = max(12, int(self.square_size * 0.82))
		piece_font = _get_font(piece_font_size)
		outline_px = getattr(values, 'PIECE_OUTLINE_PX', 2)
		for r in range(self.rows):
			for c in range(self.cols):
				piece = self.board[r][c]
				if not piece:
					continue
				if isinstance(piece, (list, tuple)):
					symbol, color_key = piece[0], piece[1]
				else:
					symbol, color_key = piece, None
				fill_color = values.PIECE_COLORS.get(color_key, values.PIECE_COLOR)
				outline_color = values.PIECE_OUTLINE_COLORS.get(color_key, (128, 128, 128))
				text = _render_outlined_text(piece_font, str(symbol), fill_color, outline_color, outline_px=outline_px)
				px = tx + self.margin + c * self.square_size + self.square_size // 2 - text.get_width() // 2
				py = ty + self.margin + r * self.square_size + self.square_size // 2 - text.get_height() // 2
				# soft drop shadow for depth
				shadow_surf = piece_font.render(str(symbol), True, (0, 0, 0))
				shadow_alpha = pygame.Surface(shadow_surf.get_size(), pygame.SRCALPHA)
				shadow_alpha.blit(shadow_surf, (0, 0))
				shadow_alpha.set_alpha(70)
				surface.blit(shadow_alpha, (px + 2, py + 2))
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
		"""Set a piece at (row,col)."""
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
