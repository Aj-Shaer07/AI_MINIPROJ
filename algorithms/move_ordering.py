"""
Move Ordering — Heuristic Move Prioritization
==============================================
Orders moves to maximize alpha-beta pruning efficiency.
With perfect ordering, alpha-beta reduces complexity from O(b^d) to O(b^(d/2)).

Priority tiers (highest first):
1. **TT best-move** (10,000):  Previously found best move for this position
2. **Queen promotions** (9,000): Almost always the best move
3. **MVV-LVA captures** (1,000+): Most Valuable Victim − Least Valuable Attacker
4. **Killer moves** (800):     Quiet moves that caused beta cutoffs at same ply
5. **History heuristic** (0–700): Cumulative cutoff count per (color, from, to),
                                  incremented by depth² on each beta cutoff
"""
import chess

# ─────────────────────────────────────────────────────────
# PIECE VALUES FOR MVV-LVA ORDERING
# ─────────────────────────────────────────────────────────
_PIECE_VAL = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
}


def order_moves(board, moves, tt_move=None, killers=None, history=None):
    """
    Score and sort moves for alpha-beta search.

    Priority order:
      1. TT move              (10_000)
      2. Winning captures      MVV-LVA (1_000+)
      3. Promotions            (900)
      4. Killer moves          (800)
      5. Quiet moves           (history heuristic if available)
    """
    def score(move):
        # Hash move is always searched first
        if tt_move and move == tt_move:
            return 10_000

        s = 0

        # MVV-LVA for captures
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                # Score = 10 * victim_value - attacker_value  (captures high-value with low-value first)
                s += 10 * _PIECE_VAL.get(victim.piece_type, 0) - _PIECE_VAL.get(attacker.piece_type, 0)
            elif victim:
                s += 10 * _PIECE_VAL.get(victim.piece_type, 0)
            # En passant: victim square is empty but it's still a capture
            if not victim:
                s += 1000  # en passant capture

        # Promotions
        if move.promotion:
            if move.promotion == chess.QUEEN:
                s += 9000
            elif move.promotion == chess.KNIGHT:
                s += 3000  # knight underpromotions can be tactical
            else:
                s += 500

        # Killer moves (quiet but caused a beta cutoff at this depth before)
        if killers and not board.is_capture(move) and not move.promotion:
            if move in killers:
                s += 800

        # History heuristic for quiet moves
        if history and not board.is_capture(move) and not move.promotion:
            h_key = (board.turn, move.from_square, move.to_square)
            s += min(history.get(h_key, 0), 700)  # cap so it doesn't override killers

        return s

    return sorted(moves, key=score, reverse=True)
