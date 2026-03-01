import 'package:chess/chess.dart' as chess;

// ─────────────────────────────────────────────────────────
// PIECE VALUES FOR MVV-LVA ORDERING
// ─────────────────────────────────────────────────────────
final Map<chess.PieceType, int> _pieceVal = {
  chess.PieceType.PAWN: 100,
  chess.PieceType.KNIGHT: 320,
  chess.PieceType.BISHOP: 330,
  chess.PieceType.ROOK: 500,
  chess.PieceType.QUEEN: 900,
  chess.PieceType.KING: 20000,
};

/// Score a single move for ordering.
int _scoreMove(
  chess.Chess board,
  chess.Move move, {
  chess.Move? ttMove,
  List<chess.Move>? killers,
  Map<String, int>? history,
}) {
  // Hash move is always first
  if (ttMove != null &&
      move.fromAlgebraic == ttMove.fromAlgebraic &&
      move.toAlgebraic == ttMove.toAlgebraic &&
      move.promotion == ttMove.promotion) {
    return 10000;
  }

  int s = 0;

  // Detect capture: piece at target square before move
  final victim = board.get(move.toAlgebraic);
  final attacker = board.get(move.fromAlgebraic);

  final isCapture = victim != null;

  // MVV-LVA for captures
  if (isCapture && attacker != null) {
    s += 10 * (_pieceVal[victim.type] ?? 0) - (_pieceVal[attacker.type] ?? 0);
  } else if (isCapture) {
    s += 10 * (_pieceVal[victim.type] ?? 0);
  }

  // En passant (capture with no victim on target square encoded differently)
  // The chess package handles this, but we check the flag
  if (move.flags & chess.Chess.BITS_EP_CAPTURE != 0) {
    s += 1000;
  }

  // Promotions
  if (move.promotion != null) {
    if (move.promotion == chess.PieceType.QUEEN) {
      s += 9000;
    } else if (move.promotion == chess.PieceType.KNIGHT) {
      s += 3000;
    } else {
      s += 500;
    }
  }

  // Killer moves
  if (killers != null && !isCapture && move.promotion == null) {
    for (final k in killers) {
      if (k.fromAlgebraic == move.fromAlgebraic &&
          k.toAlgebraic == move.toAlgebraic) {
        s += 800;
        break;
      }
    }
  }

  // History heuristic
  if (history != null && !isCapture && move.promotion == null) {
    final hKey =
        '${board.turn == chess.Color.WHITE ? "w" : "b"}_${move.fromAlgebraic}_${move.toAlgebraic}';
    final hVal = history[hKey] ?? 0;
    s += hVal.clamp(0, 700);
  }

  return s;
}

/// Order moves for alpha-beta search (highest score first).
List<chess.Move> orderMoves(
  chess.Chess board,
  List<chess.Move> moves, {
  chess.Move? ttMove,
  List<chess.Move>? killers,
  Map<String, int>? history,
}) {
  final scored = moves
      .map(
        (m) => MapEntry(
          m,
          _scoreMove(
            board,
            m,
            ttMove: ttMove,
            killers: killers,
            history: history,
          ),
        ),
      )
      .toList();
  scored.sort((a, b) => b.value.compareTo(a.value));
  return scored.map((e) => e.key).toList();
}
