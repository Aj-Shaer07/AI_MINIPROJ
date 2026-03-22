import chess

MATE_SCORE = 100000

# ─────────────────────────────────────────────────────────
# MATERIAL VALUES  (midgame / endgame)
# ─────────────────────────────────────────────────────────
MG_VALUE = {
    chess.PAWN: 82, chess.KNIGHT: 337, chess.BISHOP: 365,
    chess.ROOK: 477, chess.QUEEN: 1025, chess.KING: 0,
}
EG_VALUE = {
    chess.PAWN: 94, chess.KNIGHT: 281, chess.BISHOP: 297,
    chess.ROOK: 512, chess.QUEEN: 936, chess.KING: 0,
}

# Kept for backward compatibility (used by move_ordering etc.)
PIECE_VALUES = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
}

# Phase weights for tapering (total = 24 at game start)
PHASE_WEIGHT = {
    chess.PAWN: 0, chess.KNIGHT: 1, chess.BISHOP: 1,
    chess.ROOK: 2, chess.QUEEN: 4, chess.KING: 0,
}
TOTAL_PHASE = 24  # 4*1 + 4*1 + 4*2 + 2*4

# ─────────────────────────────────────────────────────────
# PeSTO PIECE-SQUARE TABLES  (from White's perspective, a1=index 0)
# Indexed [square] where square is chess.A1..chess.H8
# Source: https://www.chessprogramming.org/PeSTO%27s_Evaluation_Function
# ─────────────────────────────────────────────────────────

# Helper: PeSTO tables are written rank-8-first (visual order).
# We reverse them so index 0 = a1, matching python-chess squares.
def _flip(table):
    """Flip a 64-element table from rank-8-first to rank-1-first."""
    result = []
    for rank in range(7, -1, -1):
        result.extend(table[rank * 8 : rank * 8 + 8])
    return result


# ── PAWNS ──
MG_PAWN_TABLE = _flip([
      0,   0,   0,   0,   0,   0,   0,   0,
     98, 134,  61,  95,  68, 126,  34, -11,
     -6,   7,  26,  31,  65,  56,  25, -20,
    -14,  13,   6,  21,  23,  12,  17, -23,
    -27,  -2,  -5,  12,  17,   6,  10, -25,
    -26,  -4,  -4, -10,   3,   3,  33, -12,
    -35,  -1, -20, -23, -15,  24,  38, -22,
      0,   0,   0,   0,   0,   0,   0,   0,
])
EG_PAWN_TABLE = _flip([
      0,   0,   0,   0,   0,   0,   0,   0,
    178, 173, 158, 134, 147, 132, 165, 187,
     94, 100,  85,  67,  56,  53,  82,  84,
     32,  24,  13,   5,  -2,   4,  17,  17,
     13,   9,  -3,  -7,  -7,  -8,   3,  -1,
      4,   7,  -6,   1,   0,  -5,  -1,  -8,
     13,   8,   8,  10,  13,   0,   2,  -7,
      0,   0,   0,   0,   0,   0,   0,   0,
])

# ── KNIGHTS ──
MG_KNIGHT_TABLE = _flip([
   -167, -89, -34, -49,  61, -97, -15,-107,
    -73, -41,  72,  36,  23,  62,   7, -17,
    -47,  60,  37,  65,  84, 129,  73,  44,
     -9,  17,  19,  53,  37,  69,  18,  22,
    -13,   4,  16,  13,  28,  19,  21,  -8,
    -23,  -9,  12,  10,  19,  17,  25, -16,
    -29, -53, -12,  -3,  -1,  18, -14, -19,
   -105, -21, -58, -33, -17, -28, -19, -23,
])
EG_KNIGHT_TABLE = _flip([
    -58, -38, -13, -28, -31, -27, -63, -99,
    -25,  -8, -25,  -2,  -9, -25, -24, -52,
    -24, -20,  10,   9,  -1,  -9, -19, -41,
    -17,   3,  22,  22,  22,  11,   8, -18,
    -18,  -6,  16,  25,  16,  17,   4, -18,
    -23,  -3,  -1,  15,  10,  -3, -20, -22,
    -42, -20, -10,  -5,  -2, -20, -23, -44,
    -29, -51, -23, -15, -22, -18, -50, -64,
])

