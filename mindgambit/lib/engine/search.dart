import 'package:chess/chess.dart' as chess;
import 'evaluation.dart';
import 'move_ordering.dart';
import 'transposition.dart';

// ─────────────────────────────────────────────────────────
// SEARCH CONSTANTS
// ─────────────────────────────────────────────────────────
const int maxCheckExtensions = 3;
const int lmrFullDepthMoves = 3;
const int lmrReductionLimit = 3;
const int deltaMargin = 200;

/// Max time per search in milliseconds (prevents freezes)
const int maxSearchTimeMs = 5000;

// ─────────────────────────────────────────────────────────
// SEARCH STATS
// ─────────────────────────────────────────────────────────
class SearchStats {
  int nodes = 0;
  int qnodes = 0;
  int cutoffs = 0;
  int ttHits = 0;
  int ttProbes = 0;
  int maxPly = 0;
  int maxQPly = 0;
}

// ─────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────
bool _isCapture(chess.Chess board, chess.Move move) {
  return board.get(move.toAlgebraic) != null ||
      (move.flags & chess.Chess.BITS_EP_CAPTURE != 0);
}

bool _movesEqual(chess.Move a, chess.Move b) {
  return a.fromAlgebraic == b.fromAlgebraic &&
      a.toAlgebraic == b.toAlgebraic &&
      a.promotion == b.promotion;
}

bool _isRepetition(chess.Chess board) {
  return board.in_threefold_repetition;
}

// ─────────────────────────────────────────────────────────
// QUIESCENCE SEARCH
// ─────────────────────────────────────────────────────────
int quiescence(
  chess.Chess board,
  int alpha,
  int beta,
  int ply,
  SearchStats stats,
  Stopwatch sw,
) {
  stats.qnodes++;
  if (ply > stats.maxQPly) stats.maxQPly = ply;

  // Time cutoff in quiescence
  if (stats.qnodes % 512 == 0 && sw.elapsedMilliseconds > maxSearchTimeMs) {
    return alpha;
  }

  if (board.in_checkmate) return -mateScore + ply;
  if (board.in_stalemate) return 0;

  int standPat = evaluate(board, ply);
  if (board.turn == chess.Color.BLACK) standPat = -standPat;

  if (standPat >= beta) return beta;
  if (standPat > alpha) alpha = standPat;

  final inCheck = board.in_check;
  List<chess.Move> moves;
  if (inCheck) {
    moves = board.generate_moves();
  } else {
    moves = board.generate_moves().where((m) => _isCapture(board, m)).toList();
    if (standPat + 1000 + deltaMargin < alpha) return alpha;
  }

  moves = orderMoves(board, moves);

  for (final move in moves) {
    board.move(move);
    final score = -quiescence(board, -beta, -alpha, ply + 1, stats, sw);
    board.undo_move();

    if (score >= beta) return beta;
    if (score > alpha) alpha = score;
  }

  return alpha;
}

