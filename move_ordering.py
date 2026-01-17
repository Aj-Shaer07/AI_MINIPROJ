import chess

def order_moves(board, moves):
    def score(move):
        s = 0

        # Captures first (MVV-LVA lite)
        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            if captured:
                s += 10 * captured.piece_type

        # Promotions
        if move.promotion:
            s += 900

        # Checks
        board.push(move)
        if board.is_check():
            s += 50
        board.pop()

        return s

    return sorted(moves, key=score, reverse=True)