# ── BISHOPS ──
MG_BISHOP_TABLE = _flip([
    -29,   4, -82, -37, -25, -42,   7,  -8,
    -26,  16, -18, -13,  30,  59,  18, -47,
    -16,  37,  43,  40,  35,  50,  37,  -2,
     -4,   5,  19,  50,  37,  37,   7,  -2,
     -6,  13,  13,  26,  34,  12,  10,   4,
      0,  15,  15,  15,  14,  27,  18,  10,
      4,  15,  16,   0,   7,  21,  33,   1,
    -33,  -3, -14, -21, -13, -12, -39, -21,
])
EG_BISHOP_TABLE = _flip([
    -14, -21, -11,  -8,  -7,  -9, -17, -24,
     -8,  -4,   7, -12,  -3, -13,  -4, -14,
      2,  -8,   0,  -1,  -2,   6,   0,   4,
     -3,   9,  12,   9,  14,  10,   3,   2,
     -6,   3,  13,  19,   7,  10,  -3,  -9,
    -12,  -3,   8,  10,  13,   3,  -7, -15,
    -14, -18,  -7,  -1,   4,  -9, -15, -27,
    -23,  -9, -23,  -5,  -9, -16,  -5, -17,
])

# ── ROOKS ──
MG_ROOK_TABLE = _flip([
     32,  42,  32,  51,  63,   9,  31,  43,
     27,  32,  58,  62,  80,  67,  26,  44,
     -5,  19,  26,  36,  17,  45,  61,  16,
    -24, -11,   7,  26,  24,  35,  -8, -20,
    -36, -26, -12,  -1,   9,  -7,   6, -23,
    -45, -25, -16, -17,   3,   0,  -5, -33,
    -44, -16, -20,  -9,  -1,  11,  -6, -71,
    -19, -13,   1,  17,  16,   7, -37, -26,
])
EG_ROOK_TABLE = _flip([
     13,  10,  18,  15,  12,  12,   8,   5,
     11,  13,  13,  11,  -3,   3,   8,   3,
      7,   7,   7,   5,   4,  -3,  -5,  -3,
      4,   3,  13,   1,   2,   1,  -1,   2,
      3,   5,   8,   4,  -5,  -6,  -8, -11,
     -4,   0,  -5,  -1,  -7, -12,  -8, -16,
     -6,  -6,   0,   2,  -9,  -9, -11,  -3,
     -9,   2,   3,  -1,  -5, -13,   4, -20,
])

# ── QUEENS ──
MG_QUEEN_TABLE = _flip([
    -28,   0,  29,  12,  59,  44,  43,  45,
    -24, -39,  -5,   1, -16,  57,  28,  54,
    -13, -17,   7,   8,  29,  56,  47,  57,
    -27, -27, -16, -16,  -1,  17,  -2,   1,
     -9, -26,  -9, -10,  -2,  -4,   3,  -3,
    -14,   2, -11,  -2,  -5,   2,  14,   5,
    -35,  -8,  11,   2,   8,  15,  -3,   1,
     -1, -18,  -9,  10, -15, -25, -31, -50,
])
EG_QUEEN_TABLE = _flip([
     -9,  22,  22,  27,  27,  19,  10,  20,
    -17,  20,  32,  41,  58,  25,  30,   0,
    -20,   6,   9,  49,  47,  35,  19,   9,
      3,  22,  24,  45,  57,  40,  57,  36,
    -18,  28,  19,  47,  31,  34,  39,  23,
    -16, -27,  15,   6,   9,  17,  10,   5,
    -22, -23, -30, -16, -16, -23, -36, -32,
    -33, -28, -22, -43,  -5, -32, -20, -41,
])

# ── KINGS ──
MG_KING_TABLE = _flip([
    -65,  23,  16, -15, -56, -34,   2,  13,
     29,  -1, -20,  -7,  -8,  -4, -38, -29,
     -9,  24,   2, -16, -20,   6,  22, -22,
    -17, -20, -12, -27, -30, -25, -14, -36,
    -49,  -1, -27, -39, -46, -44, -33, -51,
    -14, -14, -22, -46, -44, -30, -15, -27,
      1,   7,  -8, -64, -43, -16,   9,   8,
    -15,  36,  12, -54,   8, -28,  24,  14,
])
EG_KING_TABLE = _flip([
    -74, -35, -18, -18, -11,  15,   4, -17,
    -12,  17,  14,  17,  17,  38,  23,  11,
     10,  17,  23,  15,  20,  45,  44,  13,
     -8,  22,  24,  27,  26,  33,  26,   3,
    -18,  -4,  21,  24,  27,  23,   9, -11,
    -19,  -3,  11,  21,  23,  16,   7,  -9,
    -27, -11,   4,  13,  14,   4,  -5, -17,
    -53, -34, -21, -11, -28, -14, -24, -43,
])

