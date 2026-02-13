
import argparse
import pygame
import sys
import values
import pieces
import importlib
import chessboard
import chess
from game_controller import GameController


def parse_args():
	p = argparse.ArgumentParser(description='Chessboard UI')
	p.add_argument('--window-width', type=int, default=values.WINDOW_WIDTH, help='Window width in pixels')
	p.add_argument('--window-height', type=int, default=values.WINDOW_HEIGHT, help='Window height in pixels')
	p.add_argument('--rows', type=int, default=values.ROWS, help='Board rows')
	p.add_argument('--cols', type=int, default=values.COLS, help='Board cols')
	p.add_argument('--square-size', type=int, default=values.SQUARE_SIZE, help='Square size in pixels')
	p.add_argument('--margin', type=int, default=values.MARGIN, help='Board margin in pixels (around squares, for labels)')

	# engine options
	p.add_argument('--engine-depth', type=int, default=4, help='Engine max search depth')

	return p.parse_args()


# ── helpers ──────────────────────────────────────────────────────────────

def _draw_rounded_rect(surface, color, rect, radius, border=0, border_color=None):
	"""Utility to draw a filled rounded rect, optionally with border."""
	pygame.draw.rect(surface, color, rect, border_radius=radius)
	if border > 0 and border_color:
		pygame.draw.rect(surface, border_color, rect, border, border_radius=radius)


def _draw_shadow(surface, rect, radius=8, shadow_offset=4, alpha=60):
	"""Draw a drop-shadow behind a rect."""
	shadow_surf = pygame.Surface((rect.width + shadow_offset * 2, rect.height + shadow_offset * 2), pygame.SRCALPHA)
	shadow_rect = pygame.Rect(shadow_offset, shadow_offset, rect.width, rect.height)
	pygame.draw.rect(shadow_surf, (0, 0, 0, alpha), shadow_rect, border_radius=radius)
	surface.blit(shadow_surf, (rect.x - shadow_offset, rect.y - shadow_offset))


def _draw_button(surface, rect, text, font, bg_color, text_color, radius=8, border_color=None):
	"""Draw a styled button with text centered."""
	_draw_rounded_rect(surface, bg_color, rect, radius, border=2 if border_color else 0, border_color=border_color)
	text_surf = font.render(text, True, text_color)
	surface.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))


# ── captured pieces ─────────────────────────────────────────────────────

def captured_pieces_data(board_ref: chess.Board):
	"""Return (white_captured_list, black_captured_list).

	white_captured_list = pieces that White captured (i.e., missing Black pieces),
	shown as (symbol, count) tuples.
	black_captured_list = analogous for Black.
	"""
	initial = {
		chess.WHITE: {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1},
		chess.BLACK: {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1},
	}
	current = {
		chess.WHITE: {k: 0 for k in initial[chess.WHITE]},
		chess.BLACK: {k: 0 for k in initial[chess.BLACK]},
	}
	for piece in board_ref.piece_map().values():
		if piece.piece_type in current[piece.color]:
			current[piece.color][piece.piece_type] += 1
	order = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]
	white_captured = []  # pieces White captured = missing black pieces
	black_captured = []  # pieces Black captured = missing white pieces
	for ptype in order:
		missing_black = initial[chess.BLACK][ptype] - current[chess.BLACK][ptype]
		missing_white = initial[chess.WHITE][ptype] - current[chess.WHITE][ptype]
		if missing_black > 0:
			symbol = values.PIECE_SYMBOL_MAP[ptype][0]  # black piece symbol
			white_captured.extend([symbol] * missing_black)
		if missing_white > 0:
			symbol = values.PIECE_SYMBOL_MAP[ptype][1]  # white piece symbol
			black_captured.extend([symbol] * missing_white)
	return white_captured, black_captured