// ─────────────────────────────────────────────────────────
// NEGAMAX SEARCH WITH ALPHA-BETA
// ─────────────────────────────────────────────────────────
({int score, chess.Move? move}) negamax(
  chess.Chess board,
  int depth,
  int alpha,
  int beta,
  int ply,
  int checkExtUsed,
  SearchStats stats,
  Map<int, List<chess.Move>> killers,
  Map<String, int> history,
  TranspositionTable tt,
  Stopwatch sw,
) {
  stats.nodes++;
  if (ply > stats.maxPly) stats.maxPly = ply;

  // Time cutoff
  if (stats.nodes % 1024 == 0 && sw.elapsedMilliseconds > maxSearchTimeMs) {
    return (score: alpha, move: null);
  }

  if (_isRepetition(board)) return (score: 0, move: null);

  // TT probe
  final statsRef = SearchStatsRef();
  final cached = tt.lookup(board, depth, alpha, beta, stats: statsRef);
  stats.ttProbes += statsRef.ttProbes;
  stats.ttHits += statsRef.ttHits;
  if (cached != null) return (score: cached.score, move: cached.move);

  final originalAlpha = alpha;

  if (board.game_over) {
    int score = evaluate(board, ply);
    if (board.turn == chess.Color.BLACK) score = -score;
    return (score: score, move: null);
  }

  if (depth <= 0) {
    return (score: quiescence(board, alpha, beta, ply, stats, sw), move: null);
  }

  final inCheck = board.in_check;
  final ttMove = tt.probeMove(board);

  // Null-move pruning: skipped — chess package doesn't support null moves

  var moves = board.generate_moves();
  final plyKillers = killers[ply] ?? [];
  moves = orderMoves(
    board,
    moves,
    ttMove: ttMove,
    killers: plyKillers,
    history: history,
  );

  if (moves.isEmpty) {
    int score = evaluate(board, ply);
    if (board.turn == chess.Color.BLACK) score = -score;
    return (score: score, move: null);
  }

  chess.Move? bestMove;
  int bestValue = -999999;
  int movesSearched = 0;

  for (final move in moves) {
    final isCap = _isCapture(board, move);

    board.move(move);

    int newDepth = depth - 1;
    int newExt = checkExtUsed;

    // Check extension
    if (board.in_check && checkExtUsed < maxCheckExtensions) {
      newDepth = depth;
      newExt++;
    }

    int value;

    if (movesSearched == 0) {
      final result = negamax(
        board,
        newDepth,
        -beta,
        -alpha,
        ply + 1,
        newExt,
        stats,
        killers,
        history,
        tt,
        sw,
      );
      value = -result.score;
    } else {
      // LMR
      int reduction = 0;
      if (movesSearched >= lmrFullDepthMoves &&
          depth >= lmrReductionLimit &&
          !inCheck &&
          !isCap &&
          move.promotion == null) {
        reduction = 1;
        if (movesSearched >= 6) reduction = 2;
      }

      var result = negamax(
        board,
        newDepth - reduction,
        -alpha - 1,
        -alpha,
        ply + 1,
        newExt,
        stats,
        killers,
        history,
        tt,
        sw,
      );
      value = -result.score;

      if (reduction > 0 && value > alpha) {
        result = negamax(
          board,
          newDepth,
          -alpha - 1,
          -alpha,
          ply + 1,
          newExt,
          stats,
          killers,
          history,
          tt,
          sw,
        );
        value = -result.score;
      }

      if (value > alpha && value < beta) {
        result = negamax(
          board,
          newDepth,
          -beta,
          -alpha,
          ply + 1,
          newExt,
          stats,
          killers,
          history,
          tt,
          sw,
        );
        value = -result.score;
      }
    }

    board.undo_move();
    movesSearched++;

    // Time cutoff after move
    if (sw.elapsedMilliseconds > maxSearchTimeMs) {
      if (value > bestValue) {
        bestValue = value;
        bestMove = move;
      }
      break;
    }

    if (value > bestValue) {
      bestValue = value;
      bestMove = move;
    }

    if (value > alpha) {
      alpha = value;
      if (!isCap && move.promotion == null) {
        final hKey =
            '${board.turn == chess.Color.WHITE ? "w" : "b"}_${move.fromAlgebraic}_${move.toAlgebraic}';
        history[hKey] = (history[hKey] ?? 0) + depth * depth;
      }
    }

    if (alpha >= beta) {
      stats.cutoffs++;
      if (!isCap && move.promotion == null) {
        if (!killers.containsKey(ply)) killers[ply] = [];
        final kList = killers[ply]!;
        if (!kList.any((k) => _movesEqual(k, move))) {
          kList.insert(0, move);
          if (kList.length > 2) kList.removeLast();
        }
      }
      break;
    }
  }

  tt.store(board, depth, bestValue, bestMove, originalAlpha, beta);
  return (score: bestValue, move: bestMove);
}

// ─────────────────────────────────────────────────────────
// ITERATIVE DEEPENING WITH TIME LIMIT
// ─────────────────────────────────────────────────────────
({chess.Move? move, int value, int depth, SearchStats stats, int elapsedMs})
iterativeDeepening(
  chess.Chess board,
  int maxDepth, {
  bool engineIsBlack = true,
}) {
  final stats = SearchStats();
  final sw = Stopwatch()..start();

  chess.Move? bestMove;
  int bestDepth = 0;
  int bestValue = 0;

  final killers = <int, List<chess.Move>>{};
  final history = <String, int>{};
  final tt = TranspositionTable();

  int prevScore = 0;
  const aspirationWindow = 50;

  for (int depth = 1; depth <= maxDepth; depth++) {
    // Time check before starting next depth
    if (depth > 1 && sw.elapsedMilliseconds > maxSearchTimeMs) break;

    int alpha, beta;
    if (depth <= 2) {
      alpha = -1000000;
      beta = 1000000;
    } else {
      alpha = prevScore - aspirationWindow;
      beta = prevScore + aspirationWindow;
    }

    var result = negamax(
      board,
      depth,
      alpha,
      beta,
      0,
      0,
      stats,
      killers,
      history,
      tt,
      sw,
    );

    // Re-search with full window on fail
    if (result.score <= alpha || result.score >= beta) {
      if (sw.elapsedMilliseconds < maxSearchTimeMs) {
        result = negamax(
          board,
          depth,
          -1000000,
          1000000,
          0,
          0,
          stats,
          killers,
          history,
          tt,
          sw,
        );
      }
    }

    if (result.move != null) {
      bestMove = result.move;
      bestDepth = depth;
      bestValue = result.score;
    }

    prevScore = result.score;

    // If we're already past time, don't start next depth
    if (sw.elapsedMilliseconds > maxSearchTimeMs) break;
  }

  sw.stop();

  if (engineIsBlack) bestValue = -bestValue;

  return (
    move: bestMove,
    value: bestValue,
    depth: bestDepth,
    stats: stats,
    elapsedMs: sw.elapsedMilliseconds,
  );
}

