import 'package:chess/chess.dart' as chess;
import 'evaluation.dart';

/// Provides Explainable AI (XAI) features for the engine.
class Explainer {
  static const int _openingPhase = 24;
  static const int _endgamePhase = 8;

  static String _getPhaseName(int phaseValue) {
    if (phaseValue >= _openingPhase - 4) return "Opening";
    if (phaseValue <= _endgamePhase) return "Endgame";
    return "Middlegame";
  }

  /// Generates a human-readable summary of the current board evaluation.
  static String getPositionSummary(chess.Chess board) {
    final result = evaluateWithBreakdown(board);
    final scoreCp = result.score;
    final absScore = scoreCp.abs();

    String mainEval;
    if (absScore < 50) {
      mainEval = "Position is balanced";
    } else if (absScore < 150) {
      mainEval = scoreCp > 0
          ? "White is slightly better"
          : "Black is slightly better";
    } else if (absScore < 300) {
      mainEval = scoreCp > 0
          ? "White has a clear advantage"
          : "Black has a clear advantage";
    } else if (absScore >= 90000) {
      final mateInSq = (100000 - absScore + 1) ~/ 2;
      mainEval = scoreCp > 0
          ? "White has forced mate in $mateInSq"
          : "Black has forced mate in $mateInSq";
    } else {
      mainEval = scoreCp > 0
          ? "White is decisively winning"
          : "Black is decisively winning";
    }

    final pDisplay = (scoreCp / 100.0).toStringAsFixed(2);
    final evalStr = "$mainEval (${scoreCp > 0 ? '+' : ''}$pDisplay).";

    final snap = board.fen; // We can use fen to check material
    final testBoard = chess.Chess.fromFEN(snap);
    final basicEval = evaluateWithBreakdown(testBoard);
    final bk = basicEval.breakdown;

    final wMat =
        (bk['material_mg_white'] ?? 0) + (bk['material_eg_white'] ?? 0);
    final bMat =
        (bk['material_mg_black'] ?? 0) + (bk['material_eg_black'] ?? 0);
    final diff = wMat - bMat;

    String matStr;
    if (diff.abs() < 100) {
      matStr = "Material is equal.";
    } else if (diff >= 100) {
      matStr = "White is up material.";
    } else {
      matStr = "Black is up material.";
    }

    String passStr = "";
    final wPass =
        (bk['passed_pawns_mg'] ?? 0) > 0 || (bk['passed_pawns_eg'] ?? 0) > 0;
    final bPass =
        (bk['passed_pawns_mg'] ?? 0) < 0 || (bk['passed_pawns_eg'] ?? 0) < 0;
    if (wPass && !bPass) passStr = " White has a passed pawn.";
    if (!wPass && bPass) passStr = " Black has a passed pawn.";
    if (wPass && bPass) passStr = " Both sides have passed pawns.";

    return "$evalStr $matStr$passStr";
  }

  /// Generates a detailed explanation for why the engine chose a specific move.
  static Map<String, dynamic> explainMove(
    chess.Chess board,
    chess.Move move,
    Map<String, int> searchInfo,
  ) {
    // 1. Evaluate position BEFORE the move
    final beforeEval = evaluateWithBreakdown(board);
    final beforeScore = beforeEval.score;
    final beforeBk = beforeEval.breakdown;

    // 2. Evaluate position AFTER the move
    board.move(move);
    final afterEval = evaluateWithBreakdown(board, 1);
    final afterScore =
        -afterEval.score; // Negate to stay in absolute perspective
    final afterBk = afterEval.breakdown;
    board.undo(); // Restore to allow subsequent calls

    // 3. Compute the delta
    final isWhite = board.turn == chess.Color.WHITE;
    final sign = isWhite ? 1 : -1;
    final deltaCp = (afterScore - beforeScore) * sign;

    final bkDelta = <String, int>{};
    for (final key in afterBk.keys) {
      // afterBk is from opponent's perspective, so invert its meaning based on color
      int beforeVal = beforeBk[key] ?? 0;
      int afterVal = afterBk[key] ?? 0;
      if (!isWhite) {
        beforeVal = -beforeVal;
        afterVal =
            -afterVal; // Is it already from white's perspective? No, evaluate() is absolute.
      }
      // Wait, evaluate() ALWAYS returns white's absolute perspective for breakdown components!
      // Actually, my Dart evaluate() returns an absolute score? No, wait:
      // "Tapered eval... return score" -> evaluate() returns absolute score (positive = white advantage).
      // Let me re-read evaluate():
      // "mgScore += sign * m" -> white pieces add to mgScore, black pieces subtract from mgScore.
      // Yes, `evaluate` and `breakdown` are ALWAYS absolute (positive = good for White).
    }

    // Recalculate correctly using absolute perspective for both
    // Evaluate before
    final bBk = beforeEval.breakdown;

    // Evaluate after
    board.move(move);
    final aEval = evaluateWithBreakdown(
      board,
    ); // Call normally, NO NEGATION NEEDED here for absolute bk
    final aBk = aEval.breakdown;
    board.undo();

    for (final key in aBk.keys) {
      int beforeVal = bBk[key] ?? 0;
      int afterVal = aBk[key] ?? 0;
      int delta = afterVal - beforeVal;
      if (!isWhite) delta = -delta; // Convert to player's perspective
      bkDelta[key] = delta;
    }

    // 4. Determine Move Tags
    final tags = <String>[];
    final piece = board.get(move.fromAlgebraic);
    final captured = board.get(move.toAlgebraic);

    if (captured != null) tags.add("capture");

    board.move(move);
    if (board.in_check) tags.add("check");
    if (board.in_checkmate) tags.add("checkmate");
    board.undo();

    if (move.promotion != null) tags.add("promotion");
    if (tags.isEmpty) tags.add("quiet");

    // Get search data
    final depth = searchInfo['depth'] ?? 0;
    final nodes = searchInfo['nodes'] ?? 0;

    // 5. Build Narrative
    final narrative = _buildNarrative(
      board,
      move,
      piece!.type,
      captured?.type,
      tags,
      deltaCp,
      bkDelta,
      bBk['phase_value'] ?? 24,
      depth,
      nodes,
      isWhite,
    );

    return {
      "move_uci":
          '${move.fromAlgebraic}${move.toAlgebraic}${move.promotion?.name ?? ""}',
      "move_san": board.move_to_san(move),
      "before_eval_cp": beforeScore,
      "after_eval_cp": isWhite ? aEval.score : -aEval.score,
      "eval_delta_cp": deltaCp,
      "game_phase": _getPhaseName(bBk['phase_value'] ?? 24),
      "move_tags": tags,
      "breakdown_delta": bkDelta,
      "narrative": narrative,
      "full_breakdown_after": aBk,
    };
  }

