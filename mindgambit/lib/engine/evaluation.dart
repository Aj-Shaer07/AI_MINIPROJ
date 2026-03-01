import 'package:chess/chess.dart' as chess;

const int mateScore = 100000;

// ─────────────────────────────────────────────────────────
// MATERIAL VALUES (midgame / endgame)
// ─────────────────────────────────────────────────────────
final Map<chess.PieceType, int> mgValue = {
  chess.PieceType.PAWN: 82,
  chess.PieceType.KNIGHT: 337,
  chess.PieceType.BISHOP: 365,
  chess.PieceType.ROOK: 477,
  chess.PieceType.QUEEN: 1025,
  chess.PieceType.KING: 0,
};

final Map<chess.PieceType, int> egValue = {
  chess.PieceType.PAWN: 94,
  chess.PieceType.KNIGHT: 281,
  chess.PieceType.BISHOP: 297,
  chess.PieceType.ROOK: 512,
  chess.PieceType.QUEEN: 936,
  chess.PieceType.KING: 0,
};

final Map<chess.PieceType, int> pieceValues = {
  chess.PieceType.PAWN: 100,
  chess.PieceType.KNIGHT: 320,
  chess.PieceType.BISHOP: 330,
  chess.PieceType.ROOK: 500,
  chess.PieceType.QUEEN: 900,
  chess.PieceType.KING: 20000,
};

final Map<chess.PieceType, int> phaseWeight = {
  chess.PieceType.PAWN: 0,
  chess.PieceType.KNIGHT: 1,
  chess.PieceType.BISHOP: 1,
  chess.PieceType.ROOK: 2,
  chess.PieceType.QUEEN: 4,
  chess.PieceType.KING: 0,
};
const int totalPhase = 24;

// ─────────────────────────────────────────────────────────
// PeSTO PIECE-SQUARE TABLES (rank-8-first, flipped to rank-1-first)
// ─────────────────────────────────────────────────────────
List<int> _flip(List<int> table) {
  final result = List<int>.filled(64, 0);
  for (int rank = 7; rank >= 0; rank--) {
    for (int file = 0; file < 8; file++) {
      result[(7 - rank) * 8 + file] = table[rank * 8 + file];
    }
  }
  return result;
}

final List<int> mgPawnTable = _flip([
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  98,
  134,
  61,
  95,
  68,
  126,
  34,
  -11,
  -6,
  7,
  26,
  31,
  65,
  56,
  25,
  -20,
  -14,
  13,
  6,
  21,
  23,
  12,
  17,
  -23,
  -27,
  -2,
  -5,
  12,
  17,
  6,
  10,
  -25,
  -26,
  -4,
  -4,
  -10,
  3,
  3,
  33,
  -12,
  -35,
  -1,
  -20,
  -23,
  -15,
  24,
  38,
  -22,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
]);

final List<int> egPawnTable = _flip([
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  178,
  173,
  158,
  134,
  147,
  132,
  165,
  187,
  94,
  100,
  85,
  67,
  56,
  53,
  82,
  84,
  32,
  24,
  13,
  5,
  -2,
  4,
  17,
  17,
  13,
  9,
  -3,
  -7,
  -7,
  -8,
  3,
  -1,
  4,
  7,
  -6,
  1,
  0,
  -5,
  -1,
  -8,
  13,
  8,
  8,
  10,
  13,
  0,
  2,
  -7,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
]);

final List<int> mgKnightTable = _flip([
  -167,
  -89,
  -34,
  -49,
  61,
  -97,
  -15,
  -107,
  -73,
  -41,
  72,
  36,
  23,
  62,
  7,
  -17,
  -47,
  60,
  37,
  65,
  84,
  129,
  73,
  44,
  -9,
  17,
  19,
  53,
  37,
  69,
  18,
  22,
  -13,
  4,
  16,
  13,
  28,
  19,
  21,
  -8,
  -23,
  -9,
  12,
  10,
  19,
  17,
  25,
  -16,
  -29,
  -53,
  -12,
  -3,
  -1,
  18,
  -14,
  -19,
  -105,
  -21,
  -58,
  -33,
  -17,
  -28,
  -19,
  -23,
]);