// ─────────────────────────────────────────────────────────
// OPENING BOOK — instant replies for common openings
// ─────────────────────────────────────────────────────────
chess.Move? _findOpeningMove(chess.Chess board) {
  final moves = board.generate_moves();

  chess.Move? _findMove(String from, String to) {
    for (final m in moves) {
      if (m.fromAlgebraic == from && m.toAlgebraic == to && m.promotion == null)
        return m;
    }
    return null;
  }

  final hist = board.getHistory();

  // White's first move
  if (hist.isEmpty && board.turn == chess.Color.WHITE) {
    // Play e4 or d4
    return _findMove('e2', 'e4') ?? _findMove('d2', 'd4');
  }

  // Black's first reply
  if (hist.length == 1 && board.turn == chess.Color.BLACK) {
    final whiteMove = hist.first;
    if (whiteMove == 'e4')
      return _findMove('e7', 'e5') ?? _findMove('c7', 'c5');
    if (whiteMove == 'd4')
      return _findMove('d7', 'd5') ?? _findMove('g8', 'f6');
    if (whiteMove == 'Nf3')
      return _findMove('d7', 'd5') ?? _findMove('g8', 'f6');
    if (whiteMove == 'c4')
      return _findMove('e7', 'e5') ?? _findMove('g8', 'f6');
    // Default: play e5 or d5
    return _findMove('e7', 'e5') ?? _findMove('d7', 'd5');
  }

  // White's second move
  if (hist.length == 2 && board.turn == chess.Color.WHITE) {
    final w1 = hist[0];
    final b1 = hist[1];
    if (w1 == 'e4' && b1 == 'e5') return _findMove('g1', 'f3'); // Nf3
    if (w1 == 'e4' && b1 == 'c5')
      return _findMove('g1', 'f3'); // Nf3 (Sicilian)
    if (w1 == 'd4' && b1 == 'd5')
      return _findMove('c2', 'c4'); // c4 (Queen's Gambit)
    if (w1 == 'd4' && b1 == 'Nf6') return _findMove('c2', 'c4'); // c4
  }

  // Black's second move
  if (hist.length == 3 && board.turn == chess.Color.BLACK) {
    final w1 = hist[0];
    final b1 = hist[1];
    final w2 = hist[2];
    if (w1 == 'e4' && b1 == 'e5' && w2 == 'Nf3')
      return _findMove('b8', 'c6'); // Nc6
    if (w1 == 'd4' && b1 == 'd5' && w2 == 'c4')
      return _findMove('e7', 'e6'); // e6 (QGD)
  }

  return null;
}

// ─────────────────────────────────────────────────────────
// HIGH-LEVEL SEARCH API
// ─────────────────────────────────────────────────────────
({chess.Move? move, Map<String, int> info}) searchWithInfo(
  chess.Chess board,
  int maxDepth, {
  bool engineIsBlack = true,
}) {
  // Try opening book first (instant)
  final bookMove = _findOpeningMove(board);
  if (bookMove != null) {
    return (
      move: bookMove,
      info: {
        'eval_cp': 0,
        'depth': 0,
        'time_ms': 0,
        'nodes': 0,
        'qnodes': 0,
        'cutoffs': 0,
        'tt_hits': 0,
        'tt_probes': 0,
        'max_ply': 0,
        'max_qply': 0,
      },
    );
  }

  final result = iterativeDeepening(
    board,
    maxDepth,
    engineIsBlack: engineIsBlack,
  );

  return (
    move: result.move,
    info: {
      'eval_cp': result.value,
      'depth': result.depth,
      'time_ms': result.elapsedMs,
      'nodes': result.stats.nodes,
      'qnodes': result.stats.qnodes,
      'cutoffs': result.stats.cutoffs,
      'tt_hits': result.stats.ttHits,
      'tt_probes': result.stats.ttProbes,
      'max_ply': result.stats.maxPly,
      'max_qply': result.stats.maxQPly,
    },
  );
}
