EXACT, LOWER, UPPER = range(3)

transposition_table = {}


def _key(board):
    # Prefer zobrist keys when available, otherwise fall back to full FEN for stability
    if hasattr(board, "transposition_key"):
        return board.transposition_key()
    if hasattr(board, "_transposition_key"):
        return board._transposition_key()
    return board.fen()


def lookup(board, depth, alpha, beta):
    entry = transposition_table.get(_key(board))
    if not entry:
        return None

    entry_depth, score, flag, move = entry

    # Only use entries that are at least as deep as the current search
    if entry_depth < depth:
        return None

    if flag == EXACT:
        return score, move
    if flag == LOWER and score >= beta:
        return score, move
    if flag == UPPER and score <= alpha:
        return score, move

    return None


def probe_move(board):
    entry = transposition_table.get(_key(board))
    return entry[3] if entry else None


def store(board, depth, score, move, alpha, beta):
    flag = EXACT
    if score <= alpha:
        flag = UPPER
    elif score >= beta:
        flag = LOWER

    transposition_table[_key(board)] = (depth, score, flag, move)