final List<int> egKnightTable = _flip([
  -58,
  -38,
  -13,
  -28,
  -31,
  -27,
  -63,
  -99,
  -25,
  -8,
  -25,
  -2,
  -9,
  -25,
  -24,
  -52,
  -24,
  -20,
  10,
  9,
  -1,
  -9,
  -19,
  -41,
  -17,
  3,
  22,
  22,
  22,
  11,
  8,
  -18,
  -18,
  -6,
  16,
  25,
  16,
  17,
  4,
  -18,
  -23,
  -3,
  -1,
  15,
  10,
  -3,
  -20,
  -22,
  -42,
  -20,
  -10,
  -5,
  -2,
  -20,
  -23,
  -44,
  -29,
  -51,
  -23,
  -15,
  -22,
  -18,
  -50,
  -64,
]);

final List<int> mgBishopTable = _flip([
  -29,
  4,
  -82,
  -37,
  -25,
  -42,
  7,
  -8,
  -26,
  16,
  -18,
  -13,
  30,
  59,
  18,
  -47,
  -16,
  37,
  43,
  40,
  35,
  50,
  37,
  -2,
  -4,
  5,
  19,
  50,
  37,
  37,
  7,
  -2,
  -6,
  13,
  13,
  26,
  34,
  12,
  10,
  4,
  0,
  15,
  15,
  15,
  14,
  27,
  18,
  10,
  4,
  15,
  16,
  0,
  7,
  21,
  33,
  1,
  -33,
  -3,
  -14,
  -21,
  -13,
  -12,
  -39,
  -21,
]);

final List<int> egBishopTable = _flip([
  -14,
  -21,
  -11,
  -8,
  -7,
  -9,
  -17,
  -24,
  -8,
  -4,
  7,
  -12,
  -3,
  -13,
  -4,
  -14,
  2,
  -8,
  0,
  -1,
  -2,
  6,
  0,
  4,
  -3,
  9,
  12,
  9,
  14,
  10,
  3,
  2,
  -6,
  3,
  13,
  19,
  7,
  10,
  -3,
  -9,
  -12,
  -3,
  8,
  10,
  13,
  3,
  -7,
  -15,
  -14,
  -18,
  -7,
  -1,
  4,
  -9,
  -15,
  -27,
  -23,
  -9,
  -23,
  -5,
  -9,
  -16,
  -5,
  -17,
]);

final List<int> mgRookTable = _flip([
  32,
  42,
  32,
  51,
  63,
  9,
  31,
  43,
  27,
  32,
  58,
  62,
  80,
  67,
  26,
  44,
  -5,
  19,
  26,
  36,
  17,
  45,
  61,
  16,
  -24,
  -11,
  7,
  26,
  24,
  35,
  -8,
  -20,
  -36,
  -26,
  -12,
  -1,
  9,
  -7,
  6,
  -23,
  -45,
  -25,
  -16,
  -17,
  3,
  0,
  -5,
  -33,
  -44,
  -16,
  -20,
  -9,
  -1,
  11,
  -6,
  -71,
  -19,
  -13,
  1,
  17,
  16,
  7,
  -37,
  -26,
]);

final List<int> egRookTable = _flip([
  13,
  10,
  18,
  15,
  12,
  12,
  8,
  5,
  11,
  13,
  13,
  11,
  -3,
  3,
  8,
  3,
  7,
  7,
  7,
  5,
  4,
  -3,
  -5,
  -3,
  4,
  3,
  13,
  1,
  2,
  1,
  -1,
  2,
  3,
  5,
  8,
  4,
  -5,
  -6,
  -8,
  -11,
  -4,
  0,
  -5,
  -1,
  -7,
  -12,
  -8,
  -16,
  -6,
  -6,
  0,
  2,
  -9,
  -9,
  -11,
  -3,
  -9,
  2,
  3,
  -1,
  -5,
  -13,
  4,
  -20,
]);