  static List<String> _buildNarrative(
    chess.Chess board,
    chess.Move move,
    chess.PieceType pt,
    chess.PieceType? capturedPt,
    List<String> tags,
    int deltaCp,
    Map<String, int> bkDelta,
    int phaseValue,
    int depth,
    int nodes,
    bool isWhite,
  ) {
    final list = <String>[];
    final ptName = pt.name.toLowerCase();

    // Action sentence
    if (tags.contains("checkmate")) {
      list.add("Delivers checkmate.");
    } else if (tags.contains("capture")) {
      list.add(
        "Captures the ${capturedPt!.name.toLowerCase()} on ${move.toAlgebraic} with the $ptName.",
      );
    } else if (tags.contains("promotion")) {
      list.add("Promotes the pawn to a ${move.promotion!.name.toLowerCase()}.");
    } else {
      list.add(
        "Moves $ptName from ${move.fromAlgebraic} to ${move.toAlgebraic}.",
      );
    }

    if (tags.contains("check") && !tags.contains("checkmate")) {
      list.add("Places the opponent's king in check.");
    }

    // Material analysis
    int matDelta = 0;
    if (isWhite) {
      matDelta =
          (bkDelta['material_mg_white'] ?? 0) -
          (bkDelta['material_mg_black'] ?? 0);
    } else {
      matDelta =
          (bkDelta['material_mg_black'] ?? 0) -
          (bkDelta['material_mg_white'] ?? 0);
    }

    if (matDelta > 50) {
      list.add("Wins material (+${(matDelta / 100).toStringAsFixed(2)}).");
    } else if (matDelta < -50) {
      list.add("Sacrifices material (${(matDelta / 100).toStringAsFixed(2)}).");
    }

    // Positional analysis (PST)
    int pstDelta = 0;
    if (isWhite) {
      pstDelta =
          (bkDelta['pst_mg_white'] ?? 0) - (bkDelta['pst_mg_black'] ?? 0);
    } else {
      pstDelta =
          (bkDelta['pst_mg_black'] ?? 0) - (bkDelta['pst_mg_white'] ?? 0);
    }

    if (tags.contains("quiet") && pstDelta > 20) {
      list.add(
        "Develops a piece, improving activity (+${(pstDelta / 100).toStringAsFixed(2)}).",
      );
    }

    // Structural analysis
    final sDelta =
        (bkDelta['passed_pawns_mg'] ?? 0) + (bkDelta['passed_pawns_eg'] ?? 0);
    if (sDelta > 20) {
      list.add("Creates or advances a dangerous passed pawn.");
    }

    if ((bkDelta['doubled_pawns_eg'] ?? 0) < -10 ||
        (bkDelta['isolated_pawns_mg'] ?? 0) < -10) {
      list.add("Accepts a minor structural weakness.");
    } else if ((bkDelta['doubled_pawns_eg'] ?? 0) > 10) {
      list.add("Improves pawn structure.");
    }

    // King Safety
    if ((bkDelta['king_shield_mg'] ?? 0) > 15) {
      list.add("Strengthens the king's defensive pawn shield.");
    }

    // Hanging pieces
    if ((bkDelta['hanging_penalty_mg'] ?? 0) > 30) {
      list.add("Defends a previously attacked piece.");
    }

    // Contextual phase
    final phase = _getPhaseName(phaseValue);
    if (phase == "Opening") {
      list.add("Early game — development and center control are key.");
    } else if (phase == "Endgame") {
      list.add("Endgame — king activity and passed pawns decide the game.");
    }

    // Engine validation
    final nodeStr = nodes >= 1000
        ? "${(nodes / 1000).toStringAsFixed(1)}k nodes"
        : "$nodes nodes";
    list.add("Engine confirmed this at depth $depth ($nodeStr searched).");

    return list;
  }
}
