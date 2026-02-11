
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

	def reset_game() -> None:
		controller.board = chess.Board()
		controller.sync_to_ui(board)
		board.possible_moves = []
		board.king_in_check = None
		board.highlight = None
		move_history.clear()
		nonlocal game_over_reason
		game_over_reason = None

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

	# drag state
	dragging = False
	drag_piece = None
	drag_from = None
	mouse_pos = (0, 0)

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
					if piece:
						# allow dragging only for player's pieces (white)
						color_key = piece[1] if isinstance(piece, (list, tuple)) and len(piece) > 1 else None
						if controller.board.turn == chess.WHITE and color_key == 'white':
							dragging = True
							drag_piece = piece
							drag_from = (r, c)
							board.set_piece(r, c, None)
							# show possible moves
							moves = controller.get_moves_for_square(r, c)
							board.possible_moves = moves
						else:
							# toggle highlight for non-draggable squares
							if board.highlight == (r, c):
								board.highlight = None
							else:
								board.highlight = (r, c)
					else:
						if board.highlight == (r, c):
							board.highlight = None
						else:
							board.highlight = (r, c)
			elif event.type == pygame.MOUSEMOTION:
				x, y = event.pos
				mouse_pos = (x, y)
			elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				x, y = event.pos
				if dragging:
					sq = board.pixel_to_square(x, y, top_left=top_left)
					if sq:
						r2, c2 = sq
						ok, move = controller.try_player_move(drag_from[0], drag_from[1], r2, c2)
						if ok:
							# player move accepted
							controller.print_terminal()
							controller.sync_to_ui(board)
							add_move("White", move, controller.board)
							# engine move (if any)
							if not controller.board.is_game_over() and controller.board.turn == (not controller.engine_is_black):
								eng_move = controller.engine_move()
								if eng_move:
									print(f"[ENGINE] plays: {eng_move}")
									controller.print_terminal()
									controller.sync_to_ui(board)
									add_move("Black (Engine)", eng_move, controller.board)
						else:
							# invalid move; restore piece
							board.set_piece(drag_from[0], drag_from[1], drag_piece)
					else:
						board.set_piece(drag_from[0], drag_from[1], drag_piece)
					dragging = False
					drag_piece = None
					drag_from = None
					board.possible_moves = []
				else:
					resign_rect = pygame.Rect(window_w - panel_w - panel_margin, panel_margin * 2 + (window_h - (panel_margin * 3) - resign_button_h - 60), resign_button_w, resign_button_h)
					if resign_rect.collidepoint((x, y)) and not is_game_over_ui():
						game_over_reason = "Game Over - Resignation"
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

		if controller.board.is_game_over() and game_over_reason is None:
			game_over_reason = game_over_text()

		screen.fill(values.BG_COLOR)
		board.draw(screen, top_left=top_left)

		# move log panel
		panel_rect = pygame.Rect(
			window_w - panel_w - panel_margin,
			panel_margin,
			panel_w,
			window_h - (panel_margin * 3) - resign_button_h - 60,
		)
		pygame.draw.rect(screen, values.PANEL_BG_COLOR, panel_rect)
		pygame.draw.rect(screen, values.PANEL_BORDER_COLOR, panel_rect, 2)
		title_font = chessboard._get_font(22)
		item_font = chessboard._get_font(16)
		title_text = title_font.render("History", True, values.PANEL_TITLE_COLOR)
		screen.blit(title_text, (panel_rect.x + 10, panel_rect.y + 10))
		line_y = panel_rect.y + 40
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
			reason = game_over_reason if game_over_reason else "Game Over"
			text = font.render(reason, True, (255, 255, 255))
			screen.blit(text, (popup_rect.centerx - text.get_width() // 2, popup_rect.y + 30))
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
		pygame.display.flip()
		clock.tick(60)

	pygame.quit()
	sys.exit()


if __name__ == '__main__':
	main()