final List<int> mgQueenTable = _flip([
  -28,
  0,
  29,
  12,
  59,
  44,
  43,
  45,
  -24,
  -39,
  -5,
  1,
  -16,
  57,
  28,
  54,
  -13,
  -17,
  7,
  8,
  29,
  56,
  47,
  57,
  -27,
  -27,
  -16,
  -16,
  -1,
  17,
  -2,
  1,
  -9,
  -26,
  -9,
  -10,
  -2,
  -4,
  3,
  -3,
  -14,
  2,
  -11,
  -2,
  -5,
  2,
  14,
  5,
  -35,
  -8,
  11,
  2,
  8,
  15,
  -3,
  1,
  -1,
  -18,
  -9,
  10,
  -15,
  -25,
  -31,
  -50,
]);

final List<int> egQueenTable = _flip([
  -9,
  22,
  22,
  27,
  27,
  19,
  10,
  20,
  -17,
  20,
  32,
  41,
  58,
  25,
  30,
  0,
  -20,
  6,
  9,
  49,
  47,
  35,
  19,
  9,
  3,
  22,
  24,
  45,
  57,
  40,
  57,
  36,
  -18,
  28,
  19,
  47,
  31,
  34,
  39,
  23,
  -16,
  -27,
  15,
  6,
  9,
  17,
  10,
  5,
  -22,
  -23,
  -30,
  -16,
  -16,
  -23,
  -36,
  -32,
  -33,
  -28,
  -22,
  -43,
  -5,
  -32,
  -20,
  -41,
]);

final List<int> mgKingTable = _flip([
  -65,
  23,
  16,
  -15,
  -56,
  -34,
  2,
  13,
  29,
  -1,
  -20,
  -7,
  -8,
  -4,
  -38,
  -29,
  -9,
  24,
  2,
  -16,
  -20,
  6,
  22,
  -22,
  -17,
  -20,
  -12,
  -27,
  -30,
  -25,
  -14,
  -36,
  -49,
  -1,
  -27,
  -39,
  -46,
  -44,
  -33,
  -51,
  -14,
  -14,
  -22,
  -46,
  -44,
  -30,
  -15,
  -27,
  1,
  7,
  -8,
  -64,
  -43,
  -16,
  9,
  8,
  -15,
  36,
  12,
  -54,
  8,
  -28,
  24,
  14,
]);

final List<int> egKingTable = _flip([
  -74,
  -35,
  -18,
  -18,
  -11,
  15,
  4,
  -17,
  -12,
  17,
  14,
  17,
  17,
  38,
  23,
  11,
  10,
  17,
  23,
  15,
  20,
  45,
  44,
  13,
  -8,
  22,
  24,
  27,
  26,
  33,
  26,
  3,
  -18,
  -4,
  21,
  24,
  27,
  23,
  9,
  -11,
  -19,
  -3,
  11,
  21,
  23,
  16,
  7,
  -9,
  -27,
  -11,
  4,
  13,
  14,
  4,
  -5,
  -17,
  -53,
  -34,
  -21,
  -11,
  -28,
  -14,
  -24,
  -43,
]);

final Map<chess.PieceType, List<int>> mgPst = {
  chess.PieceType.PAWN: mgPawnTable,
  chess.PieceType.KNIGHT: mgKnightTable,
  chess.PieceType.BISHOP: mgBishopTable,
  chess.PieceType.ROOK: mgRookTable,
  chess.PieceType.QUEEN: mgQueenTable,
  chess.PieceType.KING: mgKingTable,
};

final Map<chess.PieceType, List<int>> egPst = {
  chess.PieceType.PAWN: egPawnTable,
  chess.PieceType.KNIGHT: egKnightTable,
  chess.PieceType.BISHOP: egBishopTable,
  chess.PieceType.ROOK: egRookTable,
  chess.PieceType.QUEEN: egQueenTable,
  chess.PieceType.KING: egKingTable,
};

int _mirror(int sq) => sq ^ 56;