def draw_captured_bar(surface, captured_list, x, y, w, h, font, color, label, bg_color=None):
	"""Draw a horizontal strip showing captured pieces."""
	bar_rect = pygame.Rect(x, y, w, h)
	if bg_color:
		pygame.draw.rect(surface, bg_color, bar_rect, border_radius=4)
	# label
	label_surf = font.render(label, True, (140, 140, 150))
	surface.blit(label_surf, (x + 6, y + (h - label_surf.get_height()) // 2))
	# pieces
	offset_x = x + 6 + label_surf.get_width() + 6
	piece_font = chessboard._get_font(max(12, h - 6))
	for sym in captured_list:
		sym_surf = piece_font.render(sym, True, color)
		surface.blit(sym_surf, (offset_x, y + (h - sym_surf.get_height()) // 2))
		offset_x += sym_surf.get_width() + 1


# ── main ────────────────────────────────────────────────────────────────

def main():
	args = parse_args()
	pygame.init()

	board = chessboard.create_chessboard(rows=args.rows, cols=args.cols, square_size=args.square_size, margin=args.margin)

	# game controller (engine plays black by default)
	controller = GameController(max_depth=getattr(args, 'engine_depth', 4), engine_is_black=True)
	controller.sync_to_ui(board)

	move_history = []
	game_over_reason = None
	white_time_ms = 0
	black_time_ms = 0
	turn_start_ticks = pygame.time.get_ticks()

	# layout constants
	panel_margin = values.PANEL_MARGIN
	panel_w = values.PANEL_WIDTH
	captured_row_h = values._CAPTURED_ROW_H

	def reset_game() -> None:
		controller.board = chess.Board()
		controller.sync_to_ui(board)
		board.possible_moves = []
		board.king_in_check = None
		board.highlight = None
		move_history.clear()
		nonlocal game_over_reason
		game_over_reason = None
		nonlocal white_time_ms, black_time_ms, turn_start_ticks
		white_time_ms = 0
		black_time_ms = 0
		turn_start_ticks = pygame.time.get_ticks()
		nonlocal dragging, pending_drag, drag_piece, drag_from, selected_square, engine_pending
		dragging = False
		pending_drag = False
		drag_piece = None
		drag_from = None
		selected_square = None
		engine_pending = False

	def add_move(color_label: str, move: chess.Move, board_ref: chess.Board) -> None:
		uci = move.uci() if move else ""
		if not uci or len(uci) < 4:
			text = "? -> ?"
			symbol = "?"
		else:
			from_sq = uci[:2]
			to_sq = uci[2:4]
			promo = f"={uci[4].upper()}" if len(uci) > 4 else ""
			piece = board_ref.piece_at(move.to_square) if move else None
			if piece:
				symbol = values.PIECE_SYMBOL_MAP[piece.piece_type][0 if piece.color == chess.BLACK else 1]
			else:
				symbol = "?"
			text = f"{from_sq} -> {to_sq}{promo}"
		move_history.append((len(move_history) + 1, color_label, f"{symbol} {text}"))

	def game_over_text() -> str:
		if controller.board.is_checkmate():
			return "Checkmate"
		if controller.board.is_stalemate():
			return "Stalemate"
		if controller.board.is_insufficient_material():
			return "Draw — Insufficient Material"
		if controller.board.is_fivefold_repetition() or controller.board.is_seventyfive_moves():
			return "Draw — Repetition"
		return "Game Over"

	def is_game_over_ui() -> bool:
		return controller.board.is_game_over() or game_over_reason is not None

	def fmt_time(total_ms: int) -> str:
		total_sec = max(0, total_ms // 1000)
		minutes = total_sec // 60
		seconds = total_sec % 60
		return f"{minutes:02d}:{seconds:02d}"

	# drag / select state
	dragging = False
	pending_drag = False
	drag_piece = None
	drag_from = None
	drag_start_pos = (0, 0)
	mouse_pos = (0, 0)
	selected_square = None
	engine_pending = False
	drag_threshold = 6
	hover_resign = False

	window_w = args.window_width
	window_h = args.window_height

	screen = pygame.display.set_mode((window_w, window_h))
	pygame.display.set_caption('Chess — AI Engine')
	clock = pygame.time.Clock()

	# board positioning: board is on the left with captured strips above/below
	board_area_x = panel_margin
	board_area_y = panel_margin + captured_row_h
	top_left = (board_area_x, board_area_y)

	# panel occupies the space right of the board, same total height
	panel_x = board_area_x + board.width + panel_margin
	panel_y = panel_margin  # start from very top margin
	# total height available = captured_row + board + captured_row
	total_side_h = captured_row_h + board.height + captured_row_h

	# resign button sits inside bottom of the panel
	resign_button_h = 42
	resign_button_w = panel_w - 20  # a bit of internal padding

	running = True
	while running:
		mx, my = pygame.mouse.get_pos()
		mouse_pos = (mx, my)

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if is_game_over_ui():
					continue
				x, y = event.pos
				sq = board.pixel_to_square(x, y, top_left=top_left)
				if sq:
					r, c = sq
					piece = board.board[r][c]
					if selected_square and (r, c) in board.possible_moves:
						ok, move = controller.try_player_move(selected_square[0], selected_square[1], r, c)
						if ok:
							now = pygame.time.get_ticks()
							white_time_ms += now - turn_start_ticks
							turn_start_ticks = now
							controller.print_terminal()
							controller.sync_to_ui(board)
							add_move("White", move, controller.board)
							engine_pending = True
						selected_square = None
						board.highlight = None
						board.possible_moves = []
						pending_drag = False
						dragging = False
						drag_piece = None
						drag_from = None
						continue
					if piece:
						color_key = piece[1] if isinstance(piece, (list, tuple)) and len(piece) > 1 else None
						if controller.board.turn == chess.WHITE and color_key == 'white':
							if selected_square == (r, c):
								selected_square = None
								board.highlight = None
								board.possible_moves = []
								pending_drag = False
								drag_piece = None
								drag_from = None
							else:
								selected_square = (r, c)
								board.highlight = (r, c)
								board.possible_moves = controller.get_moves_for_square(r, c)
								pending_drag = True
								drag_piece = piece
								drag_from = (r, c)
								drag_start_pos = (x, y)
						else:
							selected_square = None
							board.highlight = (r, c)
							board.possible_moves = []
							pending_drag = False
							drag_piece = None
							drag_from = None
					else:
						selected_square = None
						board.highlight = None
						board.possible_moves = []
						pending_drag = False
						drag_piece = None
						drag_from = None
			elif event.type == pygame.MOUSEMOTION:
				x, y = event.pos
				mouse_pos = (x, y)
				if pending_drag and not dragging:
					dx = x - drag_start_pos[0]
					dy = y - drag_start_pos[1]
					if (dx * dx + dy * dy) >= (drag_threshold * drag_threshold):
						dragging = True
						pending_drag = False
						board.set_piece(drag_from[0], drag_from[1], None)
			elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				x, y = event.pos
				if dragging:
					sq = board.pixel_to_square(x, y, top_left=top_left)
					if sq:
						r2, c2 = sq
						ok, move = controller.try_player_move(drag_from[0], drag_from[1], r2, c2)
						if ok:
							now = pygame.time.get_ticks()
							white_time_ms += now - turn_start_ticks
							turn_start_ticks = now
							controller.print_terminal()
							controller.sync_to_ui(board)
							add_move("White", move, controller.board)
							engine_pending = True
						else:
							board.set_piece(drag_from[0], drag_from[1], drag_piece)
					else:
						board.set_piece(drag_from[0], drag_from[1], drag_piece)
					dragging = False
					pending_drag = False
					drag_piece = None
					drag_from = None
					board.possible_moves = []
					board.highlight = None
					selected_square = None
				else:
					pending_drag = False
					# resign button click
					resign_rect = pygame.Rect(
						panel_x + 10,
						panel_y + total_side_h - resign_button_h - 10,
						resign_button_w,
						resign_button_h,
					)
					if resign_rect.collidepoint((x, y)) and not is_game_over_ui():
						game_over_reason = "Resignation"
						controller.print_terminal()
						print("Result: Resigned — 0-1")
					# game-over popup reset button
					if is_game_over_ui():
						btn_w, btn_h = 160, 44
						popup_w, popup_h = 420, 270
						popup_x_pos = window_w // 2 - popup_w // 2
						popup_y_pos = window_h // 2 - popup_h // 2
						button_rect = pygame.Rect(
							window_w // 2 - btn_w // 2,
							popup_y_pos + popup_h - btn_h - 24,
							btn_w, btn_h
						)
						if button_rect.collidepoint((x, y)):
							reset_game()
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_r:
					importlib.reload(values)
					importlib.reload(pieces)
					importlib.reload(chessboard)
					board = chessboard.create_chessboard(rows=args.rows, cols=args.cols, square_size=args.square_size, margin=args.margin)
					controller = GameController(max_depth=getattr(args, 'engine_depth', 4), engine_is_black=True)
					controller.sync_to_ui(board)
					window_w = getattr(values, 'WINDOW_WIDTH', window_w)
					window_h = getattr(values, 'WINDOW_HEIGHT', window_h)
					screen = pygame.display.set_mode((window_w, window_h))
					pygame.display.set_caption('Chess — AI Engine')
					board_area_x = panel_margin
					board_area_y = panel_margin + captured_row_h
					top_left = (board_area_x, board_area_y)
					panel_x = board_area_x + board.width + panel_margin
					panel_y = panel_margin
					total_side_h = captured_row_h + board.height + captured_row_h
					white_time_ms = 0
					black_time_ms = 0
					turn_start_ticks = pygame.time.get_ticks()

		if controller.board.is_game_over() and game_over_reason is None:
			game_over_reason = game_over_text()

		# ── DRAW ────────────────────────────────────────────────────────
		screen.fill(values.BG_COLOR)

		# draw chessboard
		board.draw(screen, top_left=top_left)

		# ── captured pieces bars ────────────────────────────────────────
		cap_font = chessboard._get_font(14)
		white_caps, black_caps = captured_pieces_data(controller.board)

		# top bar (Black's captures / White pieces taken)
		draw_captured_bar(
			screen, black_caps,
			board_area_x, panel_margin,
			board.width, captured_row_h,
			cap_font, (200, 200, 200), "▼ ",
			bg_color=values.CAPTURED_BG,
		)
		# bottom bar (White's captures / Black pieces taken)
		draw_captured_bar(
			screen, white_caps,
			board_area_x, board_area_y + board.height,
			board.width, captured_row_h,
			cap_font, (200, 200, 200), "▲ ",
			bg_color=values.CAPTURED_BG,
		)

		# ── side panel (History + Timer + Resign) ───────────────────────
		# The panel spans the full height from top margin to bottom of captured bar
		panel_rect = pygame.Rect(panel_x, panel_y, panel_w, total_side_h)
		_draw_rounded_rect(screen, values.PANEL_BG_COLOR, panel_rect, 10, border=2, border_color=values.PANEL_BORDER_COLOR)

		# header bar
		header_rect = pygame.Rect(panel_x, panel_y, panel_w, 44)
		_draw_rounded_rect(screen, values.PANEL_HEADER_BG, header_rect, 10)
		# square off bottom corners of header (overlap with panel body)
		pygame.draw.rect(screen, values.PANEL_HEADER_BG, pygame.Rect(panel_x, panel_y + 20, panel_w, 24))

		title_font = chessboard._get_font(22)
		title_text = title_font.render("♜  Move History", True, values.PANEL_TITLE_COLOR)
		screen.blit(title_text, (panel_x + 14, panel_y + 12))

		# timer
		now_ticks = pygame.time.get_ticks()
		if not is_game_over_ui():
			if controller.board.turn == chess.WHITE:
				white_display = white_time_ms + (now_ticks - turn_start_ticks)
				black_display = black_time_ms
			else:
				white_display = white_time_ms
				black_display = black_time_ms + (now_ticks - turn_start_ticks)
		else:
			white_display = white_time_ms
			black_display = black_time_ms

		timer_font = chessboard._get_font(15)
		# timer row
		timer_y = panel_y + 52
		# white timer
		w_icon = timer_font.render("♔", True, (220, 220, 220))
		screen.blit(w_icon, (panel_x + 14, timer_y))
		w_time = timer_font.render(fmt_time(white_display), True, values.PANEL_TEXT_COLOR)
		screen.blit(w_time, (panel_x + 14 + w_icon.get_width() + 4, timer_y))
		# black timer
		b_icon = timer_font.render("♚", True, (180, 180, 180))
		b_time = timer_font.render(fmt_time(black_display), True, values.PANEL_TEXT_COLOR)
		bx = panel_x + panel_w - 14 - b_time.get_width()
		screen.blit(b_time, (bx, timer_y))
		screen.blit(b_icon, (bx - b_icon.get_width() - 4, timer_y))

		# turn indicator
		turn_label = "White's Turn" if controller.board.turn == chess.WHITE else "Black's Turn"
		if is_game_over_ui():
			turn_label = "Game Over"
		turn_font = chessboard._get_font(14)
		turn_surf = turn_font.render(turn_label, True, (150, 150, 158))
		screen.blit(turn_surf, (panel_x + 14, timer_y + 22))

		# separator line
		sep_y = timer_y + 44
		pygame.draw.line(screen, values.PANEL_BORDER_COLOR, (panel_x + 10, sep_y), (panel_x + panel_w - 10, sep_y), 1)

		# move history list
		item_font = chessboard._get_font(15)
		line_height = item_font.get_height() + 5
		history_top = sep_y + 8
		history_bottom = panel_y + total_side_h - resign_button_h - 24
		max_lines = max(1, (history_bottom - history_top) // line_height)
		recent_moves = move_history[-max_lines:]

		line_y = history_top
		for i, (move_no, color_label, move_text) in enumerate(recent_moves):
			# alternating subtle background
			if i % 2 == 0:
				row_rect = pygame.Rect(panel_x + 4, line_y - 1, panel_w - 8, line_height)
				pygame.draw.rect(screen, (30, 30, 34), row_rect, border_radius=3)
			# move number
			num_color = (95, 95, 105)
			num_surf = item_font.render(f"{move_no}.", True, num_color)
			screen.blit(num_surf, (panel_x + 12, line_y))
			# color dot
			dot_color = (230, 230, 230) if "White" in color_label else (70, 70, 70)
			dot_x = panel_x + 12 + num_surf.get_width() + 6
			dot_y_c = line_y + item_font.get_height() // 2
			pygame.draw.circle(screen, dot_color, (dot_x, dot_y_c), 4)
			pygame.draw.circle(screen, (140, 140, 150), (dot_x, dot_y_c), 4, 1)
			# move text
			text_surf = item_font.render(move_text, True, values.PANEL_TEXT_COLOR)
			screen.blit(text_surf, (dot_x + 10, line_y))
			line_y += line_height

		# resign button (inside panel, at bottom)
		resign_rect = pygame.Rect(
			panel_x + 10,
			panel_y + total_side_h - resign_button_h - 10,
			resign_button_w,
			resign_button_h,
		)
		hover_resign = resign_rect.collidepoint(mouse_pos)
		if is_game_over_ui():
			btn_color = values.RESIGN_BTN_DISABLED
		elif hover_resign:
			btn_color = values.RESIGN_BTN_HOVER
		else:
			btn_color = values.RESIGN_BTN_COLOR
		resign_font = chessboard._get_font(18)
		_draw_button(screen, resign_rect, "⚐  Resign", resign_font, btn_color, (255, 255, 255), radius=8, border_color=(100, 40, 40) if not is_game_over_ui() else (50, 50, 50))

		# ── status bar ──────────────────────────────────────────────────
		status_font = chessboard._get_font(16)
		if controller.board.is_checkmate() or game_over_reason:
			if controller.board.is_checkmate():
				winner = "White" if controller.board.turn == chess.BLACK else "Black"
				status_text = f"Winner: {winner}"
			else:
				status_text = game_over_reason if game_over_reason else "Game Over"
		else:
			turn_l = "White" if controller.board.turn == chess.WHITE else "Black"
			status_text = f"Turn: {turn_l}"
		status_surface = status_font.render(status_text, True, (140, 140, 150))
		status_y = min(window_h - status_surface.get_height() - 6, board_area_y + board.height + captured_row_h + 4)
		screen.blit(status_surface, (board_area_x + 4, status_y))

		# ── game over popup ─────────────────────────────────────────────
		if is_game_over_ui():
			# darken overlay
			overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
			overlay.fill((0, 0, 0, 140))
			screen.blit(overlay, (0, 0))

			popup_w, popup_h = 420, 270
			popup_x = window_w // 2 - popup_w // 2
			popup_y = window_h // 2 - popup_h // 2
			popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)

			# shadow
			_draw_shadow(screen, popup_rect, radius=16, shadow_offset=8, alpha=80)

			# popup background
			_draw_rounded_rect(screen, values.POPUP_BG, popup_rect, 16, border=2, border_color=values.POPUP_BORDER)

			# accent stripe at top
			stripe_rect = pygame.Rect(popup_x, popup_y, popup_w, 6)
			pygame.draw.rect(screen, values.POPUP_ACCENT, stripe_rect, border_radius=16)
			# cover bottom corners of stripe
			pygame.draw.rect(screen, values.POPUP_ACCENT, pygame.Rect(popup_x, popup_y, popup_w, 4))
			pygame.draw.rect(screen, values.POPUP_BG, pygame.Rect(popup_x + 2, popup_y + 4, popup_w - 4, 4))

			# title
			go_font = chessboard._get_font(30)
			if controller.board.is_checkmate():
				reason = "Checkmate!"
			elif game_over_reason:
				reason = game_over_reason
			else:
				reason = "Game Over"
			go_text = go_font.render(reason, True, (255, 255, 255))
			screen.blit(go_text, (popup_rect.centerx - go_text.get_width() // 2, popup_y + 30))

			# winner / result
			result_font = chessboard._get_font(22)
			if controller.board.is_checkmate():
				winner = "White" if controller.board.turn == chess.BLACK else "Black"
				result_line = f"🏆 Winner: {winner}"
				result_color = (255, 215, 0)
			elif game_over_reason and "Resign" in game_over_reason:
				result_line = "White Resigned — Black Wins"
				result_color = (200, 200, 210)
			else:
				result_line = "It's a Draw"
				result_color = (200, 200, 210)
			result_surf = result_font.render(result_line, True, result_color)
			screen.blit(result_surf, (popup_rect.centerx - result_surf.get_width() // 2, popup_y + 75))

			# stats
			stats_font = chessboard._get_font(16)
			moves_count = len(move_history)
			stats_line = f"Moves: {moves_count}   |   White: {fmt_time(white_display)}   Black: {fmt_time(black_display)}"
			stats_surf = stats_font.render(stats_line, True, (140, 140, 155))
			screen.blit(stats_surf, (popup_rect.centerx - stats_surf.get_width() // 2, popup_y + 120))

			# separator
			pygame.draw.line(screen, values.POPUP_BORDER, (popup_x + 30, popup_y + 155), (popup_x + popup_w - 30, popup_y + 155), 1)

			# reset button
			btn_w, btn_h = 160, 44
			button_rect = pygame.Rect(popup_rect.centerx - btn_w // 2, popup_y + popup_h - btn_h - 24, btn_w, btn_h)
			btn_hover = button_rect.collidepoint(mouse_pos)
			btn_bg = (220, 200, 160) if btn_hover else values.POPUP_ACCENT
			_draw_button(screen, button_rect, "▶  New Game", chessboard._get_font(18), btn_bg, (20, 20, 24), radius=10, border_color=(180, 160, 120))

		# draw dragged piece at mouse
		if dragging and drag_piece and mouse_pos:
			piece_font = chessboard._get_font(max(12, int(board.square_size * 0.9)))
			symbol = drag_piece[0] if isinstance(drag_piece, (list, tuple)) else drag_piece
			color_key = drag_piece[1] if isinstance(drag_piece, (list, tuple)) else None
			fill_color = values.PIECE_COLORS.get(color_key, values.PIECE_COLOR)
			outline_color = values.PIECE_OUTLINE_COLORS.get(color_key, (128, 128, 128))
			outline_px = getattr(values, 'PIECE_OUTLINE_PX', 2)
			text = chessboard._render_outlined_text(piece_font, str(symbol), fill_color, outline_color, outline_px=outline_px)
			x, y = mouse_pos
			screen.blit(text, (x - text.get_width() // 2, y - text.get_height() // 2))

		pygame.display.flip()

		if engine_pending and is_game_over_ui():
			engine_pending = False

		if engine_pending and not is_game_over_ui() and controller.board.turn == (not controller.engine_is_black):
			eng_move = controller.engine_move()
			now = pygame.time.get_ticks()
			black_time_ms += now - turn_start_ticks
			turn_start_ticks = now
			if eng_move:
				print(f"[ENGINE] plays: {eng_move}")
				controller.print_terminal()
				controller.sync_to_ui(board)
				add_move("Black (Engine)", eng_move, controller.board)
			engine_pending = False
		clock.tick(60)

	pygame.quit()
	sys.exit()


if __name__ == '__main__':
	main()
