import 'package:chess/chess.dart' as chess;

// ─────────────────────────────────────────────────────────
// TABLEBASE  (equivalent to algorithms/tablebase.py)
// ─────────────────────────────────────────────────────────
// Dart/Flutter cannot load Syzygy binary tablebase files via
// chess.syzygy (a C extension).  Instead we implement a lightweight
// heuristic tablebase that covers the most common ≤ 4-piece endings
// using pure Dart logic.  The interface mirrors the Python version:
//
//   isTablebaseLoaded()            → always true (built-in)
//   tablebaseMoveForRoot(board)    → best move or null
//
// For positions outside the hard-coded patterns the function returns
// null and the engine falls through to normal search.
// ─────────────────────────────────────────────────────────

/// Always true — the built-in heuristic tablebase is always available.
bool isTablebaseLoaded() => true;

/// Try to return a tablebase move for root positions with ≤ 4 pieces.
///
/// Returns a legal [chess.Move] when a clear winning continuation is
/// known from the built-in heuristic, or [null] to fall back to search.
chess.Move? tablebaseMoveForRoot(chess.Chess board) {
  // Mirror Python's guard: castling rights or en-passant → skip.
  // We read both from the FEN string because the chess package does not
  // expose them as top-level getters.
  final fen = board.fen;
  final fenParts = fen.split(' ');
  // fenParts[2] = castling rights (e.g. "KQkq" or "-")
  // fenParts[3] = en-passant square (e.g. "e3" or "-")
  if (fenParts.length >= 4) {
    if (fenParts[2] != '-') return null; // castling rights present
    if (fenParts[3] != '-') return null; // en-passant square set
  }

  // Count pieces on board (0x88 layout: valid squares have (i & 0x88) == 0)
  int pieceCount = 0;
  for (int i = 0; i < 128; i++) {
    if ((i & 0x88) == 0 && board.board[i] != null) pieceCount++;
  }
  if (pieceCount > 4) return null;

  // Determine material for each side
  final _Material wMat = _Material.fromBoard(board, chess.Color.WHITE);
  final _Material bMat = _Material.fromBoard(board, chess.Color.BLACK);

  final bool whiteToMove = board.turn == chess.Color.WHITE;

  // ── K+Q vs K ──────────────────────────────────────────
  // The side with the queen wins by driving the enemy king to the edge.
  if (_isKqVsK(wMat, bMat)) {
    return _mopUpMove(board, whiteToMove: whiteToMove, winnerHasQueen: true);
  }

  // ── K+R vs K ──────────────────────────────────────────
  if (_isKrVsK(wMat, bMat)) {
    return _mopUpMove(board, whiteToMove: whiteToMove, winnerHasQueen: false);
  }

  // ── K+B+B vs K ────────────────────────────────────────
  if (_isKbbVsK(wMat, bMat)) {
    return _mopUpMove(board, whiteToMove: whiteToMove, winnerHasQueen: false);
  }

  // ── K vs K (draw) ─────────────────────────────────────
  if (_isKvK(wMat, bMat)) {
    return _anyLegalMove(board); // just make a move, it's a draw
  }

  return null; // no heuristic available; fall through to search
}

// ─────────────────────────────────────────────────────────
// MATERIAL HELPER
// ─────────────────────────────────────────────────────────
class _Material {
  final int pawns, knights, bishops, rooks, queens;

  const _Material({
    required this.pawns,
    required this.knights,
    required this.bishops,
    required this.rooks,
    required this.queens,
  });

  factory _Material.fromBoard(chess.Chess board, chess.Color color) {
    int p = 0, n = 0, b = 0, r = 0, q = 0;
    for (int i = 0; i < 128; i++) {
      if ((i & 0x88) != 0) continue;
      final piece = board.board[i];
      if (piece == null || piece.color != color) continue;
      switch (piece.type) {
        case chess.PieceType.PAWN:
          p++;
          break;
        case chess.PieceType.KNIGHT:
          n++;
          break;
        case chess.PieceType.BISHOP:
          b++;
          break;
        case chess.PieceType.ROOK:
          r++;
          break;
        case chess.PieceType.QUEEN:
          q++;
          break;
        default:
          break;
      }
    }
    return _Material(pawns: p, knights: n, bishops: b, rooks: r, queens: q);
  }