// ─────────────────────────────────────────────────────────
// PAWN STRUCTURE CONSTANTS
// ─────────────────────────────────────────────────────────
const int doubledPawnPenalty = -15;
const int isolatedPawnPenalty = -20;
const List<int> passedPawnBonusMg = [0, 5, 10, 20, 40, 65, 100, 0];
const List<int> passedPawnBonusEg = [0, 15, 30, 50, 90, 150, 250, 0];
const int bishopPairBonus = 30;
const int rookOpenFileBonus = 25;
const int rookSemiOpenFileBonus = 12;
const int kingShieldBonus = 10;

// ─────────────────────────────────────────────────────────
// Pre-computed square name table (avoid string allocs in hot path)
// ─────────────────────────────────────────────────────────
final List<String> _sqNames = List.generate(64, (sq) {
  return String.fromCharCode('a'.codeUnitAt(0) + (sq % 8)) +
      String.fromCharCode('1'.codeUnitAt(0) + (sq ~/ 8));
});

// ─────────────────────────────────────────────────────────
// BOARD SNAPSHOT — scan board once, cache everything
// ─────────────────────────────────────────────────────────
class _BoardSnapshot {
  final List<int> whitePawns = [];
  final List<int> blackPawns = [];
  final List<int> whiteKnights = [];
  final List<int> blackKnights = [];
  final List<int> whiteBishops = [];
  final List<int> blackBishops = [];
  final List<int> whiteRooks = [];
  final List<int> blackRooks = [];
  final List<int> whiteQueens = [];
  final List<int> blackQueens = [];
  int whiteKing = 0;
  int blackKing = 0;

  _BoardSnapshot(chess.Chess board) {
    for (int sq = 0; sq < 64; sq++) {
      final piece = board.get(_sqNames[sq]);
      if (piece == null) continue;
      final isW = piece.color == chess.Color.WHITE;
      final pt = piece.type;
      if (pt == chess.PieceType.PAWN) {
        (isW ? whitePawns : blackPawns).add(sq);
      } else if (pt == chess.PieceType.KNIGHT) {
        (isW ? whiteKnights : blackKnights).add(sq);
      } else if (pt == chess.PieceType.BISHOP) {
        (isW ? whiteBishops : blackBishops).add(sq);
      } else if (pt == chess.PieceType.ROOK) {
        (isW ? whiteRooks : blackRooks).add(sq);
      } else if (pt == chess.PieceType.QUEEN) {
        (isW ? whiteQueens : blackQueens).add(sq);
      } else if (pt == chess.PieceType.KING) {
        if (isW) {
          whiteKing = sq;
        } else {
          blackKing = sq;
        }
      }
    }
  }

  List<int> pawns(bool white) => white ? whitePawns : blackPawns;
  List<int> knights(bool white) => white ? whiteKnights : blackKnights;
  List<int> bishops(bool white) => white ? whiteBishops : blackBishops;
  List<int> rooks(bool white) => white ? whiteRooks : blackRooks;
  List<int> queens(bool white) => white ? whiteQueens : blackQueens;
  int king(bool white) => white ? whiteKing : blackKing;

  int totalPieces() =>
      whitePawns.length +
      blackPawns.length +
      whiteKnights.length +
      blackKnights.length +
      whiteBishops.length +
      blackBishops.length +
      whiteRooks.length +
      blackRooks.length +
      whiteQueens.length +
      blackQueens.length +
      2;

  bool hasNonPawnMaterial(bool white) {
    if (white) {
      return whiteKnights.isNotEmpty ||
          whiteBishops.isNotEmpty ||
          whiteRooks.isNotEmpty ||
          whiteQueens.isNotEmpty;
    }
    return blackKnights.isNotEmpty ||
        blackBishops.isNotEmpty ||
        blackRooks.isNotEmpty ||
        blackQueens.isNotEmpty;
  }

  int material(bool white) {
    if (white) {
      return whitePawns.length * 100 +
          whiteKnights.length * 320 +
          whiteBishops.length * 330 +
          whiteRooks.length * 500 +
          whiteQueens.length * 900;
    }
    return blackPawns.length * 100 +
        blackKnights.length * 320 +
        blackBishops.length * 330 +
        blackRooks.length * 500 +
        blackQueens.length * 900;
  }
}

