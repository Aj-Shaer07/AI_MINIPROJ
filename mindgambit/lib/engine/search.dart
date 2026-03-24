import 'package:chess/chess.dart' as chess;
import 'evaluation.dart';
import 'move_ordering.dart';
import 'tablebase.dart';
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
  // Match Python's is_repetition(2): detect 2-fold repetition.
  // Count how many times the current position FEN (board + turn + castling + ep)
  // has appeared in the game history.
  final fen = board.fen;
  final parts = fen.split(' ');
  final posKey = '${parts[0]} ${parts[1]} ${parts[2]} ${parts[3]}';

  // Walk backwards through the move history by undoing moves,
  // checking the position key at each step.
  // We use a simpler approach: the chess package exposes the header/fen list
  // implicitly. We'll use the board's built-in by counting via undo/redo.
  int count = 1; // current position counts as 1
  final undone = <chess.Move>[];
  // Only need to check back to last irreversible move (capture/pawn move)
  while (board.half_moves > 0) {
    final move = board.undo_move();
    if (move == null) break;
    undone.add(move);
    final hFen = board.fen;
    final hParts = hFen.split(' ');
    final hKey = '${hParts[0]} ${hParts[1]} ${hParts[2]} ${hParts[3]}';
    if (hKey == posKey) {
      count++;
      if (count >= 2) break; // 2-fold found
    }
    // If halfmove clock is 0 in the reached position, no earlier
    // position can match (irreversible move happened)
    if (board.half_moves == 0) break;
  }
  // Redo all undone moves to restore the board
  for (int i = undone.length - 1; i >= 0; i--) {
    board.move(undone[i]);
  }
  return count >= 2;
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
  Stopwatch sw, [
  List<Map<String, dynamic>>? rootMoves,
]) {
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

  // ── Null-Move Pruning ──────────────────────────────────────
  // Simulate a null move by flipping the side-to-move in a board copy.
  // Skip when: in check, at root (ply == 0), shallow depth, or near-zugzwang.
  if (!inCheck && depth >= 3 && ply > 0 && _hasNonPawnMaterial(board)) {
    final nullBoard = _makeNullMoveBoard(board);
    if (nullBoard != null) {
      final nullResult = negamax(
        nullBoard,
        depth - 3,
        -beta,
        -beta + 1,
        ply + 1,
        checkExtUsed,
        stats,
        killers,
        history,
        tt,
        sw,
      );
      final nullScore = -nullResult.score;
      if (nullScore >= beta) {
        stats.cutoffs++;
        return (score: beta, move: null);
      }
    }
  }

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

    if (ply == 0 && rootMoves != null) {
      rootMoves.add({'move': move, 'score': value});
    }

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
({
  chess.Move? move,
  int value,
  int depth,
  SearchStats stats,
  int elapsedMs,
  List<Map<String, dynamic>> alternatives,
})
iterativeDeepening(
  chess.Chess board,
  int maxDepth, {
  bool engineIsBlack = true,
  TranspositionTable? externalTT,
}) {
  final stats = SearchStats();
  final sw = Stopwatch()..start();

  chess.Move? bestMove;
  int bestDepth = 0;
  int bestValue = 0;

  final killers = <int, List<chess.Move>>{};
  final history = <String, int>{};
  final tt = externalTT ?? TranspositionTable();

  int totalPieces = 0;
  for (int i = 0; i < 128; i++) {
    if ((i & 0x88) == 0 && board.board[i] != null) totalPieces++;
  }
  if (totalPieces <= 6) {
    maxDepth += 3;
  } else if (totalPieces <= 10) {
    maxDepth += 2;
  } else if (totalPieces <= 16) {
    maxDepth += 1;
  }

  int prevScore = 0;
  const aspirationWindow = 50;

  List<Map<String, dynamic>> bestRootMoves = [];

  for (int depth = 1; depth <= maxDepth; depth++) {
    if (depth > 1 && sw.elapsedMilliseconds > maxSearchTimeMs) break;

    int alpha, beta;
    if (depth <= 2) {
      alpha = -1000000;
      beta = 1000000;
    } else {
      alpha = prevScore - aspirationWindow;
      beta = prevScore + aspirationWindow;
    }

    List<Map<String, dynamic>> currentRootMoves = [];
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
      currentRootMoves,
    );

    if (result.score <= alpha || result.score >= beta) {
      if (sw.elapsedMilliseconds < maxSearchTimeMs) {
        currentRootMoves.clear();
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
          currentRootMoves,
        );
      }
    }

    if (result.move != null) {
      bestMove = result.move;
      bestDepth = depth;
      bestValue = result.score;
      bestRootMoves = currentRootMoves;
    }

    prevScore = result.score;

    if (sw.elapsedMilliseconds > maxSearchTimeMs) break;
  }

  sw.stop();

  if (engineIsBlack) bestValue = -bestValue;

  bestRootMoves.sort(
    (a, b) => (b['score'] as int).compareTo(a['score'] as int),
  );
  final alternatives = <Map<String, dynamic>>[];
  for (int i = 0; i < bestRootMoves.length && i < 3; i++) {
    final rm = bestRootMoves[i];
    final m = rm['move'] as chess.Move;
    int sc = rm['score'] as int;
    if (engineIsBlack) sc = -sc;

    String moveUci = '${m.fromAlgebraic}${m.toAlgebraic}';
    if (m.promotion != null) {
      moveUci += m.promotion!.name.toLowerCase();
    }

    alternatives.add({'move_uci': moveUci, 'eval_cp': sc});
  }

  return (
    move: bestMove,
    value: bestValue,
    depth: bestDepth,
    stats: stats,
    elapsedMs: sw.elapsedMilliseconds,
    alternatives: alternatives,
  );
}

