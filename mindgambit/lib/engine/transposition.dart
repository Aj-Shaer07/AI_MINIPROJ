import 'package:chess/chess.dart' as chess;

// ─────────────────────────────────────────────────────────
// TRANSPOSITION TABLE
// ─────────────────────────────────────────────────────────
const int ttExact = 0;
const int ttLower = 1;
const int ttUpper = 2;
const int maxTTSize = 1 << 20; // ~1M entries

class TTEntry {
  final int depth;
  final int score;
  final int flag;
  final chess.Move? move;

  TTEntry(this.depth, this.score, this.flag, this.move);
}

class TranspositionTable {
  final Map<String, TTEntry> _table = {};

  String _key(chess.Chess board) {
    // Use board FEN (position only) + side to move as key
    return board.fen;
  }

  /// Probe the TT. Returns (score, move) or null.
  ({int score, chess.Move? move})? lookup(
    chess.Chess board,
    int depth,
    int alpha,
    int beta, {
    SearchStatsRef? stats,
  }) {
    if (stats != null) stats.ttProbes++;

    final entry = _table[_key(board)];
    if (entry == null) return null;
    if (entry.depth < depth) return null;

    if (entry.flag == ttExact) {
      if (stats != null) stats.ttHits++;
      return (score: entry.score, move: entry.move);
    }
    if (entry.flag == ttLower && entry.score >= beta) {
      if (stats != null) stats.ttHits++;
      return (score: entry.score, move: entry.move);
    }
    if (entry.flag == ttUpper && entry.score <= alpha) {
      if (stats != null) stats.ttHits++;
      return (score: entry.score, move: entry.move);
    }

    return null;
  }

  /// Return the best move stored for this position, or null.
  chess.Move? probeMove(chess.Chess board) {
    final entry = _table[_key(board)];
    return entry?.move;
  }

  /// Store a position in the TT.
  void store(
    chess.Chess board,
    int depth,
    int score,
    chess.Move? move,
    int alpha,
    int beta,
  ) {
    final key = _key(board);
    int flag = ttExact;
    if (score <= alpha) {
      flag = ttUpper;
    } else if (score >= beta) {
      flag = ttLower;
    }

    final existing = _table[key];
    if (existing != null && existing.depth > depth) return;

    _table[key] = TTEntry(depth, score, flag, move);

    // Evict if too large
    if (_table.length > maxTTSize) {
      final keysToRemove = _table.keys.take(maxTTSize ~/ 4).toList();
      for (final k in keysToRemove) {
        _table.remove(k);
      }
    }
  }

  void clear() => _table.clear();
}

/// Mutable stats reference to pass around.
class SearchStatsRef {
  int ttProbes = 0;
  int ttHits = 0;
}
