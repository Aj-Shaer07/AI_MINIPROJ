
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

	# demo options removed

	return p.parse_args()


def main():
	args = parse_args()
	pygame.init()

	board = chessboard.create_chessboard(rows=args.rows, cols=args.cols, square_size=args.square_size, margin=args.margin)

	# game controller (engine plays black by default)
	controller = GameController(max_depth=getattr(args, 'engine_depth', 4), engine_is_black=True)
	# initialize UI from controller's starting position
	controller.sync_to_ui(board)

	move_history = []
	panel_margin = 10
	panel_w = values.PANEL_WIDTH
	resign_button_h = 40
	resign_button_w = panel_w
	game_over_reason = None
	white_time_ms = 0
	black_time_ms = 0
	turn_start_ticks = pygame.time.get_ticks()

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
				color_key = 'white' if piece.color == chess.WHITE else 'black'
				symbol = values.PIECE_SYMBOL_MAP[piece.piece_type][0 if piece.color == chess.BLACK else 1]
			else:
				symbol = "?"
			text = f"{from_sq} -> {to_sq}{promo}"
		move_history.append((len(move_history) + 1, color_label, f"{symbol} {text}"))

	def game_over_text() -> str:
		if controller.board.is_checkmate():
			return "Game Over - Checkmate"
		if controller.board.is_stalemate():
			return "Game Over - Stalemate"
		if controller.board.is_insufficient_material():
			return "Game Over - Draw"
		if controller.board.is_fivefold_repetition() or controller.board.is_seventyfive_moves():
			return "Game Over - Draw"
		return "Game Over"

	def is_game_over_ui() -> bool:
		return controller.board.is_game_over() or game_over_reason is not None

	def fmt_time(total_ms: int) -> str:
		total_sec = max(0, total_ms // 1000)
		minutes = total_sec // 60
		seconds = total_sec % 60
		return f"{minutes:02d}:{seconds:02d}"

	def captured_symbols(board_ref: chess.Board) -> tuple:
		initial = {
			chess.WHITE: {
				chess.PAWN: 8,
				chess.KNIGHT: 2,
				chess.BISHOP: 2,
				chess.ROOK: 2,
				chess.QUEEN: 1,
			},
			chess.BLACK: {
				chess.PAWN: 8,
				chess.KNIGHT: 2,
				chess.BISHOP: 2,
				chess.ROOK: 2,
				chess.QUEEN: 1,
			},
		}
		current = {
			chess.WHITE: {k: 0 for k in initial[chess.WHITE].keys()},
			chess.BLACK: {k: 0 for k in initial[chess.BLACK].keys()},
		}
		for piece in board_ref.piece_map().values():
			if piece.piece_type in current[piece.color]:
				current[piece.color][piece.piece_type] += 1
		order = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]
		label_map = {
			chess.QUEEN: "Q",
			chess.ROOK: "R",
			chess.BISHOP: "B",
			chess.KNIGHT: "N",
			chess.PAWN: "P",
		}
		white_captured = []
		black_captured = []
		for ptype in order:
			missing_black = initial[chess.BLACK][ptype] - current[chess.BLACK][ptype]
			missing_white = initial[chess.WHITE][ptype] - current[chess.WHITE][ptype]
			if missing_black > 0:
				symbol = values.PIECE_SYMBOL_MAP[ptype][0]
				label = label_map[ptype]
				white_captured.append(f"{label}x{missing_black}")
				white_captured.append(symbol * missing_black)
			if missing_white > 0:
				symbol = values.PIECE_SYMBOL_MAP[ptype][1]
				label = label_map[ptype]
				black_captured.append(f"{label}x{missing_white}")
				black_captured.append(symbol * missing_white)
		white_text = " ".join(white_captured) if white_captured else "None"
		black_text = " ".join(black_captured) if black_captured else "None"
		return white_text, black_text

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

	window_w = args.window_width
	window_h = args.window_height

	screen = pygame.display.set_mode((window_w, window_h))
	pygame.display.set_caption('Chessboard UI')
	clock = pygame.time.Clock()

	# compute top-left to center the board inside the window (leave space for panel)
	available_w = window_w - panel_w - (panel_margin * 2)
	top_left_x = max(panel_margin, (available_w - board.width) // 2 + panel_margin)
	top_left_y = max(panel_margin, (window_h - board.height) // 2)
	top_left = (top_left_x, top_left_y)

	running = True
	while running:
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
					# handle selecting a piece
					if piece:
						color_key = piece[1] if isinstance(piece, (list, tuple)) and len(piece) > 1 else None
						if controller.board.turn == chess.WHITE and color_key == 'white':
							# toggle selection
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
							# player move accepted
							controller.print_terminal()
							controller.sync_to_ui(board)
							add_move("White", move, controller.board)
							engine_pending = True
						else:
							# invalid move; restore piece
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
					resign_rect = pygame.Rect(
						window_w - panel_w - panel_margin,
						top_left_y + board.height + panel_margin,
						resign_button_w,
						resign_button_h,
					)
					if resign_rect.collidepoint((x, y)) and not is_game_over_ui():
						game_over_reason = "Game Over - Resignation"
						# print board/state to terminal when player resigns
						controller.print_terminal()
						# show resignation result in the same format as print_terminal
						print("Result: Resigned — 0-1")
					if is_game_over_ui():
						button_rect = pygame.Rect(window_w // 2 - 70, window_h // 2 + 10, 140, 40)
						if button_rect.collidepoint((x, y)):
							reset_game()
			elif event.type == pygame.KEYDOWN:
				# Press R to reload modules and refresh the UI without restarting
				if event.key == pygame.K_r:
					importlib.reload(values)
					importlib.reload(pieces)
					importlib.reload(chessboard)
					# recreate and resync
					board = chessboard.create_chessboard(rows=args.rows, cols=args.cols, square_size=args.square_size, margin=args.margin)
					controller = GameController(max_depth=getattr(args, 'engine_depth', 4), engine_is_black=True)
					controller.sync_to_ui(board)
					# update window size if values changed
					window_w = getattr(values, 'WINDOW_WIDTH', window_w)
					window_h = getattr(values, 'WINDOW_HEIGHT', window_h)
					screen = pygame.display.set_mode((window_w, window_h))
					pygame.display.set_caption('Chessboard UI')
					# recompute top-left so board recenters (leave space for panel)
					available_w = window_w - panel_w - (panel_margin * 2)
					top_left_x = max(panel_margin, (available_w - board.width) // 2 + panel_margin)
					top_left_y = max(panel_margin, (window_h - board.height) // 2)
					top_left = (top_left_x, top_left_y)
					white_time_ms = 0
					black_time_ms = 0
					turn_start_ticks = pygame.time.get_ticks()

		if controller.board.is_game_over() and game_over_reason is None:
			game_over_reason = game_over_text()


		screen.fill(values.BG_COLOR)
		board.draw(screen, top_left=top_left)

		# move log panel (match board height)
		panel_rect = pygame.Rect(
			window_w - panel_w - panel_margin,
			top_left_y,
			panel_w,
			board.height,
		)
		pygame.draw.rect(screen, values.PANEL_BG_COLOR, panel_rect)
		pygame.draw.rect(screen, values.PANEL_BORDER_COLOR, panel_rect, 2)
		title_font = chessboard._get_font(22)
		item_font = chessboard._get_font(16)
		title_text = title_font.render("History", True, values.PANEL_TITLE_COLOR)
		screen.blit(title_text, (panel_rect.x + 10, panel_rect.y + 10))
		# timer block
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
		timer_font = chessboard._get_font(16)
		white_text = timer_font.render(f"White: {fmt_time(white_display)}", True, values.PANEL_TEXT_COLOR)
		black_text = timer_font.render(f"Black: {fmt_time(black_display)}", True, values.PANEL_TEXT_COLOR)
		screen.blit(white_text, (panel_rect.x + 10, panel_rect.y + 40))
		screen.blit(black_text, (panel_rect.x + 10, panel_rect.y + 60))

		white_caps, black_caps = captured_symbols(controller.board)
		caps_font = chessboard._get_font(16)
		white_caps_text = caps_font.render(f"Captured by White: {white_caps}", True, values.PANEL_TEXT_COLOR)
		black_caps_text = caps_font.render(f"Captured by Black: {black_caps}", True, values.PANEL_TEXT_COLOR)
		screen.blit(white_caps_text, (panel_rect.x + 10, panel_rect.y + 85))
		screen.blit(black_caps_text, (panel_rect.x + 10, panel_rect.y + 105))

		line_y = panel_rect.y + 135
		line_height = item_font.get_height() + 4
		max_lines = max(1, (panel_rect.height - 50) // line_height)
		recent_moves = move_history[-max_lines:]
		for move_no, color_label, move_text in recent_moves:
			line = f"{move_no}. {color_label}: {move_text}"
			text = item_font.render(line, True, values.PANEL_TEXT_COLOR)
			screen.blit(text, (panel_rect.x + 10, line_y))
			line_y += line_height

		# resign button
		resign_rect = pygame.Rect(
			window_w - panel_w - panel_margin,
			panel_rect.bottom + panel_margin,
			resign_button_w,
			resign_button_h,
		)
		resign_color = (120, 60, 60) if not is_game_over_ui() else (70, 70, 70)
		pygame.draw.rect(screen, resign_color, resign_rect)
		pygame.draw.rect(screen, (0, 0, 0), resign_rect, 2)
		resign_font = chessboard._get_font(18)
		resign_text = resign_font.render("Resign", True, (255, 255, 255))
		screen.blit(resign_text, (resign_rect.centerx - resign_text.get_width() // 2, resign_rect.centery - resign_text.get_height() // 2))

		# draw game over popup
		if is_game_over_ui():
			overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
			overlay.fill((0, 0, 0, 160))
			screen.blit(overlay, (0, 0))
			popup_w = 360
			popup_h = 180
			popup_x = window_w // 2 - popup_w // 2
			popup_y = window_h // 2 - popup_h // 2
			popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
			pygame.draw.rect(screen, (40, 40, 40), popup_rect)
			pygame.draw.rect(screen, (120, 120, 120), popup_rect, 2)
			font = chessboard._get_font(28)
			if controller.board.is_checkmate():
				winner = "White" if controller.board.turn == chess.BLACK else "Black"
				reason = "Checkmate"
				winner_line = f"Winner: {winner}"
			else:
				reason = game_over_reason if game_over_reason else "Game Over"
				winner_line = None
			text = font.render(reason, True, (255, 255, 255))
			screen.blit(text, (popup_rect.centerx - text.get_width() // 2, popup_rect.y + 30))
			if winner_line:
				winner_font = chessboard._get_font(22)
				winner_text = winner_font.render(winner_line, True, (255, 255, 255))
				screen.blit(winner_text, (popup_rect.centerx - winner_text.get_width() // 2, popup_rect.y + 70))
			button_rect = pygame.Rect(popup_rect.centerx - 70, popup_rect.y + 110, 140, 40)
			pygame.draw.rect(screen, (170, 170, 170), button_rect)
			pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
			button_font = chessboard._get_font(20)
			button_text = button_font.render("Reset Game", True, (0, 0, 0))
			screen.blit(button_text, (button_rect.centerx - button_text.get_width() // 2, button_rect.centery - button_text.get_height() // 2))

		# draw dragged piece at mouse if any
		if dragging and drag_piece and mouse_pos:
			piece_font = chessboard._get_font(max(12, int(board.square_size * 0.9)))
			symbol = drag_piece[0] if isinstance(drag_piece, (list, tuple)) else drag_piece
			render_color = values.PIECE_COLORS.get(drag_piece[1], values.PIECE_COLOR) if isinstance(drag_piece, (list, tuple)) else values.PIECE_COLOR
			text = piece_font.render(str(symbol), True, render_color)
			x, y = mouse_pos
			screen.blit(text, (x - text.get_width() // 2, y - text.get_height() // 2))

		# status bar
		status_font = chessboard._get_font(18)
		if controller.board.is_checkmate() or game_over_reason:
			if controller.board.is_checkmate():
				winner = "White" if controller.board.turn == chess.BLACK else "Black"
				status_text = f"Winner: {winner}"
			else:
				status_text = game_over_reason if game_over_reason else "Game Over"
		else:
			turn_label = "White" if controller.board.turn == chess.WHITE else "Black"
			status_text = f"Turn: {turn_label}"
		status_surface = status_font.render(status_text, True, values.PANEL_TEXT_COLOR)
		status_y = min(window_h - status_surface.get_height() - 8, top_left_y + board.height + 8)
		screen.blit(status_surface, (top_left_x, status_y))
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

