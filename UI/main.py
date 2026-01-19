
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

	# demo options (so you can change demo piece at runtime)
	p.add_argument('--demo-piece', default=values.DEMO_PIECE_NAME, help='Demo piece name (e.g. king, queen)')
	p.add_argument('--demo-color', default=values.DEMO_PIECE_COLOR, choices=['white', 'black'], help='Demo piece color')

	return p.parse_args()


def main():
	args = parse_args()
	pygame.init()

	board = chessboard.create_chessboard(rows=args.rows, cols=args.cols, square_size=args.square_size, margin=args.margin)

	# game controller (engine plays black by default)
	controller = GameController(max_depth=getattr(args, 'engine_depth', 4), engine_is_black=True)
	# initialize UI from controller's starting position
	controller.sync_to_ui(board)

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

	# compute top-left to center the board inside the window
	top_left_x = max(0, (window_w - board.width) // 2)
	top_left_y = max(0, (window_h - board.height) // 2)
	top_left = (top_left_x, top_left_y)

	running = True
	while running:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
							# engine move (if any)
							if not controller.board.is_game_over() and controller.board.turn == (not controller.engine_is_black):
								eng_move = controller.engine_move()
								if eng_move:
									print(f"[ENGINE] plays: {eng_move}")
									controller.print_terminal()
									controller.sync_to_ui(board)
						else:
							# invalid move; restore piece
							board.set_piece(drag_from[0], drag_from[1], drag_piece)
					else:
						board.set_piece(drag_from[0], drag_from[1], drag_piece)
					dragging = False
					drag_piece = None
					drag_from = None
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
					# recompute top-left so board recenters
					top_left_x = max(0, (window_w - board.width) // 2)
					top_left_y = max(0, (window_h - board.height) // 2)
					top_left = (top_left_x, top_left_y)

		screen.fill(values.BG_COLOR)
		board.draw(screen, top_left=top_left)
		# draw dragged piece at mouse if any
		if dragging and drag_piece and mouse_pos:
			piece_font = chessboard._get_font(max(12, int(board.square_size * 0.8)))
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

