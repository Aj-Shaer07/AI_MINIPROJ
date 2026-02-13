import chess

MATE_SCORE = 100000

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

KNIGHT_DEVELOPMENT_PENALTY = 40
CHECK_BONUS = 10
MOBILITY_WEIGHT = 2
HANGING_PENALTY_RATIO = 0.5
CENTER_BONUS = 5
EARLY_QUEEN_PENALTY = 40
KING_CENTER_PENALTY = 50
CASTLING_BONUS = 40
EARLY_KING_MOVE_PENALTY = 80


def _hanging_score(board, color):
    # Penalize pieces that are attacked but not defended
    penalty = 0
    enemy = not color
    for piece_type, value in PIECE_VALUES.items():
        for sq in board.pieces(piece_type, color):
            attacked = board.is_attacked_by(enemy, sq)
            defended = board.is_attacked_by(color, sq)
            if attacked and not defended:
                penalty += int(value * HANGING_PENALTY_RATIO)
    return penalty


def _center_control(board, color):
    center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]
    bonus = 0
    for sq in center_squares:
        if board.piece_at(sq) and board.piece_at(sq).color == color:
            bonus += CENTER_BONUS
    return bonus


def evaluate(board, ply=0):
    if board.is_checkmate():
        return -MATE_SCORE + ply

    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # Material evaluation
    for piece_type, value in PIECE_VALUES.items():
        score += len(board.pieces(piece_type, chess.WHITE)) * value
        score -= len(board.pieces(piece_type, chess.BLACK)) * value

    # Knight development penalty ONLY
    for sq in board.pieces(chess.KNIGHT, chess.WHITE):
        if sq in (chess.B1, chess.G1):
            score -= KNIGHT_DEVELOPMENT_PENALTY
    for sq in board.pieces(chess.KNIGHT, chess.BLACK):
        if sq in (chess.B8, chess.G8):
            score += KNIGHT_DEVELOPMENT_PENALTY

    # Early queen sorties are discouraged if the queen is still on board
    if board.fullmove_number < 12:
        white_queen_sq = board.king(chess.WHITE)  # reuse variable slot
        white_queen_sq = board.pieces(chess.QUEEN, chess.WHITE)
        if white_queen_sq:
            if list(white_queen_sq)[0] != chess.D1:
                score -= EARLY_QUEEN_PENALTY
        black_queen_sq = board.pieces(chess.QUEEN, chess.BLACK)
        if black_queen_sq:
            if list(black_queen_sq)[0] != chess.D8:
                score += EARLY_QUEEN_PENALTY

    # Mobility (encourage active pieces). Count moves for both sides using copies to avoid illegal null moves.
    white_board = board.copy()
    white_board.turn = chess.WHITE
    black_board = board.copy()
    black_board.turn = chess.BLACK

    white_moves = white_board.legal_moves.count()
    black_moves = black_board.legal_moves.count()
    score += MOBILITY_WEIGHT * (white_moves - black_moves)

    # Hanging pieces
    score -= _hanging_score(board, chess.WHITE)
    score += _hanging_score(board, chess.BLACK)

    # Center control
    score += _center_control(board, chess.WHITE)
    score -= _center_control(board, chess.BLACK)

    white_king_sq = board.king(chess.WHITE)
    black_king_sq = board.king(chess.BLACK)

    # King safety: keeping king in the center without castling rights is bad
    if white_king_sq in (chess.E1, chess.D1) and not board.has_kingside_castling_rights(chess.WHITE) and not board.has_queenside_castling_rights(chess.WHITE):
        score -= KING_CENTER_PENALTY
    if black_king_sq in (chess.E8, chess.D8) and not board.has_kingside_castling_rights(chess.BLACK) and not board.has_queenside_castling_rights(chess.BLACK):
        score += KING_CENTER_PENALTY

    # Castling bonuses and early king wandering penalties
    if white_king_sq in (chess.G1, chess.C1):
        score += CASTLING_BONUS
    elif board.fullmove_number < 15 and white_king_sq not in (chess.E1, chess.C1, chess.G1):
        score -= EARLY_KING_MOVE_PENALTY

    if black_king_sq in (chess.G8, chess.C8):
        score -= CASTLING_BONUS
    elif board.fullmove_number < 15 and black_king_sq not in (chess.E8, chess.C8, chess.G8):
        score += EARLY_KING_MOVE_PENALTY

    # Check pressure (side to move is in check is bad)
    if board.is_check():
        score += CHECK_BONUS if board.turn == chess.BLACK else -CHECK_BONUS

    return score

