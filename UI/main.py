
import argparse
import pygame
import sys
import values
import pieces
import importlib
import chessboard


def parse_args():
	p = argparse.ArgumentParser(description='Chessboard UI')
	p.add_argument('--window-width', type=int, default=values.WINDOW_WIDTH, help='Window width in pixels')
	p.add_argument('--window-height', type=int, default=values.WINDOW_HEIGHT, help='Window height in pixels')
	p.add_argument('--rows', type=int, default=values.ROWS, help='Board rows')
	p.add_argument('--cols', type=int, default=values.COLS, help='Board cols')
	p.add_argument('--square-size', type=int, default=values.SQUARE_SIZE, help='Square size in pixels')
	p.add_argument('--margin', type=int, default=values.MARGIN, help='Board margin in pixels (around squares, for labels)')

	# demo options (so you can change demo piece at runtime)
	p.add_argument('--demo-piece', default=values.DEMO_PIECE_NAME, help='Demo piece name (e.g. king, queen)')
	p.add_argument('--demo-color', default=values.DEMO_PIECE_COLOR, choices=['white', 'black'], help='Demo piece color')

	return p.parse_args()


def main():
	args = parse_args()
	pygame.init()

	board = chessboard.create_chessboard(rows=args.rows, cols=args.cols, square_size=args.square_size, margin=args.margin)

	# demo: place the test piece (resolved via pieces.py using placeholders from values)
	demo_name = args.demo_piece
	demo_color = args.demo_color
	demo_symbol = pieces.get(demo_name, demo_color)
	demo_row, demo_col = values.DEMO_PIECE_POS
	# store symbol together with color key so rendering uses the per-piece color
	board.set_piece(demo_row, demo_col, (demo_symbol, demo_color))

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
					# toggle highlight
					if board.highlight == (r, c):
						board.highlight = None
					else:
						board.highlight = (r, c)
					# demo: toggle a king of the configured demo color on click
					if board.board[r][c] is None:
						demo_color = values.DEMO_PIECE_COLOR
						symbol = pieces.get('king', demo_color)
						# store (symbol, color_key) so rendering uses the correct color
						board.set_piece(r, c, (symbol, demo_color))
					else:
						board.set_piece(r, c, None)
			elif event.type == pygame.KEYDOWN:
				# Press R to reload modules and refresh the UI without restarting
				if event.key == pygame.K_r:
					importlib.reload(values)
					importlib.reload(pieces)
					importlib.reload(chessboard)
					# recreate board (use same CLI args for rows/cols/sizes)
					board = chessboard.create_chessboard(rows=args.rows, cols=args.cols, square_size=args.square_size, margin=args.margin)
					# pick up possibly-updated demo settings from reloaded values
					demo_name = getattr(values, 'DEMO_PIECE_NAME', demo_name)
					demo_color = getattr(values, 'DEMO_PIECE_COLOR', demo_color)
					demo_symbol = pieces.get(demo_name, demo_color)
					demo_row, demo_col = getattr(values, 'DEMO_PIECE_POS', (demo_row, demo_col))
					board.set_piece(demo_row, demo_col, (demo_symbol, demo_color))
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
		pygame.display.flip()
		clock.tick(60)

	pygame.quit()
	sys.exit()


if __name__ == '__main__':
	main()