// ─────────────────────────────────────────────────────────
// OPENING BOOK — instant replies for common openings
// ─────────────────────────────────────────────────────────
chess.Move? _findOpeningMove(chess.Chess board) {
  // Match Python: only handle Black's first reply to 1.e4 and 1.d4
  final hist = board.getHistory();

  if (hist.length == 1 && board.turn == chess.Color.BLACK) {
    final moves = board.generate_moves();
    chess.Move? findMove(String from, String to) {
      for (final m in moves) {
        if (m.fromAlgebraic == from &&
            m.toAlgebraic == to &&
            m.promotion == null)
          return m;
      }
      return null;
    }

    final whiteMove = hist.first;
    if (whiteMove == 'e4') {
      final reply = findMove('e7', 'e5');
      if (reply != null) return reply;
    }
    if (whiteMove == 'd4') {
      final reply = findMove('d7', 'd5');
      if (reply != null) return reply;
    }
  }

  return null;
}

// ─────────────────────────────────────────────────────────
// NULL-MOVE HELPERS
// ─────────────────────────────────────────────────────────

/// Create a board copy with the side-to-move flipped (simulates a null move).
/// Returns null if the FEN cannot be rebuilt (shouldn't happen for normal positions).
chess.Chess? _makeNullMoveBoard(chess.Chess board) {
  try {
    final fen = board.fen;
    final parts = fen.split(' ');
    if (parts.length < 6) return null;
    // Flip side to move
    parts[1] = parts[1] == 'w' ? 'b' : 'w';
    // Clear en-passant square
    parts[3] = '-';
    // Increment halfmove clock
    final hm = int.tryParse(parts[4]) ?? 0;
    parts[4] = (hm + 1).toString();
    final newFen = parts.join(' ');
    final copy = chess.Chess.fromFEN(newFen);
    return copy;
  } catch (_) {
    return null;
  }
}

/// Returns true if the side to move has at least one non-pawn, non-king piece.
bool _hasNonPawnMaterial(chess.Chess board) {
  for (int i = 0; i < 128; i++) {
    if ((i & 0x88) != 0) continue;
    final p = board.board[i];
    if (p == null || p.color != board.turn) continue;
    if (p.type != chess.PieceType.PAWN && p.type != chess.PieceType.KING) {
      return true;
    }
  }
  return false;
}

// ─────────────────────────────────────────────────────────
// HIGH-LEVEL SEARCH API
// ─────────────────────────────────────────────────────────
({chess.Move? move, Map<String, dynamic> info}) searchWithInfo(
  chess.Chess board,
  int maxDepth, {
  bool engineIsBlack = true,
  TranspositionTable? tt,
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

  // Try built-in tablebase for ≤4-piece endgames (mirrors Python tablebase.py)
  if (isTablebaseLoaded()) {
    final tbMove = tablebaseMoveForRoot(board);
    if (tbMove != null) {
      return (
        move: tbMove,
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
  }

  final result = iterativeDeepening(
    board,
    maxDepth,
    engineIsBlack: engineIsBlack,
    externalTT: tt,
  );

  final info = <String, dynamic>{
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
    'alternatives': result.alternatives,
  };

  return (move: result.move, info: info);
}
