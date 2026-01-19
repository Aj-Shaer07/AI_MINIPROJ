transposition_table = {}

def lookup(board, depth):
    key = (board.fen(), depth)
    return transposition_table.get(key)

def store(board, depth, value, best_move):
    key = (board.fen(), depth)
    transposition_table[key] = (value, best_move)
