import 'dart:async';

import 'package:chess/chess.dart' as chess;
import 'package:flutter/foundation.dart';
import 'search.dart';
import 'transposition.dart';
import '../models/difficulty.dart';
import '../models/engine_result.dart';

// ─────────────────────────────────────────────────────────
// CHESS ENGINE — compute() wrapper for non-blocking AI
// ─────────────────────────────────────────────────────────
class ChessEngine {
  /// Persistent transposition table — survives across moves (like Python's global TT).
  /// Note: this is only used for the sync path. The isolate compute() path
  /// creates its own TT per call since isolate boundaries prevent sharing.
  static final TranspositionTable _tt = TranspositionTable();

  /// Clear the transposition table (call when starting a new game).
  static void clearTT() => _tt.clear();

  /// Compute the best move asynchronously via Flutter compute().
  static Future<EngineResult> findBestMove({
    required String fen,
    required Difficulty difficulty,
    required bool engineIsBlack,
  }) async {
    try {
      final result = await compute(
        _computeSearch,
        _SearchParams(
          fen: fen,
          maxDepth: difficulty.depth,
          engineIsBlack: engineIsBlack,
        ),
      );
      return result;
    } catch (e) {
      debugPrint('[ChessEngine] Error in compute: $e');
      // Fallback: run synchronously (uses persistent TT)
      return findBestMoveSync(
        fen: fen,
        difficulty: difficulty,
        engineIsBlack: engineIsBlack,
      );
    }
  }

  /// Synchronous search (fallback) — uses persistent TT.
  static EngineResult findBestMoveSync({
    required String fen,
    required Difficulty difficulty,
    required bool engineIsBlack,
  }) {
    final board = chess.Chess.fromFEN(fen);
    final result = searchWithInfo(
      board,
      difficulty.depth,
      engineIsBlack: engineIsBlack,
      tt: _tt,
    );

    String? moveStr;
    if (result.move != null) {
      moveStr = '${result.move!.fromAlgebraic}${result.move!.toAlgebraic}';
      if (result.move!.promotion != null) {
        moveStr += result.move!.promotion.toString();
      }
    }

    return EngineResult(
      bestMoveUci: moveStr,
      evalCp: result.info['eval_cp'] ?? 0,
      depth: result.info['depth'] ?? 0,
      nodes: result.info['nodes'] ?? 0,
      timeMs: result.info['time_ms'] ?? 0,
      explanation: result.info['explanation'] as Map<String, dynamic>?,
      alternatives: result.info['alternatives'] as List<Map<String, dynamic>>?,
    );
  }
}

// ─────────────────────────────────────────────────────────
// ISOLATE-SAFE PARAMS & COMPUTE FUNCTION
// ─────────────────────────────────────────────────────────
class _SearchParams {
  final String fen;
  final int maxDepth;
  final bool engineIsBlack;

  _SearchParams({
    required this.fen,
    required this.maxDepth,
    required this.engineIsBlack,
  });
}

EngineResult _computeSearch(_SearchParams params) {
  final board = chess.Chess.fromFEN(params.fen);
  final result = searchWithInfo(
    board,
    params.maxDepth,
    engineIsBlack: params.engineIsBlack,
    // Note: no external TT here — isolates can't share objects.
    // Each isolate call gets a fresh TT. This matches the Python behavior
    // for the primary compute path since Python also doesn't have threading.
  );

  String? moveStr;
  if (result.move != null) {
    moveStr = '${result.move!.fromAlgebraic}${result.move!.toAlgebraic}';
    if (result.move!.promotion != null) {
      moveStr += result.move!.promotion.toString();
    }
  }

  return EngineResult(
    bestMoveUci: moveStr,
    evalCp: result.info['eval_cp'] ?? 0,
    depth: result.info['depth'] ?? 0,
    nodes: result.info['nodes'] ?? 0,
    timeMs: result.info['time_ms'] ?? 0,
    explanation: result.info['explanation'] as Map<String, dynamic>?,
    alternatives: result.info['alternatives'] as List<Map<String, dynamic>>?,
  );
}
