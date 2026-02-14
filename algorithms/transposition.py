EXACT, LOWER, UPPER = range(3)

transposition_table = {}


def _key(board):
    if hasattr(board, "transposition_key"):
        return board.transposition_key()
    if hasattr(board, "_transposition_key"):
        return board._transposition_key()
    return board.fen()


def lookup(board, depth, alpha, beta, stats=None):
    if stats is not None:
        stats.tt_probes += 1

    entry = transposition_table.get(_key(board))
    if not entry:
        return None

    entry_depth, score, flag, move = entry

    if entry_depth < depth:
        return None

    if flag == EXACT:
        if stats is not None:
            stats.tt_hits += 1
        return score, move

    if flag == LOWER and score >= beta:
        if stats is not None:
            stats.tt_hits += 1
        return score, move

    if flag == UPPER and score <= alpha:
        if stats is not None:
            stats.tt_hits += 1
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