# Collect into dictionaries for easy access
MG_PST = {
    chess.PAWN: MG_PAWN_TABLE, chess.KNIGHT: MG_KNIGHT_TABLE,
    chess.BISHOP: MG_BISHOP_TABLE, chess.ROOK: MG_ROOK_TABLE,
    chess.QUEEN: MG_QUEEN_TABLE, chess.KING: MG_KING_TABLE,
}
EG_PST = {
    chess.PAWN: EG_PAWN_TABLE, chess.KNIGHT: EG_KNIGHT_TABLE,
    chess.BISHOP: EG_BISHOP_TABLE, chess.ROOK: EG_ROOK_TABLE,
    chess.QUEEN: EG_QUEEN_TABLE, chess.KING: EG_KING_TABLE,
}

# Mirror square for Black: flip rank (a1↔a8)
def _mirror(sq):
    return sq ^ 56


# ─────────────────────────────────────────────────────────
# PAWN STRUCTURE BONUSES / PENALTIES
# ─────────────────────────────────────────────────────────
DOUBLED_PAWN_PENALTY = -15
ISOLATED_PAWN_PENALTY = -20
PASSED_PAWN_BONUS_MG = [0, 5, 10, 20, 40, 65, 100, 0]   # by rank (0-7)
PASSED_PAWN_BONUS_EG = [0, 15, 30, 50, 90, 150, 250, 0]  # much bigger in EG

BISHOP_PAIR_BONUS = 30

ROOK_OPEN_FILE_BONUS = 25
ROOK_SEMI_OPEN_FILE_BONUS = 12

ROOK_BEHIND_PASSER_BONUS = 40   # EG bonus for rook behind own passed pawn
CONNECTED_PASSER_BONUS = 30     # EG bonus for two passed pawns on adjacent files

# King pawn-shield bonus (for pawns directly in front of castled king)
KING_SHIELD_BONUS = 10

# Hanging piece penalty
HANGING_PENALTY_RATIO = 0.5


