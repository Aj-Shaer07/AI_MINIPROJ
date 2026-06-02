"""
Transposition Table — Zobrist-Keyed Position Cache
==================================================
Caches evaluated positions to avoid redundant search of the same
position reached via different move orders (transpositions).

Implementation:
- **Hash key**:     python-chess transposition_key() (Zobrist-style 64-bit)
- **Max entries**:  2^20 = 1,048,576 positions
- **Entry format**: (depth, score, flag, best_move)
- **Flags**:        EXACT | LOWER_BOUND | UPPER_BOUND
- **Replacement**:  Depth-preferred (deeper entries survive)
- **Eviction**:     When full, removes ~25% oldest entries (FIFO)

Provides both a class-based API (TranspositionTable) for per-request
isolation and module-level convenience functions for shared usage.
"""
"""
Transposition Table — Zobrist-Keyed Position Cache
==================================================
Caches evaluated positions to avoid redundant search of the same
position reached via different move orders (transpositions).

Implementation:
- **Hash key**:     python-chess transposition_key() (Zobrist-style 64-bit)
- **Max entries**:  2^20 = 1,048,576 positions
- **Entry format**: (depth, score, flag, best_move)
- **Flags**:        EXACT | LOWER_BOUND | UPPER_BOUND
- **Replacement**:  Depth-preferred (deeper entries survive)
- **Eviction**:     When full, removes ~25% oldest entries (FIFO)

Provides both a class-based API (TranspositionTable) for per-request
isolation and module-level convenience functions for shared usage.
"""
EXACT, LOWER, UPPER = range(3)

# ─────────────────────────────────────────────────────────
# SIZE-BOUNDED TRANSPOSITION TABLE
# ─────────────────────────────────────────────────────────
MAX_SIZE = 1 << 20  # 1,048,576 entries


class TranspositionTable:
    def __init__(self, max_size=MAX_SIZE):
        self.max_size = max_size
        self._table = {}

    def lookup(self, board, depth, alpha, beta, stats=None):
        """Probe the TT. Returns (score, move) or None."""
        if stats is not None:
            stats.tt_probes += 1

        entry = self._table.get(_key(board))
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

    def probe_move(self, board):
        """Return the best move stored for this position, or None."""
        entry = self._table.get(_key(board))
        return entry[3] if entry else None

    def store(self, board, depth, score, move, alpha, beta):
        """Store a position in the TT with depth-preferred replacement."""
        key = _key(board)

        flag = EXACT
        if score <= alpha:
            flag = UPPER
        elif score >= beta:
            flag = LOWER

        # Depth-preferred replacement: only replace if new depth >= existing
        existing = self._table.get(key)
        if existing and existing[0] > depth:
            return  # keep the deeper entry

        self._table[key] = (depth, score, flag, move)

        # Evict oldest entries if we exceed the size limit
        if len(self._table) > self.max_size:
            # Remove ~25% of entries (the first ones inserted)
            keys_to_remove = list(self._table.keys())[: self.max_size // 4]
            for k in keys_to_remove:
                del self._table[k]

    def clear(self):
        self._table.clear()


_default_tt = TranspositionTable()


def _key(board):
    """Get a hashable key for the current board position."""
    if hasattr(board, "transposition_key"):
        return board.transposition_key()
    if hasattr(board, "_transposition_key"):
        return board._transposition_key()
    # Faster fallback: board_fen + turn (skips move counters)
    return (board.board_fen(), board.turn)


def lookup(board, depth, alpha, beta, stats=None):
    return _default_tt.lookup(board, depth, alpha, beta, stats=stats)


def probe_move(board):
    return _default_tt.probe_move(board)


def store(board, depth, score, move, alpha, beta):
    _default_tt.store(board, depth, score, move, alpha, beta)


def clear():
    """Clear the default process-level transposition table."""
    _default_tt.clear()
