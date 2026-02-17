EXACT, LOWER, UPPER = range(3)

# ─────────────────────────────────────────────────────────
# SIZE-BOUNDED TRANSPOSITION TABLE
# ─────────────────────────────────────────────────────────
MAX_SIZE = 1 << 20  # 1,048,576 entries

_table = {}


def _key(board):
    """Get a hashable key for the current board position."""
    if hasattr(board, "transposition_key"):
        return board.transposition_key()
    if hasattr(board, "_transposition_key"):
        return board._transposition_key()
    # Faster fallback: board_fen + turn (skips move counters)
    return (board.board_fen(), board.turn)


def lookup(board, depth, alpha, beta, stats=None):
    """Probe the TT. Returns (score, move) or None."""
    if stats is not None:
        stats.tt_probes += 1

    entry = _table.get(_key(board))
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
    """Return the best move stored for this position, or None."""
    entry = _table.get(_key(board))
    return entry[3] if entry else None


def store(board, depth, score, move, alpha, beta):
    """Store a position in the TT with depth-preferred replacement."""
    key = _key(board)

    flag = EXACT
    if score <= alpha:
        flag = UPPER
    elif score >= beta:
        flag = LOWER

    # Depth-preferred replacement: only replace if new depth >= existing
    existing = _table.get(key)
    if existing and existing[0] > depth:
        return  # keep the deeper entry

    _table[key] = (depth, score, flag, move)

    # Evict oldest entries if we exceed the size limit
    if len(_table) > MAX_SIZE:
        # Remove ~25% of entries (the first ones inserted)
        keys_to_remove = list(_table.keys())[: MAX_SIZE // 4]
        for k in keys_to_remove:
            del _table[k]


def clear():
    """Clear the transposition table (call between games)."""
    _table.clear()
