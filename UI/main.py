import argparse
import pygame
import sys
import values
import pieces
import importlib
import chessboard
import chess
import threading
import queue
from game_controller import GameController
import evaluation_values
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

	# clock / time control (seconds)
	p.add_argument('--time', type=int, default=0, help='Initial time per side in seconds (0 = no clock)')
	p.add_argument('--increment', type=int, default=0, help='Increment per move in seconds')

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
	for sym in captured_list:
		# try image (PNG) or SVG first (size approx height minus padding)
		svg_size = max(12, h - 6)
		surf = pieces.get_piece_surface_for_symbol(sym, svg_size)
		if surf is not None:
			surface.blit(surf, (offset_x, y + (h - surf.get_height()) // 2))
			offset_x += surf.get_width() + 6
		else:
			# request a font that can render this symbol
			piece_font = chessboard._get_font(max(12, h - 6), sym)
			sym_surf = piece_font.render(sym, True, color)
			surface.blit(sym_surf, (offset_x, y + (h - sym_surf.get_height()) // 2))
			offset_x += sym_surf.get_width() + 1


# ── main ────────────────────────────────────────────────────────────────

def main(start_time=None, increment=None, human_color=None, fen=None):
	args = parse_args()
	# If called from the landing page, override CLI args with provided choices
	if start_time is not None:
		args.time = int(start_time)
	if increment is not None:
		args.increment = int(increment)
	pygame.init()

	board = chessboard.create_chessboard(rows=args.rows, cols=args.cols, square_size=args.square_size, margin=args.margin)

	# time control
	clock_enabled = getattr(args, 'time', 0) > 0
	initial_time_ms = int(getattr(args, 'time', 0)) * 1000
	increment_ms = int(getattr(args, 'increment', 0)) * 1000

	# game controller (engine plays black by default)
	# If user chose to play black, engine should play white (engine_is_black=False)
	engine_is_black = True
	if human_color is not None:
		engine_is_black = True if str(human_color).lower() == 'white' else False
	controller = GameController(max_depth=getattr(args, 'engine_depth', 4), engine_is_black=engine_is_black, fen=fen)
	controller.sync_to_ui(board)

	# human color determination (human is opposite of engine)
	human_color_key = 'white' if controller.engine_is_black else 'black'
	human_color_bool = chess.WHITE if human_color_key == 'white' else chess.BLACK
	# premove state: stored as (from_r, from_c, to_r, to_c)
	premove = None
	board.premove = None

	# Engine worker thread/queue for non-blocking search
	engine_thread = None
	engine_queue = queue.Queue()
	# cancellation event used to ignore/stop background worker results
	engine_cancel_event = threading.Event()

	move_history = []
	game_over_reason = None
	eval_display_info = None
	# evaluation bar animation state (centipawns)
	eval_cp_target = 0.0
	eval_cp_current = 0.0
	# timers: we keep both 'elapsed' and 'remaining' variables so switching
	# between modes is straightforward.
	white_time_ms = 0
	black_time_ms = 0
	white_remaining_ms = initial_time_ms
	black_remaining_ms = initial_time_ms
	turn_start_ticks = pygame.time.get_ticks()

	# layout constants are read from values.* directly where needed

	def reset_game() -> None:
		controller.board = chess.Board()
		controller.sync_to_ui(board)
		board.possible_moves = []
		board.king_in_check = None
		board.highlight = None
		move_history.clear()
		nonlocal game_over_reason
		game_over_reason = None
		nonlocal white_time_ms, black_time_ms, turn_start_ticks, white_remaining_ms, black_remaining_ms
		white_time_ms = 0
		black_time_ms = 0
		white_remaining_ms = initial_time_ms
		black_remaining_ms = initial_time_ms
		turn_start_ticks = pygame.time.get_ticks()
		nonlocal dragging, pending_drag, drag_piece, drag_from, selected_square, engine_pending, engine_thread, engine_queue, eval_cp_target, eval_cp_current, engine_cancel_event, promotion_pending
		dragging = False
		pending_drag = False
		drag_piece = None
		drag_from = None
		selected_square = None
		engine_pending = False
		promotion_pending = None
		# reset evaluation bar
		eval_cp_target = 0.0
		eval_cp_current = 0.0
		# cancel any running engine worker so its results won't be applied
		try:
			if engine_thread is not None and getattr(engine_thread, 'is_alive', lambda: False)():
				engine_cancel_event.set()
				try:
					engine_thread.join(timeout=0.2)
				except Exception:
					pass
		except Exception:
			pass
		engine_thread = None
		engine_cancel_event = threading.Event()
		# clear pending engine queue
		try:
			while not engine_queue.empty():
				engine_queue.get_nowait()
		except Exception:
			pass

	def apply_move_timing(is_engine_move: bool, now_ticks: int) -> None:
		"""Update timing variables after a move by engine or human.

		is_engine_move: True if engine moved, False for human.
		now_ticks: current pygame ticks when move completed.
		"""
		nonlocal white_time_ms, black_time_ms, white_remaining_ms, black_remaining_ms, turn_start_ticks
		elapsed = now_ticks - turn_start_ticks
		if is_engine_move:
			# update engine-side timers (engine may be White or Black)
			if values.SHOW_ENGINE_CLOCK:
				if clock_enabled:
					if controller.engine_is_black:
						black_remaining_ms -= elapsed
						if increment_ms:
							black_remaining_ms += increment_ms
					else:
						white_remaining_ms -= elapsed
						if increment_ms:
							white_remaining_ms += increment_ms
				else:
					if controller.engine_is_black:
						black_time_ms += elapsed
					else:
						white_time_ms += elapsed
		else:
			# human move timing (player clocks)
			if values.SHOW_PLAYER_CLOCK:
				if clock_enabled:
					if human_color_bool == chess.WHITE:
						white_remaining_ms -= elapsed
						if increment_ms:
							white_remaining_ms += increment_ms
					else:
						black_remaining_ms -= elapsed
						if increment_ms:
							black_remaining_ms += increment_ms
				else:
					if human_color_bool == chess.WHITE:
						white_time_ms += elapsed
					else:
						black_time_ms += elapsed
		turn_start_ticks = now_ticks

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
		return controller.board.is_game_over(claim_draw=False) or game_over_reason is not None

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
	promotion_pending = None  # (from_r, from_c, to_r, to_c) when awaiting promotion choice

	window_w = args.window_width
	window_h = args.window_height

	screen = pygame.display.set_mode((window_w, window_h))
	pygame.display.set_caption('Chess — AI Engine')
	clock = pygame.time.Clock()

	# board positioning: board is on the left with captured strips above/below
	# leave room for the evaluation bar to the left
	board_area_x = values.PANEL_MARGIN + values.EVAL_BAR_WIDTH + values.EVAL_BAR_GAP
	# nudge board up slightly to avoid overlap with bottom clock/labels
	board_area_y = values.PANEL_MARGIN + values._CAPTURED_ROW_H
	top_left = (board_area_x, board_area_y)

	# panel occupies the space right of the board, same total height
	panel_x = board_area_x + board.width + values.PANEL_MARGIN
	panel_y = values.PANEL_MARGIN  # start from very top margin
	# total height available = captured_row + board + captured_row
	total_side_h = values._CAPTURED_ROW_H + board.height + values._CAPTURED_ROW_H

	# resign button sits inside bottom of the panel
	# `RESIGN_BUTTON_H` moved into `values.py`; width computed at use-site

	running = True
	while running:
		mx, my = pygame.mouse.get_pos()
		mouse_pos = (mx, my)

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				# ── handle promotion popup click ──
				if promotion_pending is not None:
					x, y = event.pos
					pfr, pfc, ptr, ptc = promotion_pending
					# compute popup geometry (same as rendering below)
					promo_pieces = ['q', 'r', 'b', 'n']
					promo_sq_size = board.square_size
					promo_popup_w = promo_sq_size * 4 + 12
					promo_popup_h = promo_sq_size + 12
					# center popup horizontally on the target column
					target_px = top_left[0] + board.margin + ptc * board.square_size + board.square_size // 2
					promo_popup_x = target_px - promo_popup_w // 2
					# place popup just above or below the promotion rank
					if ptr == 0:  # promoting at top (white moving up)
						promo_popup_y = top_left[1] + board.margin + ptr * board.square_size
					else:  # promoting at bottom
						promo_popup_y = top_left[1] + board.margin + (ptr + 1) * board.square_size - promo_popup_h
					clicked_promo = None
					for i, pc in enumerate(promo_pieces):
						cell_x = promo_popup_x + 6 + i * promo_sq_size
						cell_y = promo_popup_y + 6
						cell_rect = pygame.Rect(cell_x, cell_y, promo_sq_size, promo_sq_size)
						if cell_rect.collidepoint(x, y):
							clicked_promo = pc
							break
					if clicked_promo:
						ok, move = controller.try_player_move_with_promotion(pfr, pfc, ptr, ptc, clicked_promo)
						if ok:
							now = pygame.time.get_ticks()
							apply_move_timing(False, now)
							controller.print_terminal()
							controller.sync_to_ui(board)
							add_move("White" if human_color_bool == chess.WHITE else "Black", move, controller.board)
							engine_pending = True
						promotion_pending = None
					else:
						# clicked outside popup — cancel promotion
						promotion_pending = None
						# restore the dragged piece if it was removed during drag
						controller.sync_to_ui(board)
					continue
				if is_game_over_ui():
					continue
				x, y = event.pos
				sq = board.pixel_to_square(x, y, top_left=top_left)
				if sq:
					r, c = sq
					piece = board.board[r][c]
					# destination click when a square is selected
					if selected_square and (r, c) in board.possible_moves:
						# if it's the human's turn, execute move immediately
						if controller.board.turn == human_color_bool:
							# check if this is a promotion move
							if controller.is_promotion_move(selected_square[0], selected_square[1], r, c):
								promotion_pending = (selected_square[0], selected_square[1], r, c)
							else:
								ok, move = controller.try_player_move(selected_square[0], selected_square[1], r, c)
								if ok:
									now = pygame.time.get_ticks()
									apply_move_timing(False, now)
									controller.print_terminal()
									controller.sync_to_ui(board)
									add_move("White" if human_color_bool == chess.WHITE else "Black", move, controller.board)
									engine_pending = True
						# otherwise store a premove to be executed when it's the human's turn
						else:
							premove = (selected_square[0], selected_square[1], r, c)
							board.premove = premove
						# clear selection UI state
						selected_square = None
						board.highlight = None
						board.possible_moves = []
						pending_drag = False
						drag_piece = None
						drag_from = None
						continue
					# piece clicked: if piece belongs to human, allow selection even when opponent to move
					if piece:
						color_key = piece[1] if isinstance(piece, (list, tuple)) and len(piece) > 1 else None
						if color_key == human_color_key:
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
								# when selecting our piece while off-turn, show legal moves for our side
								board.possible_moves = controller.get_moves_for_square(r, c, for_color=human_color_bool)
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
			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
				# right-click: cancel premove or selection
				if premove:
					premove = None
					board.premove = None
				else:
					selected_square = None
					board.highlight = None
					board.possible_moves = []
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
						# check if this is a promotion move
						if controller.is_promotion_move(drag_from[0], drag_from[1], r2, c2):
							# put the piece back and show promotion popup
							board.set_piece(drag_from[0], drag_from[1], drag_piece)
							promotion_pending = (drag_from[0], drag_from[1], r2, c2)
						else:
							ok, move = controller.try_player_move(drag_from[0], drag_from[1], r2, c2)
							if ok:
								now = pygame.time.get_ticks()
								apply_move_timing(False, now)
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
						panel_y + total_side_h - values.RESIGN_BUTTON_H - 10,
						values.PANEL_WIDTH - 20,
						values.RESIGN_BUTTON_H,
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
					window_w = values.WINDOW_WIDTH
					window_h = values.WINDOW_HEIGHT
					screen = pygame.display.set_mode((window_w, window_h))
					pygame.display.set_caption('Chess — AI Engine')
					# re-calc board position including eval bar space
					board_area_x = values.PANEL_MARGIN + values.EVAL_BAR_WIDTH + values.EVAL_BAR_GAP
					board_area_y = values.PANEL_MARGIN + values._CAPTURED_ROW_H
					top_left = (board_area_x, board_area_y)
					panel_x = board_area_x + board.width + values.PANEL_MARGIN
					panel_y = values.PANEL_MARGIN
					total_side_h = values._CAPTURED_ROW_H + board.height + values._CAPTURED_ROW_H
					white_time_ms = 0
					black_time_ms = 0
					white_remaining_ms = initial_time_ms
					black_remaining_ms = initial_time_ms
					turn_start_ticks = pygame.time.get_ticks()

		if controller.board.is_game_over() and game_over_reason is None:
			game_over_reason = game_over_text()

		# If a premove exists and it is now the human's turn, try to execute it
		if premove and controller.board.turn == human_color_bool and not is_game_over_ui():
			fr, fc, tr, tc = premove
			# clear stored premove immediately so we don't retry endlessly
			premove = None
			board.premove = None
			ok, move = controller.try_player_move(fr, fc, tr, tc)
			if ok:
				now = pygame.time.get_ticks()
				apply_move_timing(False, now)
				controller.print_terminal()
				controller.sync_to_ui(board)
				add_move("White" if human_color_bool == chess.WHITE else "Black", move, controller.board)
				engine_pending = True

		# ── DRAW ────────────────────────────────────────────────────────
		screen.fill(values.BG_COLOR)

		# draw chessboard
		board.draw(screen, top_left=top_left)

		# ── captured pieces bars ────────────────────────────────────────
		cap_font = chessboard._get_font(14)
		white_caps, black_caps = captured_pieces_data(controller.board)

		# top bar (Black's captures / White pieces taken)
		# top bar: pieces of White that Black has captured (show White pieces taken)
		draw_captured_bar(
			screen, black_caps,
			board_area_x, values.PANEL_MARGIN,
			board.width, values._CAPTURED_ROW_H,
			cap_font, (200, 200, 200), "White Captured",
			bg_color=values.CAPTURED_BG,
		)
		# bottom bar: pieces of Black that White has captured (show Black pieces taken)
		draw_captured_bar(
			screen, white_caps,
			board_area_x, board_area_y + board.height,
			board.width, values._CAPTURED_ROW_H,
			cap_font, (200, 200, 200), "Black Captured",
			bg_color=values.CAPTURED_BG,
		)

		# ── evaluation bar (left of board) ─────────────────────────────
		# animate current eval towards target with special handling for
		# extreme centipawn ranges and mate signals.
		# small easing factor for smooth motion
		try:
			raw = float(eval_cp_target)
		except Exception:
			raw = 0.0

		# detect mate information if provided by normalized eval dict
		mate_flag = None
		try:
			if eval_display_info:
				mate_flag = eval_display_info.get('mate')
		except Exception:
			mate_flag = None

		sign = 1.0 if raw >= 0 else -1.0
		# determine a target fraction (-1.0..1.0) for display
		if mate_flag is not None:
			target_frac = sign * values.EVAL_BAR_MATE_FILL
		elif values.EVAL_BAR_EXTREME_MIN_CP <= abs(raw) <= values.EVAL_BAR_EXTREME_MAX_CP:
			# extreme CPs map to a near-full fill but not completely to the edge
			target_frac = sign * values.EVAL_BAR_EXTREME_FILL
		else:
			# normal linear mapping to configured max
			target_frac = max(-1.0, min(1.0, raw / values.EVAL_BAR_MAX_CP))

		# target in centipawns to animate towards
		clamped_target = target_frac * values.EVAL_BAR_MAX_CP
		# interpolate
		eval_cp_current += (clamped_target - eval_cp_current) * 0.12

		# drawing geometry
		bar_h = board.height
		bar_w = values.EVAL_BAR_WIDTH
		bar_x = board_area_x - bar_w - values.EVAL_BAR_GAP
		bar_y = board_area_y

		# background track
		track_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
		pygame.draw.rect(screen, values.EVAL_BAR_BG, track_rect, border_radius=6)

		# center baseline
		mid_y = bar_y + bar_h // 2
		pygame.draw.line(screen, (60, 60, 64), (bar_x + 2, mid_y), (bar_x + bar_w - 2, mid_y), 2)

		# compute fill fraction from eval_cp_current
		frac = max(-1.0, min(1.0, eval_cp_current / values.EVAL_BAR_MAX_CP))
		# positive -> White advantage (fill upward), negative -> Black advantage (fill downward)
		if frac > 0:
			fill_h = int((bar_h / 2) * frac)
			fill_rect = pygame.Rect(bar_x + 2, int(mid_y - fill_h), bar_w - 4, fill_h)
			pygame.draw.rect(screen, values.EVAL_BAR_WHITE_COLOR, fill_rect, border_radius=4)
			marker_y = int(mid_y - fill_h)
			marker_color = values.EVAL_BAR_WHITE_COLOR
		elif frac < 0:
			fill_h = int((bar_h / 2) * (-frac))
			fill_rect = pygame.Rect(bar_x + 2, mid_y, bar_w - 4, fill_h)
			pygame.draw.rect(screen, values.EVAL_BAR_BLACK_COLOR, fill_rect, border_radius=4)
			marker_y = int(mid_y + fill_h)
			marker_color = values.EVAL_BAR_BLACK_COLOR
		else:
			# neutral: small marker at center
			marker_y = mid_y
			marker_color = (180, 180, 180)

		# numeric display (centipawns) above the bar
		try:
			disp_val = int(eval_cp_current)
		except Exception:
			disp_val = 0
		val_font = chessboard._get_font(14)
		# Only display mate information (e.g. M3). Do not show centipawn values.
		val_font = chessboard._get_font(14)
		if mate_flag is not None:
			try:
				m = int(mate_flag)
				text = f"M{abs(m)}"
			except Exception:
				text = "M"
			# Render with a small dark rounded background and outlined text for contrast
			try:
				txt_surf = chessboard._render_outlined_text(val_font, text, (255, 245, 200), (16, 16, 16), outline_px=1)
			except Exception:
				# fallback to simple render
				txt_surf = val_font.render(text, True, values.EVAL_BAR_TEXT_COLOR)
			pad_x, pad_y = values.EVAL_LABEL_PAD_X, values.EVAL_LABEL_PAD_Y
			bg_x = bar_x - txt_surf.get_width() - 6 - pad_x
			bg_y = bar_y + 4 - pad_y
			bg_rect = pygame.Rect(bg_x, bg_y, txt_surf.get_width() + pad_x * 2, txt_surf.get_height() + pad_y * 2)
			# slightly translucent dark background to ensure legibility
			pygame.draw.rect(screen, values.EVAL_LABEL_BG, bg_rect, border_radius=6)
			pygame.draw.rect(screen, values.EVAL_LABEL_BORDER, bg_rect, 1, border_radius=6)
			screen.blit(txt_surf, (bg_rect.x + pad_x, bg_rect.y + pad_y))

		# draw a small triangle marker like chess.com at the edge of the fill
		# center x for marker
		mx = bar_x + bar_w // 2
		# clamp marker within track
		marker_y = max(bar_y + 4, min(bar_y + bar_h - 4, marker_y))
		tri_h = 8
		if frac >= 0:
			# triangle pointing up
			points = [(mx - 6, marker_y + tri_h), (mx + 6, marker_y + tri_h), (mx, marker_y)]
		else:
			# triangle pointing down
			points = [(mx - 6, marker_y - tri_h), (mx + 6, marker_y - tri_h), (mx, marker_y)]
		pygame.draw.polygon(screen, marker_color, points)
		pygame.draw.polygon(screen, (30, 30, 30), points, 1)

		# ── side panel (History + Timer + Resign) ───────────────────────
		# The panel spans the full height from top margin to bottom of captured bar
		panel_rect = pygame.Rect(panel_x, panel_y, values.PANEL_WIDTH, total_side_h)
		_draw_rounded_rect(screen, values.PANEL_BG_COLOR, panel_rect, 10, border=2, border_color=values.PANEL_BORDER_COLOR)

		# header bar
		header_rect = pygame.Rect(panel_x, panel_y, values.PANEL_WIDTH, 44)
		_draw_rounded_rect(screen, values.PANEL_HEADER_BG, header_rect, 10)
		# square off bottom corners of header (overlap with panel body)
		pygame.draw.rect(screen, values.PANEL_HEADER_BG, pygame.Rect(panel_x, panel_y + 20, values.PANEL_WIDTH, 24))

		title_font = chessboard._get_font(22)
		title_text = title_font.render("♜  Move History", True, values.PANEL_TITLE_COLOR)
		screen.blit(title_text, (panel_x + values.PANEL_PADDING, panel_y + 12))

		# timer
		now_ticks = pygame.time.get_ticks()
		# Determine which side's clock is active based on toggle
		white_is_player = controller.engine_is_black
		white_clock_on = values.SHOW_PLAYER_CLOCK if white_is_player else values.SHOW_ENGINE_CLOCK
		black_clock_on = values.SHOW_ENGINE_CLOCK if controller.engine_is_black else values.SHOW_PLAYER_CLOCK

		elapsed_ticks = now_ticks - turn_start_ticks
		if clock_enabled:
			if not is_game_over_ui():
				if controller.board.turn == chess.WHITE and white_clock_on:
					white_display = white_remaining_ms - elapsed_ticks
				else:
					white_display = white_remaining_ms
				if controller.board.turn == chess.BLACK and black_clock_on:
					black_display = black_remaining_ms - elapsed_ticks
				else:
					black_display = black_remaining_ms
			else:
				white_display = white_remaining_ms
				black_display = black_remaining_ms
		else:
			if not is_game_over_ui():
				if controller.board.turn == chess.WHITE and white_clock_on:
					white_display = white_time_ms + elapsed_ticks
				else:
					white_display = white_time_ms
				if controller.board.turn == chess.BLACK and black_clock_on:
					black_display = black_time_ms + elapsed_ticks
				else:
					black_display = black_time_ms
			else:
				white_display = white_time_ms
				black_display = black_time_ms

		# timeout detection (only when that side's clock is toggled on)
		if clock_enabled and not is_game_over_ui():
			if controller.board.turn == chess.WHITE and white_clock_on and white_display <= 0:
				game_over_reason = "Timeout — White"
				controller.print_terminal()
				print("Result: Timeout — Black wins")
			elif controller.board.turn == chess.BLACK and black_clock_on and black_display <= 0:
				game_over_reason = "Timeout — Black"
				controller.print_terminal()
				print("Result: Timeout — White wins")


		# Draw dedicated clock UI near the board (top = Black, bottom = White)
		clock_w = min(values.CLOCK_WIDTH, board.width // 3)
		clock_h = values.CLOCK_HEIGHT
		clock_x = board_area_x + board.width - clock_w - values.CLOCK_MARGIN
		top_clock_y = values.PANEL_MARGIN + (values._CAPTURED_ROW_H - clock_h) // 2
		# add a small gap above the bottom clock so it doesn't touch board labels
		bottom_clock_y = board_area_y + board.height + (values._CAPTURED_ROW_H - clock_h) // 2 + values.ELEMENT_GAP

		clock_font = chessboard._get_font(26)

		# Determine which side is player/engine for top (Black) and bottom (White)
		top_is_engine = controller.engine_is_black       # engine is Black → top is engine
		bot_is_engine = not controller.engine_is_black    # engine is White → bottom is engine
		show_top_clock = values.SHOW_ENGINE_CLOCK if top_is_engine else values.SHOW_PLAYER_CLOCK
		show_bot_clock = values.SHOW_ENGINE_CLOCK if bot_is_engine else values.SHOW_PLAYER_CLOCK

		# top clock (Black) — only rendered when visible flag is on
		if show_top_clock:
			black_active = (controller.board.turn == chess.BLACK) and not is_game_over_ui()
			black_bg = values.CLOCK_ACTIVE_BG if black_active else values.CLOCK_INACTIVE_BG
			black_text_color = values.CLOCK_ACTIVE_TEXT if black_active else values.CLOCK_INACTIVE_TEXT
			top_rect = pygame.Rect(clock_x, top_clock_y, clock_w, clock_h)
			_draw_rounded_rect(screen, black_bg, top_rect, values.CLOCK_RADIUS)
			black_time_surf = clock_font.render(fmt_time(black_display), True, black_text_color)
			screen.blit(black_time_surf, (top_rect.centerx - black_time_surf.get_width() // 2, top_rect.centery - black_time_surf.get_height() // 2))

		# bottom clock (White) — only rendered when visible flag is on
		if show_bot_clock:
			white_active = (controller.board.turn == chess.WHITE) and not is_game_over_ui()
			white_bg = values.CLOCK_ACTIVE_BG if white_active else values.CLOCK_INACTIVE_BG
			white_text_color = values.CLOCK_ACTIVE_TEXT if white_active else values.CLOCK_INACTIVE_TEXT
			bottom_rect = pygame.Rect(clock_x, bottom_clock_y, clock_w, clock_h)
			_draw_rounded_rect(screen, white_bg, bottom_rect, values.CLOCK_RADIUS)
			white_time_surf = clock_font.render(fmt_time(white_display), True, white_text_color)
			screen.blit(white_time_surf, (bottom_rect.centerx - white_time_surf.get_width() // 2, bottom_rect.centery - white_time_surf.get_height() // 2))

		# small turn indicator inside the side panel (keeps layout semantics)
		turn_label = "White's Turn" if controller.board.turn == chess.WHITE else "Black's Turn"
		if is_game_over_ui():
			turn_label = "Game Over"
		turn_font = chessboard._get_font(14)
		turn_surf = turn_font.render(turn_label, True, (150, 150, 158))
		screen.blit(turn_surf, (panel_x + 14, panel_y + 52 + 22))

		# separator line (maintain previous spacing for history area)
		sep_y = panel_y + 52 + 44
		pygame.draw.line(screen, values.PANEL_BORDER_COLOR, (panel_x + 10, sep_y), (panel_x + values.PANEL_WIDTH - 10, sep_y), 1)

		# move history list
		item_font = chessboard._get_font(15)
		line_height = item_font.get_height() + 5
		history_top = sep_y + 8
		history_bottom = panel_y + total_side_h - values.RESIGN_BUTTON_H - 24
		max_lines = max(1, (history_bottom - history_top) // line_height)
		recent_moves = move_history[-max_lines:]

		line_y = history_top
		for i, (move_no, color_label, move_text) in enumerate(recent_moves):
			# alternating subtle background
			if i % 2 == 0:
				row_rect = pygame.Rect(panel_x + 4, line_y - 1, values.PANEL_WIDTH - 8, line_height)
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

		# Draw evaluation info box to the right of the panel (outside panel)
		if eval_display_info:
			info_x = panel_x + values.PANEL_WIDTH + values.EVAL_BOX_MARGIN
			info_y = panel_y + 12
			info_w = values.EVAL_BOX_WIDTH
			info_h = values.EVAL_BOX_HEIGHT
			info_rect = pygame.Rect(info_x, info_y, info_w, info_h)
			_draw_rounded_rect(screen, values.EVAL_BOX_BG, info_rect, 10, border=2, border_color=values.EVAL_BOX_BORDER)
			title_font = chessboard._get_font(16)
			title_surf = title_font.render("Engine Evaluation", True, values.EVAL_BOX_TITLE_COLOR)
			screen.blit(title_surf, (info_x + 12, info_y + 8))
			val_font = chessboard._get_font(14)
			lines = [
				f"Eval: {eval_display_info.get('eval_cp', 0)} cp",
				f"Depth: {eval_display_info.get('depth', 0)}",
				f"Time: {eval_display_info.get('time_s', 0)} sec",
				f"Nodes: {eval_display_info.get('nodes', 0)}",
				f"Cutoffs: {eval_display_info.get('cutoffs', 0)}",
				f"TT hits: {eval_display_info.get('tt_hits', 0)}",
				f"MaxPly: {eval_display_info.get('max_ply', 0)}",
			]
			ly = info_y + 36
			for ln in lines:
				ls = val_font.render(ln, True, values.EVAL_BOX_TEXT_COLOR)
				screen.blit(ls, (info_x + 12, ly))
				ly += ls.get_height() + 6

		# resign button (inside panel, at bottom)
		resign_rect = pygame.Rect(
			panel_x + 10,
			panel_y + total_side_h - values.RESIGN_BUTTON_H - 10,
			values.PANEL_WIDTH - 20,
			values.RESIGN_BUTTON_H,
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
		status_y = min(window_h - status_surface.get_height() - 6, board_area_y + board.height + values._CAPTURED_ROW_H + 4)
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
				result_line = f"Winner: {winner}"
				result_color = (255, 215, 0)
			elif game_over_reason and "Resign" in game_over_reason:
				result_line = "White Resigned — Black Wins"
				result_color = (200, 200, 210)
			elif game_over_reason and "Timeout" in game_over_reason:
				# game_over_reason format: "Timeout — White" or "Timeout — Black"
				if "White" in game_over_reason:
					result_line = "White Timed Out — Black Wins"
				else:
					result_line = "Black Timed Out — White Wins"
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
			# prefer SVG for dragged piece
			svg_size = max(12, int(board.square_size * 0.9))
			symbol = drag_piece[0] if isinstance(drag_piece, (list, tuple)) else drag_piece
			color_key = drag_piece[1] if isinstance(drag_piece, (list, tuple)) else None
			# unified loader: PNG -> SVG -> placeholder
			surf = pieces.get_piece_surface_for_symbol(str(symbol), svg_size) if symbol else None
			# explicit color override
			if surf is None and symbol and color_key:
				piece_name = pieces.name_from_symbol(str(symbol))
				surf = pieces.get_piece_surface(piece_name, color_key, svg_size)
			x, y = mouse_pos
			if surf is not None:
				screen.blit(surf, (x - surf.get_width() // 2, y - surf.get_height() // 2))
			else:
				piece_font = chessboard._get_font(svg_size)
				fill_color = values.PIECE_COLORS.get(color_key, values.PIECE_COLOR)
				outline_color = values.PIECE_OUTLINE_COLORS.get(color_key, (128, 128, 128))
				outline_px = values.PIECE_OUTLINE_PX
				text = chessboard._render_outlined_text(piece_font, str(symbol), fill_color, outline_color, outline_px=outline_px)
				screen.blit(text, (x - text.get_width() // 2, y - text.get_height() // 2))

		# ── promotion popup overlay ──────────────────────────────────────
		if promotion_pending is not None:
			# dim overlay
			overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
			overlay.fill((0, 0, 0, 100))
			screen.blit(overlay, (0, 0))

			pfr, pfc, ptr, ptc = promotion_pending
			promo_pieces_list = ['q', 'r', 'b', 'n']
			promo_piece_types = {
				'q': chess.QUEEN, 'r': chess.ROOK,
				'b': chess.BISHOP, 'n': chess.KNIGHT
			}
			promo_sq_size = board.square_size
			promo_popup_w = promo_sq_size * 4 + 12
			promo_popup_h = promo_sq_size + 12
			# center popup on target column
			target_px = top_left[0] + board.margin + ptc * board.square_size + board.square_size // 2
			promo_popup_x = target_px - promo_popup_w // 2
			if ptr == 0:
				promo_popup_y = top_left[1] + board.margin + ptr * board.square_size
			else:
				promo_popup_y = top_left[1] + board.margin + (ptr + 1) * board.square_size - promo_popup_h

			popup_rect = pygame.Rect(promo_popup_x, promo_popup_y, promo_popup_w, promo_popup_h)
			_draw_shadow(screen, popup_rect, radius=values.PROMO_POPUP_RADIUS, shadow_offset=6, alpha=80)
			_draw_rounded_rect(screen, values.PROMO_POPUP_BG, popup_rect, values.PROMO_POPUP_RADIUS, border=2, border_color=values.PROMO_POPUP_BORDER)

			promo_font = chessboard._get_font(int(promo_sq_size * 0.7))
			for i, pc in enumerate(promo_pieces_list):
				cell_x = promo_popup_x + 6 + i * promo_sq_size
				cell_y = promo_popup_y + 6
				cell_rect = pygame.Rect(cell_x, cell_y, promo_sq_size, promo_sq_size)
				# hover highlight
				if cell_rect.collidepoint(mouse_pos):
					_draw_rounded_rect(screen, values.PROMO_POPUP_HOVER, cell_rect, 6)
				# render piece symbol using human's color
				pt = promo_piece_types[pc]
				sym_idx = 0 if human_color_bool == chess.BLACK else 1
				sym = values.PIECE_SYMBOL_MAP[pt][sym_idx]
				color_key = 'white' if human_color_bool == chess.WHITE else 'black'
				# try surface first, fall back to text
				p_surf = pieces.get_piece_surface_for_symbol(str(sym), int(promo_sq_size * 0.8))
				if p_surf is None:
					p_surf = pieces.get_piece_surface(pieces.name_from_symbol(str(sym)), color_key, int(promo_sq_size * 0.8))
				if p_surf is not None:
					screen.blit(p_surf, (cell_rect.centerx - p_surf.get_width() // 2, cell_rect.centery - p_surf.get_height() // 2))
				else:
					fill_color = values.PIECE_COLORS.get(color_key, values.PIECE_COLOR)
					outline_color = values.PIECE_OUTLINE_COLORS.get(color_key, (128, 128, 128))
					txt = chessboard._render_outlined_text(promo_font, str(sym), fill_color, outline_color, outline_px=values.PIECE_OUTLINE_PX)
					screen.blit(txt, (cell_rect.centerx - txt.get_width() // 2, cell_rect.centery - txt.get_height() // 2))

		pygame.display.flip()

		if engine_pending and is_game_over_ui():
			engine_pending = False

		# Engine: start background worker when engine needs to move; apply result when ready
		if engine_pending and not is_game_over_ui() and controller.board.turn == (not controller.engine_is_black):
			# Start worker thread if not already running
			if engine_thread is None:
					def _engine_worker(cancel_event):
						try:
							import algorithms.search as engine_search
							# search on a copy so we don't mutate the UI/main thread board
							board_copy = controller.board.copy()
							move, info = engine_search.search_with_info(board_copy, controller.max_depth, engine_is_black=controller.engine_is_black)
							# If cancelled while searching, drop the result
							if cancel_event.is_set():
								return
							engine_queue.put((move, info))
						except Exception as e:
							logger.exception("[ENGINE ERROR]")
							try:
								engine_queue.put((None, None))
							except Exception:
								pass
					engine_thread = threading.Thread(target=_engine_worker, args=(engine_cancel_event,), daemon=True)
					engine_thread.start()
			else:
				# worker finished? retrieve and apply result
				if not engine_thread.is_alive():
					eng_move = None
					try:
						eng_move = engine_queue.get_nowait()
					except queue.Empty:
						eng_move = None

					# update timing for engine side (only if engine clock toggled on)
					now = pygame.time.get_ticks()
					apply_move_timing(True, now)
					# if cancelled while pending, ignore result
					if engine_cancel_event.is_set():
						eng_move = None

					if eng_move:
						# push move on main thread (so UI sync is safe)
						# keep the original engine result so we can extract eval info
						eng_result = eng_move
						# normalize to canonical dict for display
						try:
							eval_display_info = evaluation_values.search_result_to_dict(eng_result)
						except Exception:
							eval_display_info = None
						# update animated evaluation target (centipawns)
						try:
							eval_cp_target = float(eval_display_info.get('eval_cp', 0)) if eval_display_info else 0.0
						except Exception:
							eval_cp_target = 0.0
						# extract actual move object
						move_obj = None
						if isinstance(eng_result, (list, tuple)) and len(eng_result) > 0:
							move_obj = eng_result[0]
						elif isinstance(eng_result, dict):
							move_obj = eng_result.get("move")
						# try UCI fallback
						if move_obj is None and eval_display_info and eval_display_info.get("move_uci"):
							try:
								move_obj = chess.Move.from_uci(eval_display_info.get("move_uci"))
							except Exception:
								move_obj = None
						try:
							san = controller.board.san(move_obj) if move_obj is not None else None
						except Exception:
							san = None
						if move_obj is not None:
							controller.board.push(move_obj)
							controller.last_move = move_obj
							controller.last_move_san = san
							logger.info(f"[ENGINE] plays: {move_obj}")
							controller.print_terminal()
							controller.sync_to_ui(board)
							label = "Black (Engine)" if controller.engine_is_black else "White (Engine)"
							add_move(label, move_obj, controller.board)
						# cleanup
					engine_pending = False
					engine_thread = None
		clock.tick(60)

	pygame.quit()
	sys.exit()


if __name__ == '__main__':
	try:
		import landing

		landing.show_and_run(main)
	except Exception:
		# If landing fails for any reason, fall back to starting the game directly
		main()