  bool get onlyKing =>
      pawns == 0 && knights == 0 && bishops == 0 && rooks == 0 && queens == 0;
}

// ─────────────────────────────────────────────────────────
// PATTERN CHECKS
// ─────────────────────────────────────────────────────────
bool _isKqVsK(_Material w, _Material b) =>
    (w.queens == 1 &&
        w.pawns == 0 &&
        w.knights == 0 &&
        w.bishops == 0 &&
        w.rooks == 0 &&
        b.onlyKing) ||
    (b.queens == 1 &&
        b.pawns == 0 &&
        b.knights == 0 &&
        b.bishops == 0 &&
        b.rooks == 0 &&
        w.onlyKing);

bool _isKrVsK(_Material w, _Material b) =>
    (w.rooks == 1 &&
        w.pawns == 0 &&
        w.knights == 0 &&
        w.bishops == 0 &&
        w.queens == 0 &&
        b.onlyKing) ||
    (b.rooks == 1 &&
        b.pawns == 0 &&
        b.knights == 0 &&
        b.bishops == 0 &&
        b.queens == 0 &&
        w.onlyKing);

bool _isKbbVsK(_Material w, _Material b) =>
    (w.bishops == 2 &&
        w.pawns == 0 &&
        w.knights == 0 &&
        w.rooks == 0 &&
        w.queens == 0 &&
        b.onlyKing) ||
    (b.bishops == 2 &&
        b.pawns == 0 &&
        b.knights == 0 &&
        b.rooks == 0 &&
        b.queens == 0 &&
        w.onlyKing);

bool _isKvK(_Material w, _Material b) => w.onlyKing && b.onlyKing;

// ─────────────────────────────────────────────────────────
// MOVE SELECTION
// ─────────────────────────────────────────────────────────

/// Pick the best legal move using a mop-up heuristic:
/// drive the losing king to the edge and bring the winning king close.
chess.Move? _mopUpMove(
  chess.Chess board, {
  required bool whiteToMove,
  required bool winnerHasQueen,
}) {
  final moves = board.generate_moves();
  if (moves.isEmpty) return null;

  // Determine which side is winning
  final wMat = _Material.fromBoard(board, chess.Color.WHITE);
  final bool whiteWinning = !wMat.onlyKing;

  chess.Move? bestMove;
  int bestScore = -999999;

  for (final move in moves) {
    board.move(move);

    // Find kings
    int? wKing, bKing;
    for (int i = 0; i < 128; i++) {
      if ((i & 0x88) != 0) continue;
      final p = board.board[i];
      if (p == null) continue;
      if (p.type == chess.PieceType.KING) {
        final sq = _ox88ToSq(i);
        if (p.color == chess.Color.WHITE)
          wKing = sq;
        else
          bKing = sq;
      }
    }

    board.undo_move();

    if (wKing == null || bKing == null) continue;

    final losingKing = whiteWinning ? bKing : wKing;
    final winningKing = whiteWinning ? wKing : bKing;

    // Edge proximity (higher = more cornered)
    final edgeScore = _edgeDistance(losingKing) * 15;
    // King proximity (winning king close to losing king)
    final proxScore = (14 - _chebyshev(winningKing, losingKing)) * 8;

    final score = edgeScore + proxScore;
    if (score > bestScore) {
      bestScore = score;
      bestMove = move;
    }
  }

  return bestMove ?? moves.first;
}

/// Convert 0x88 board index to 0–63 square index.
int _ox88ToSq(int ox88) => (ox88 & 7) + ((ox88 >> 4) * 8);

int _file(int sq) => sq % 8;
int _rank(int sq) => sq ~/ 8;

int _chebyshev(int a, int b) {
  final fd = (_file(a) - _file(b)).abs();
  final rd = (_rank(a) - _rank(b)).abs();
  return fd > rd ? fd : rd;
}

/// How far the king is from the center (higher = closer to edge/corner).
int _edgeDistance(int sq) {
  final f = _file(sq);
  final r = _rank(sq);
  final fd = (3 - f) > (f - 4) ? (3 - f) : (f - 4);
  final rd = (3 - r) > (r - 4) ? (3 - r) : (r - 4);
  return fd + rd;
}

chess.Move? _anyLegalMove(chess.Chess board) {
  final moves = board.generate_moves();
  return moves.isNotEmpty ? moves.first : null;
}