# ─────────────────────────────────────────────────────────
# MAIN EVALUATION
# ─────────────────────────────────────────────────────────
def evaluate(board, ply=0):
    """Evaluate the position. Positive = White advantage."""
    if board.is_checkmate():
        # Side to move is checkmated
        if board.turn == chess.WHITE:
            return -MATE_SCORE + ply
        else:
            return MATE_SCORE - ply

    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    mg_score = 0
    eg_score = 0
    phase = 0

    # ── Material + PST ──
    for piece_type in chess.PIECE_TYPES:
        mg_table = MG_PST[piece_type]
        eg_table = EG_PST[piece_type]
        mg_val = MG_VALUE[piece_type]
        eg_val = EG_VALUE[piece_type]

        for sq in board.pieces(piece_type, chess.WHITE):
            mg_score += mg_val + mg_table[sq]
            eg_score += eg_val + eg_table[sq]
            phase += PHASE_WEIGHT[piece_type]

        for sq in board.pieces(piece_type, chess.BLACK):
            mg_score -= mg_val + mg_table[_mirror(sq)]
            eg_score -= eg_val + eg_table[_mirror(sq)]
            phase += PHASE_WEIGHT[piece_type]

    # ── Pawn Structure ──
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        pawns = board.pieces(chess.PAWN, color)
        pawn_files = set()

        for sq in pawns:
            f = chess.square_file(sq)
            r = chess.square_rank(sq)

            # Doubled pawns: penalize if another pawn of same color is on same file
            same_file_pawns = [s for s in pawns if chess.square_file(s) == f and s != sq]
            if same_file_pawns:
                eg_score += sign * DOUBLED_PAWN_PENALTY

            # Isolated pawns: no friendly pawns on adjacent files
            adj_files = []
            if f > 0:
                adj_files.append(f - 1)
            if f < 7:
                adj_files.append(f + 1)
            has_neighbor = any(chess.square_file(s) in adj_files for s in pawns if s != sq)
            if not has_neighbor:
                mg_score += sign * ISOLATED_PAWN_PENALTY
                eg_score += sign * ISOLATED_PAWN_PENALTY

            # Passed pawns: no enemy pawns on same or adjacent files ahead
            enemy_pawns = board.pieces(chess.PAWN, not color)
            is_passed = True
            check_files = [f] + adj_files
            for ep_sq in enemy_pawns:
                ep_f = chess.square_file(ep_sq)
                ep_r = chess.square_rank(ep_sq)
                if ep_f in check_files:
                    if color == chess.WHITE and ep_r > r:
                        is_passed = False
                        break
                    elif color == chess.BLACK and ep_r < r:
                        is_passed = False
                        break
            if is_passed:
                # Rank from the pawn's side perspective
                effective_rank = r if color == chess.WHITE else (7 - r)
                mg_score += sign * PASSED_PAWN_BONUS_MG[effective_rank]
                eg_score += sign * PASSED_PAWN_BONUS_EG[effective_rank]

                # Rook behind passed pawn bonus
                rook_behind = False
                for rsq in board.pieces(chess.ROOK, color):
                    if chess.square_file(rsq) == f:
                        rr = chess.square_rank(rsq)
                        if (color == chess.WHITE and rr < r) or \
                           (color == chess.BLACK and rr > r):
                            rook_behind = True
                            break
                if rook_behind:
                    eg_score += sign * ROOK_BEHIND_PASSER_BONUS

                # Connected passed pawns: check if there's another passed pawn
                # on an adjacent file (only count once per pair)
                for adj_f in adj_files:
                    for other_sq in pawns:
                        if other_sq != sq and chess.square_file(other_sq) == adj_f:
                            # Check if other pawn is also passed
                            other_r = chess.square_rank(other_sq)
                            other_passed = True
                            other_check = [adj_f]
                            if adj_f > 0:
                                other_check.append(adj_f - 1)
                            if adj_f < 7:
                                other_check.append(adj_f + 1)
                            for ep2 in enemy_pawns:
                                ep2_f = chess.square_file(ep2)
                                ep2_r = chess.square_rank(ep2)
                                if ep2_f in other_check:
                                    if color == chess.WHITE and ep2_r > other_r:
                                        other_passed = False
                                        break
                                    elif color == chess.BLACK and ep2_r < other_r:
                                        other_passed = False
                                        break
                            if other_passed and other_sq > sq:  # avoid double-counting
                                eg_score += sign * CONNECTED_PASSER_BONUS

                # King proximity to passed pawn (endgame)
                # Reward own king being close, penalize opponent king being far
                if effective_rank >= 3:  # only for advanced passers
                    own_king = board.king(color)
                    opp_king = board.king(not color)
                    own_dist = _chebyshev_distance(own_king, sq)
                    opp_dist = _chebyshev_distance(opp_king, sq)
                    # Bonus: opponent far from passer, our king close
                    eg_score += sign * (opp_dist * 5 - own_dist * 3)

            pawn_files.add(f)

    # ── Bishop Pair ──
    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        mg_score += BISHOP_PAIR_BONUS
        eg_score += BISHOP_PAIR_BONUS
    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        mg_score -= BISHOP_PAIR_BONUS
        eg_score -= BISHOP_PAIR_BONUS

    # ── Rook on Open/Semi-Open Files ──
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        for sq in board.pieces(chess.ROOK, color):
            f = chess.square_file(sq)
            own_pawns_on_file = any(
                chess.square_file(s) == f for s in board.pieces(chess.PAWN, color)
            )
            enemy_pawns_on_file = any(
                chess.square_file(s) == f for s in board.pieces(chess.PAWN, not color)
            )
            if not own_pawns_on_file and not enemy_pawns_on_file:
                mg_score += sign * ROOK_OPEN_FILE_BONUS
                eg_score += sign * ROOK_OPEN_FILE_BONUS
            elif not own_pawns_on_file:
                mg_score += sign * ROOK_SEMI_OPEN_FILE_BONUS
                eg_score += sign * ROOK_SEMI_OPEN_FILE_BONUS

    # ── King Pawn Shield ──
    if phase > 6:  # only in middlegame-ish positions
        for color in (chess.WHITE, chess.BLACK):
            sign = 1 if color == chess.WHITE else -1
            king_sq = board.king(color)
            king_file = chess.square_file(king_sq)
            king_rank = chess.square_rank(king_sq)

            # Check for pawns in front of king (shield squares)
            shield_files = [
                max(0, king_file - 1), king_file, min(7, king_file + 1)
            ]
            if color == chess.WHITE:
                shield_ranks = [king_rank + 1, king_rank + 2]
            else:
                shield_ranks = [king_rank - 1, king_rank - 2]

            for sf in shield_files:
                for sr in shield_ranks:
                    if 0 <= sr <= 7:
                        shield_sq = chess.square(sf, sr)
                        piece = board.piece_at(shield_sq)
                        if piece and piece.piece_type == chess.PAWN and piece.color == color:
                            mg_score += sign * KING_SHIELD_BONUS

    # ── Hanging Pieces ──
    # Penalize pieces that are attacked but not defended
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        enemy = not color
        for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            val = PIECE_VALUES[piece_type]
            for sq in board.pieces(piece_type, color):
                if board.is_attacked_by(enemy, sq) and not board.is_attacked_by(color, sq):
                    penalty = int(val * HANGING_PENALTY_RATIO)
                    mg_score -= sign * penalty
                    eg_score -= sign * penalty

    # ── Game-Phase Tapering ──
    # phase is how many minor/major pieces are left (0=endgame, 24=opening)
    phase = min(phase, TOTAL_PHASE)
    mg_weight = phase
    eg_weight = TOTAL_PHASE - phase
    score = (mg_score * mg_weight + eg_score * eg_weight) // TOTAL_PHASE

    # ── Endgame-Specific Evaluation ──
    # These bonuses are added AFTER tapering so they apply at full
    # strength regardless of game phase.

    # Compute raw material advantage (positive = White ahead)
    w_mat = _count_material(board, chess.WHITE)
    b_mat = _count_material(board, chess.BLACK)
    mat_advantage = w_mat - b_mat

    # Mop-up evaluation: when one side has a decisive material advantage,
    # encourage driving the enemy king to the edge and bringing your king
    # closer. This is critical for K+Q vs K, K+R vs K, K+B+B vs K.
    if abs(mat_advantage) >= 200:  # at least two pawns up
        winning_color = chess.WHITE if mat_advantage > 0 else chess.BLACK
        losing_color = not winning_color
        sign = 1 if winning_color == chess.WHITE else -1

        losing_king = board.king(losing_color)
        winning_king = board.king(winning_color)

        # Reward pushing the losing king to the edge
        edge_bonus = _king_edge_distance(losing_king) * 15

        # Reward keeping the winning king close to the losing king
        king_dist = _chebyshev_distance(winning_king, losing_king)
        proximity_bonus = (14 - king_dist) * 8

        # Stronger bonus when advantage is overwhelming (Q or R+N/B)
        advantage_scale = min(abs(mat_advantage) // 100, 10)
        mop_up = (edge_bonus + proximity_bonus) * advantage_scale // 5

        score += sign * mop_up

        # K+B+B vs K: drive king to the correct corner
        if _is_kbb_vs_k(board, winning_color):
            corner_bonus = _kbb_corner_bonus(board, losing_king, winning_color)
            score += sign * corner_bonus

        # K+B+N vs K: drive king to the corner matching bishop's square color
        if _is_kbn_vs_k(board, winning_color):
            corner_bonus = _kbn_corner_bonus(board, losing_king, winning_color)
            score += sign * corner_bonus

    # Stalemate avoidance: when we have a big advantage, penalize positions
    # where the losing side has very few legal moves (risk of stalemate)
    if abs(mat_advantage) >= 200:
        losing_color = chess.BLACK if mat_advantage > 0 else chess.WHITE
        if board.turn == losing_color:
            num_moves = len(list(board.legal_moves))
            if num_moves <= 2:
                # Dangerous: close to stalemate, penalize the winning side
                sign = 1 if mat_advantage > 0 else -1
                score -= sign * (60 - num_moves * 25)

    # 50-move rule awareness: as we approach 50 moves without progress,
    # reduce the winning side's score to encourage decisive play.
    # EXCEPTION: KBN and KBB endgames can take 30+ moves to mate;
    # decaying the score kills the evaluation gradient prematurely.
    halfmove_clock = board.halfmove_clock
    is_kbn_or_kbb = False
    if abs(mat_advantage) >= 200:
        wc = chess.WHITE if mat_advantage > 0 else chess.BLACK
        is_kbn_or_kbb = _is_kbn_vs_k(board, wc) or _is_kbb_vs_k(board, wc)
    if halfmove_clock > 30 and abs(score) > 100 and not is_kbn_or_kbb:
        # Reduce score proportionally as we approach the 50-move limit
        decay_factor = max(0, 100 - halfmove_clock) / 70
        abs_score = abs(score)
        score = int(abs_score * decay_factor) * (1 if score > 0 else -1)

    return score


# ─────────────────────────────────────────────────────────
# ENDGAME HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────
def _count_material(board, color):
    """Count non-king material for a side."""
    total = 0
    for pt, val in PIECE_VALUES.items():
        if pt != chess.KING:
            total += len(board.pieces(pt, color)) * val
    return total


def _king_edge_distance(sq):
    """How far the king is from the center (higher = closer to edge).
    Returns 0 (center) to 6 (corner). Used to reward pushing enemy king
    to the edge in mop-up endgames."""
    file = chess.square_file(sq)
    rank = chess.square_rank(sq)
    # Distance from center (3.5, 3.5)
    file_dist = max(3 - file, file - 4)
    rank_dist = max(3 - rank, rank - 4)
    return file_dist + rank_dist


def _chebyshev_distance(sq1, sq2):
    """Chebyshev (king) distance between two squares."""
    f1, r1 = chess.square_file(sq1), chess.square_rank(sq1)
    f2, r2 = chess.square_file(sq2), chess.square_rank(sq2)
    return max(abs(f1 - f2), abs(r1 - r2))


def _is_kbb_vs_k(board, winning_color):
    """Check if it's K+B+B vs K (exactly two bishops, no other pieces)."""
    losing_color = not winning_color
    # Losing side: only king
    for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        if board.pieces(pt, losing_color):
            return False
    # Winning side: exactly two bishops, no other pieces
    if len(board.pieces(chess.BISHOP, winning_color)) != 2:
        return False
    for pt in (chess.PAWN, chess.KNIGHT, chess.ROOK, chess.QUEEN):
        if board.pieces(pt, winning_color):
            return False
    return True


def _kbb_corner_bonus(board, losing_king_sq, winning_color):
    """In K+B+B vs K, drive the losing king to any corner.
    Two opposite-colored bishops can mate in any corner.
    Provides a strong gradient: push to edge -> push to corner -> bring king close."""
    bishops = list(board.pieces(chess.BISHOP, winning_color))
    if len(bishops) != 2:
        return 0

    # Ensure bishops are on opposite colors (can't mate otherwise)
    b1_color = (chess.square_file(bishops[0]) + chess.square_rank(bishops[0])) % 2
    b2_color = (chess.square_file(bishops[1]) + chess.square_rank(bishops[1])) % 2
    if b1_color == b2_color:
        return 0 

    losing_file = chess.square_file(losing_king_sq)
    losing_rank = chess.square_rank(losing_king_sq)

    # 1. Edge Push: Force the losing king to the edge of the board
    edge_dist = _king_edge_distance(losing_king_sq)
    edge_bonus = edge_dist * 50

    # 2. Corner Push: Once on the edge, force towards any corner
    corners = [(0, 0), (0, 7), (7, 0), (7, 7)]
    min_corner_dist = min(
        max(abs(losing_file - cf), abs(losing_rank - cr)) # Chebyshev
        for cf, cr in corners
    )
    corner_bonus = (7 - min_corner_dist) * 60

    # 3. King Proximity: Our king must stay close to cut off escape squares
    winning_king_sq = board.king(winning_color)
    king_dist = _chebyshev_distance(winning_king_sq, losing_king_sq)
    proximity_bonus = (14 - king_dist) * 30

    return edge_bonus + corner_bonus + proximity_bonus


def _is_kbn_vs_k(board, winning_color):
    """Check if it's K+B+N vs K (exactly one bishop + one knight, no other pieces)."""
    losing_color = not winning_color
    # Losing side: only king
    for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        if board.pieces(pt, losing_color):
            return False
    # Winning side: exactly one bishop + one knight, nothing else
    if len(board.pieces(chess.BISHOP, winning_color)) != 1:
        return False
    if len(board.pieces(chess.KNIGHT, winning_color)) != 1:
        return False
    for pt in (chess.PAWN, chess.ROOK, chess.QUEEN):
        if board.pieces(pt, winning_color):
            return False
    return True


def _kbn_corner_bonus(board, losing_king_sq, winning_color):
    """In K+B+N vs K, drive the losing king to the corner whose color
    matches the bishop's square color.
    Dark-square bishop -> target a1 (dark) or h8 (dark).
    Light-square bishop -> target a8 (light) or h1 (light).

    This is one of the hardest basic endgames. The heuristic must provide
    a smooth gradient that:
      - Pushes the losing king to the edge
      - REPELS the losing king from the WRONG corners
      - ATTRACTS the losing king to the CORRECT corners
      - Keeps the winning king close
      - Rewards restricting the losing king's mobility
      - Rewards the knight being positioned to control the correct corner
    """
    bishops = list(board.pieces(chess.BISHOP, winning_color))
    if len(bishops) != 1:
        return 0

    knights = list(board.pieces(chess.KNIGHT, winning_color))
    if len(knights) != 1:
        return 0

    # Bishop square color: 0 = dark, 1 = light
    bsq = bishops[0]
    knight_sq = knights[0]
    bishop_color = (chess.square_file(bsq) + chess.square_rank(bsq)) % 2

    # Target corners matching bishop's square color
    # a1=(0,0) dark, h8=(7,7) dark, a8=(0,7) light, h1=(7,0) light
    if bishop_color == 0:  # dark-square bishop
        target_corners = [(0, 0), (7, 7)]  # a1, h8
        wrong_corners  = [(0, 7), (7, 0)]  # a8, h1
    else:  # light-square bishop
        target_corners = [(0, 7), (7, 0)]  # a8, h1
        wrong_corners  = [(0, 0), (7, 7)]  # a1, h8

    losing_file = chess.square_file(losing_king_sq)
    losing_rank = chess.square_rank(losing_king_sq)

    # 1. Edge Push: Force the losing king to the edge of the board
    edge_dist = _king_edge_distance(losing_king_sq)
    edge_bonus = edge_dist * 80

    # 2. Correct Corner Push: Distance to nearest *correct* corner (Chebyshev)
    min_correct_dist = min(
        max(abs(losing_file - cf), abs(losing_rank - cr))
        for cf, cr in target_corners
    )
    # Very strong multiplier — this is the most important term.
    # The engine must prefer correct-corner proximity over everything else.
    corner_bonus = (7 - min_correct_dist) * 500

    # 3. Wrong Corner Repulsion: PENALIZE the losing king being near wrong corners.
    # This creates a gradient that pushes the king out of the wrong corner
    # (the classic KBN failure mode).
    min_wrong_dist = min(
        max(abs(losing_file - cf), abs(losing_rank - cr))
        for cf, cr in wrong_corners
    )
    # Bonus for being FAR from wrong corners
    wrong_corner_penalty = min_wrong_dist * 200

    # 4. King Proximity: Winning king must stay close to the losing king
    winning_king = board.king(winning_color)
    king_dist = _chebyshev_distance(winning_king, losing_king_sq)
    proximity_bonus = (14 - king_dist) * 60

    # 5. Knight Coordination: Reward the knight being near the correct corner
    # The knight needs to control squares in the mating net.
    knight_file = chess.square_file(knight_sq)
    knight_rank = chess.square_rank(knight_sq)
    min_knight_corner_dist = min(
        max(abs(knight_file - cf), abs(knight_rank - cr))
        for cf, cr in target_corners
    )
    # Also reward knight being close to the losing king (controls escape)
    knight_king_dist = _chebyshev_distance(knight_sq, losing_king_sq)
    knight_bonus = (7 - min_knight_corner_dist) * 30 + (7 - knight_king_dist) * 20

    # 6. King Trapping (Mobility): Restrict the losing king's safe squares
    safe_squares = 0
    for r_off in (-1, 0, 1):
        for f_off in (-1, 0, 1):
            if r_off == 0 and f_off == 0:
                continue
            tr = losing_rank + r_off
            tf = losing_file + f_off
            if 0 <= tr <= 7 and 0 <= tf <= 7:
                tsq = chess.square(tf, tr)
                if not board.is_attacked_by(winning_color, tsq):
                    safe_squares += 1

    # Reward fewer safe squares (max 8, so 8 - safe = how trapped)
    trapping_bonus = (8 - safe_squares) * 60

    return (edge_bonus + corner_bonus + wrong_corner_penalty +
            proximity_bonus + knight_bonus + trapping_bonus)

