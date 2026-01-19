import chess

MATE_SCORE = 100000

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Stronger, knight-only development penalty
KNIGHT_DEVELOPMENT_PENALTY = 40

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
    # White knights on starting squares are bad for White
    for sq in board.pieces(chess.KNIGHT, chess.WHITE):
        if sq == chess.B1 or sq == chess.G1:
            score -= KNIGHT_DEVELOPMENT_PENALTY

    # Black knights on starting squares are bad for Black
    for sq in board.pieces(chess.KNIGHT, chess.BLACK):
        if sq == chess.B8 or sq == chess.G8:
            score += KNIGHT_DEVELOPMENT_PENALTY

    return score