// ─────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────
int _squareFile(int sq) => sq % 8;
int _squareRank(int sq) => sq ~/ 8;

int _chebyshevDistance(int sq1, int sq2) {
  final fd = (_squareFile(sq1) - _squareFile(sq2)).abs();
  final rd = (_squareRank(sq1) - _squareRank(sq2)).abs();
  return fd > rd ? fd : rd;
}

int _kingEdgeDistance(int sq) {
  final file = _squareFile(sq);
  final rank = _squareRank(sq);
  final fileDist = (3 - file) > (file - 4) ? (3 - file) : (file - 4);
  final rankDist = (3 - rank) > (rank - 4) ? (3 - rank) : (rank - 4);
  return fileDist + rankDist;
}

/// Check if side to move has non-pawn material (used by search for null-move).
bool hasNonPawnMaterial(chess.Chess board) {
  final snap = _BoardSnapshot(board);
  return snap.hasNonPawnMaterial(board.turn == chess.Color.WHITE);
}

// ─────────────────────────────────────────────────────────
// MAIN EVALUATION — single board scan
// ─────────────────────────────────────────────────────────
int evaluate(chess.Chess board, [int ply = 0]) {
  if (board.in_checkmate) {
    return board.turn == chess.Color.WHITE ? -mateScore + ply : mateScore - ply;
  }
  if (board.in_stalemate || board.insufficient_material) {
    return 0;
  }

  final snap = _BoardSnapshot(board);
  int mgScore = 0;
  int egScore = 0;
  int phase = 0;

  // Helper to add PST + material for a list of squares
  void _addPst(List<int> squares, chess.PieceType pt, int sign) {
    final mgTable = mgPst[pt]!;
    final egTable = egPst[pt]!;
    final mgVal = mgValue[pt]!;
    final egVal = egValue[pt]!;
    final pw = phaseWeight[pt]!;
    final needMirror = sign < 0; // black pieces need mirror
    for (final sq in squares) {
      final idx = needMirror ? _mirror(sq) : sq;
      mgScore += sign * (mgVal + mgTable[idx]);
      egScore += sign * (egVal + egTable[idx]);
      phase += pw;
    }
  }

  // Material + PST (one loop per piece type, no board scanning)
  _addPst(snap.whitePawns, chess.PieceType.PAWN, 1);
  _addPst(snap.blackPawns, chess.PieceType.PAWN, -1);
  _addPst(snap.whiteKnights, chess.PieceType.KNIGHT, 1);
  _addPst(snap.blackKnights, chess.PieceType.KNIGHT, -1);
  _addPst(snap.whiteBishops, chess.PieceType.BISHOP, 1);
  _addPst(snap.blackBishops, chess.PieceType.BISHOP, -1);
  _addPst(snap.whiteRooks, chess.PieceType.ROOK, 1);
  _addPst(snap.blackRooks, chess.PieceType.ROOK, -1);
  _addPst(snap.whiteQueens, chess.PieceType.QUEEN, 1);
  _addPst(snap.blackQueens, chess.PieceType.QUEEN, -1);
  // Kings
  {
    final mgTable = mgPst[chess.PieceType.KING]!;
    final egTable = egPst[chess.PieceType.KING]!;
    mgScore += mgTable[snap.whiteKing];
    egScore += egTable[snap.whiteKing];
    mgScore -= mgTable[_mirror(snap.blackKing)];
    egScore -= egTable[_mirror(snap.blackKing)];
  }

  // Pawn structure
  for (int side = 0; side < 2; side++) {
    final isWhite = side == 0;
    final sign = isWhite ? 1 : -1;
    final pawns = snap.pawns(isWhite);
    final enemyPawns = snap.pawns(!isWhite);

    for (final sq in pawns) {
      final f = _squareFile(sq);
      final r = _squareRank(sq);

      // Doubled
      for (final s in pawns) {
        if (s != sq && _squareFile(s) == f) {
          egScore += sign * doubledPawnPenalty;
          break;
        }
      }

      // Isolated
      bool hasNeighbor = false;
      for (final s in pawns) {
        if (s != sq) {
          final sf = _squareFile(s);
          if (sf == f - 1 || sf == f + 1) {
            hasNeighbor = true;
            break;
          }
        }
      }
      if (!hasNeighbor) {
        mgScore += sign * isolatedPawnPenalty;
        egScore += sign * isolatedPawnPenalty;
      }

      // Passed
      bool isPassed = true;
      for (final epSq in enemyPawns) {
        final epF = _squareFile(epSq);
        final epR = _squareRank(epSq);
        if ((epF - f).abs() <= 1) {
          if (isWhite && epR > r) {
            isPassed = false;
            break;
          }
          if (!isWhite && epR < r) {
            isPassed = false;
            break;
          }
        }
      }
      if (isPassed) {
        final effectiveRank = isWhite ? r : (7 - r);
        mgScore += sign * passedPawnBonusMg[effectiveRank];
        egScore += sign * passedPawnBonusEg[effectiveRank];
      }
    }
  }

  // Bishop pair
  if (snap.whiteBishops.length >= 2) {
    mgScore += bishopPairBonus;
    egScore += bishopPairBonus;
  }
  if (snap.blackBishops.length >= 2) {
    mgScore -= bishopPairBonus;
    egScore -= bishopPairBonus;
  }

  // Rook on open files
  for (int side = 0; side < 2; side++) {
    final isWhite = side == 0;
    final sign = isWhite ? 1 : -1;
    for (final sq in snap.rooks(isWhite)) {
      final f = _squareFile(sq);
      bool ownPawnOnFile = false;
      bool enemyPawnOnFile = false;
      for (final ps in snap.pawns(isWhite)) {
        if (_squareFile(ps) == f) {
          ownPawnOnFile = true;
          break;
        }
      }
      if (!ownPawnOnFile) {
        for (final ps in snap.pawns(!isWhite)) {
          if (_squareFile(ps) == f) {
            enemyPawnOnFile = true;
            break;
          }
        }
        if (!enemyPawnOnFile) {
          mgScore += sign * rookOpenFileBonus;
        } else {
          mgScore += sign * rookSemiOpenFileBonus;
        }
      }
    }
  }

  // King pawn shield (midgame only)
  if (phase > 6) {
    for (int side = 0; side < 2; side++) {
      final isWhite = side == 0;
      final sign = isWhite ? 1 : -1;
      final kingSq = snap.king(isWhite);
      final kf = _squareFile(kingSq);
      final kr = _squareRank(kingSq);
      for (final ps in snap.pawns(isWhite)) {
        final pf = _squareFile(ps);
        final pr = _squareRank(ps);
        if ((pf - kf).abs() <= 1) {
          if (isWhite && (pr == kr + 1 || pr == kr + 2))
            mgScore += sign * kingShieldBonus;
          if (!isWhite && (pr == kr - 1 || pr == kr - 2))
            mgScore += sign * kingShieldBonus;
        }
      }
    }
  }

  // Tapered evaluation
  final cp = phase > totalPhase ? totalPhase : phase;
  int score = (mgScore * cp + egScore * (totalPhase - cp)) ~/ totalPhase;

  // Endgame mop-up
  final wMat = snap.material(true);
  final bMat = snap.material(false);
  final matAdv = wMat - bMat;
  if (matAdv.abs() >= 200) {
    final winWhite = matAdv > 0;
    final sign = winWhite ? 1 : -1;
    final losingKing = snap.king(!winWhite);
    final winningKing = snap.king(winWhite);
    final edge = _kingEdgeDistance(losingKing) * 15;
    final prox = (14 - _chebyshevDistance(winningKing, losingKing)) * 8;
    final scale = (matAdv.abs() ~/ 100).clamp(0, 10);
    score += sign * ((edge + prox) * scale ~/ 5);
  }

  return score;
}
