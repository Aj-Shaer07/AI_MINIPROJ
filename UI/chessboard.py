import pygame
from typing import List, Optional, Tuple
import values
import pieces
import sys


Color = Tuple[int, int, int]


def _get_font(size: int, symbol: Optional[str] = None) -> pygame.font.Font:
	"""Return a pygame Font.

	If `symbol` is provided, prefer a font that can render that symbol
	(using `pieces.get_font_for_symbol`) so chess glyphs don't become tofu
	on platforms (notably macOS). Falls back to `values.FONT_NAME` then
	`pygame.font.SysFont`.
	"""
	# Try explicit symbol-capable font first
	if symbol:
		try:
			font_name = pieces.get_font_for_symbol(symbol, size=size)
			if font_name:
				path = pygame.font.match_font(font_name)
				if path:
					return pygame.font.Font(path, size)
		except Exception:
			pass
	# Next try configured font name
	if values.FONT_NAME:
		try:
			path = pygame.font.match_font(values.FONT_NAME)
			if path:
				return pygame.font.Font(path, size)
		except Exception:
			pass
	# Fallback to a generic system font
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
		# premove stored as (from_r, from_c, to_r, to_c)
		self.premove = None
		# Cache rendered piece surfaces: key = (symbol, size, fill_color, outline_color, outline_px)
		self._piece_surface_cache = {}
		self._last_piece_font_size: Optional[int] = None

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

		# draw premove (origin + destination) if present
		if getattr(self, 'premove', None):
			try:
				fr, fc, tr, tc = self.premove
				# prepare an overlay surface so we can draw with alpha easily
				over = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
				sq = self.square_size
				half = sq // 2
				# relative centers inside overlay (account for margin)
				ori = (self.margin + fc * sq + half, self.margin + fr * sq + half)
				dst = (self.margin + tc * sq + half, self.margin + tr * sq + half)
				# translucent fill on origin and destination squares
				for rr, cc in ((fr, fc), (tr, tc)):
					if 0 <= rr < self.rows and 0 <= cc < self.cols:
						rect_rel = pygame.Rect(self.margin + cc * sq, self.margin + rr * sq, sq, sq)
						pygame.draw.rect(over, values.PREMOVE_COLOR, rect_rel)
				# draw thick arrow line and arrowhead
				thick = max(3, sq // 10)
				pygame.draw.line(over, values.PREMOVE_COLOR, ori, dst, thick)
				# arrowhead (triangle) at destination
				import math
				dx = dst[0] - ori[0]
				dy = dst[1] - ori[1]
				dist = math.hypot(dx, dy)
				if dist > 0:
					norm_x = dx / dist
					norm_y = dy / dist
					size = max(8, sq // 6)
					# base point a little before dest so arrowhead sits nicely
					base_x = dst[0] - norm_x * (size * 0.6)
					base_y = dst[1] - norm_y * (size * 0.6)
					# perpendicular for width
					perp_x = -norm_y
					perp_y = norm_x
					p1 = (dst[0], dst[1])
					p2 = (base_x + perp_x * (size * 0.5), base_y + perp_y * (size * 0.5))
					p3 = (base_x - perp_x * (size * 0.5), base_y - perp_y * (size * 0.5))
					pygame.draw.polygon(over, values.PREMOVE_COLOR, [p1, p2, p3])
				# destination ring
				ring_r = max(6, sq // 4)
				pygame.draw.circle(over, values.PREMOVE_COLOR, dst, ring_r, max(3, sq // 18))
				# origin outline (rounded rect)
				orig_rect = pygame.Rect(self.margin + fc * sq + 4, self.margin + fr * sq + 4, sq - 8, sq - 8)
				pygame.draw.rect(over, values.PREMOVE_COLOR, orig_rect, max(3, sq // 14), border_radius=6)
				# blit overlay at board top-left
				surface.blit(over, (tx, ty))
			except Exception:
				pass

		# draw pieces with outlines and drop shadows
		piece_font_size = max(12, int(self.square_size * 0.82))
		# Invalidate cached surfaces when the font size changes (board resized)
		if self._last_piece_font_size != piece_font_size:
			self._piece_surface_cache.clear()
			self._last_piece_font_size = piece_font_size
		outline_px = getattr(values, 'PIECE_OUTLINE_PX', 2)
		# On Windows the default outlined rendering can make some glyphs
		# look boxed; prefer no outline there so the unicode glyphs render
		# as intended. macOS keeps the outline for visual style.
		if sys.platform.startswith('win'):
			outline_px = 0
		for r in range(self.rows):
			for c in range(self.cols):
				piece = self.board[r][c]
				if not piece:
					continue
				if isinstance(piece, (list, tuple)):
					symbol, color_key = piece[0], piece[1]
				else:
					symbol, color_key = piece, None
				# pick a font able to render this symbol (helps on macOS)
				piece_font = _get_font(piece_font_size, str(symbol))
				# Unicode-only rendering: draw outlined text with a soft shadow
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
