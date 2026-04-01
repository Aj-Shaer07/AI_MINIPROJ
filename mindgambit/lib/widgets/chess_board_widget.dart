import 'package:flutter/material.dart';
import 'package:chess/chess.dart' as chess;
import '../theme/app_colors.dart';
import '../core/constants.dart';

/// Interactive chessboard widget with tap-to-move, highlights, and coordinate labels.
class ChessBoardWidget extends StatelessWidget {
  final chess.Chess board;
  final bool boardFlipped;
  final int? selectedSquare;
  final List<chess.Move> legalMoves;
  final chess.Move? lastMove;
  final ValueChanged<int> onSquareTapped;
  final bool enabled;

  const ChessBoardWidget({
    super.key,
    required this.board,
    required this.boardFlipped,
    required this.selectedSquare,
    required this.legalMoves,
    required this.lastMove,
    required this.onSquareTapped,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    // Precompute sets to cut per-square work during rebuilds.
    final legalTargets = <int>{
      for (final m in legalMoves) _algebraicToIndex(m.toAlgebraic),
    };
    final lastFrom = lastMove != null
        ? _algebraicToIndex(lastMove!.fromAlgebraic)
        : null;
    final lastTo = lastMove != null
        ? _algebraicToIndex(lastMove!.toAlgebraic)
        : null;
    final inCheck = board.in_check;

    return AspectRatio(
      aspectRatio: 1.0,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final boardSize = constraints.maxWidth;
          final squareSize = boardSize / 8;

          return Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primary.withValues(alpha: 0.15),
                  blurRadius: 20,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Column(
                children: List.generate(8, (row) {
                  return Row(
                    children: List.generate(8, (col) {
                      final displayRow = boardFlipped ? 7 - row : row;
                      final displayCol = boardFlipped ? 7 - col : col;
                      final squareIndex = (7 - displayRow) * 8 + displayCol;
                      final isLight = (displayRow + displayCol) % 2 == 0;

                      return _buildSquare(
                        squareIndex: squareIndex,
                        displayRow: displayRow,
                        displayCol: displayCol,
                        isLight: isLight,
                        squareSize: squareSize,
                        row: row,
                        col: col,
                        legalTargets: legalTargets,
                        lastFrom: lastFrom,
                        lastTo: lastTo,
                        inCheck: inCheck,
                      );
                    }),
                  );
                }),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildSquare({
    required int squareIndex,
    required int displayRow,
    required int displayCol,
    required bool isLight,
    required double squareSize,
    required int row,
    required int col,
    required Set<int> legalTargets,
    required int? lastFrom,
    required int? lastTo,
    required bool inCheck,
  }) {
    Color bgColor = isLight ? AppColors.boardLight : AppColors.boardDark;

    // Last move highlight
    if (lastFrom != null &&
        (squareIndex == lastFrom || squareIndex == lastTo)) {
      bgColor = Color.lerp(bgColor, AppColors.primary, 0.3)!;
    }

    // Selected square highlight
    final isSelected = selectedSquare == squareIndex;
    if (isSelected) {
      bgColor = Color.lerp(bgColor, AppColors.accent, 0.4)!;
    }

    // Check highlight
    final sqName = _indexToAlgebraic(squareIndex);
    final pieceAtSquare = board.get(sqName);

    if (inCheck) {
      final kingColor = board.turn;
      if (pieceAtSquare != null &&
          pieceAtSquare.type == chess.PieceType.KING &&
          pieceAtSquare.color == kingColor) {
        bgColor = Color.lerp(bgColor, AppColors.boardCheck, 0.6)!;
      }
    }

    // Legal move indicator
    final isLegalTarget = legalTargets.contains(squareIndex);

    return GestureDetector(
      onTap: enabled ? () => onSquareTapped(squareIndex) : null,
      child: Container(
        width: squareSize,
        height: squareSize,
        color: bgColor,
        child: Stack(
          children: [
            // Coordinate labels
            if (col == 0)
              Positioned(
                top: 2,
                left: 2,
                child: Text(
                  '${8 - (boardFlipped ? 7 - row : row)}',
                  style: TextStyle(
                    fontSize: squareSize * 0.15,
                    color: isLight ? AppColors.boardDark : AppColors.boardLight,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            if (row == 7)
              Positioned(
                bottom: 1,
                right: 3,
                child: Text(
                  String.fromCharCode(
                    'a'.codeUnitAt(0) + (boardFlipped ? 7 - col : col),
                  ),
                  style: TextStyle(
                    fontSize: squareSize * 0.15,
                    color: isLight ? AppColors.boardDark : AppColors.boardLight,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),

            // Piece
            if (pieceAtSquare != null)
              Center(child: _buildPiece(pieceAtSquare, squareSize)),

            // Legal move dot or capture ring
            if (isLegalTarget)
              Center(
                child: pieceAtSquare != null
                    ? Container(
                        width: squareSize * 0.85,
                        height: squareSize * 0.85,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: AppColors.captureRing,
                            width: squareSize * 0.06,
                          ),
                        ),
                      )
                    : Container(
                        width: squareSize * 0.28,
                        height: squareSize * 0.28,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.moveDot,
                        ),
                      ),
              ),
          ],
        ),
      ),
    );
  }

  /// Build a piece widget with clear black/white distinction and Android optimizations.
  Widget _buildPiece(chess.Piece piece, double squareSize) {
    final isWhite = piece.color == chess.Color.WHITE;
    final symbol = ChessPieces.getSymbol(piece.type.toString(), isWhite);
    final fontSize = squareSize * 0.75; // Standard size for better clarity

    // Two-pass text render: crisp outline + fill for reliable contrast.
    return Stack(
      alignment: Alignment.center,
      children: [
        // Outline pass (stroke)
        Text(
          symbol,
          textAlign: TextAlign.center,
          style: ChessPieces.getPieceOutlineStyle(
            fontSize: fontSize,
            isWhite: isWhite,
          ),
        ),
        // Fill pass (solid color)
        Text(
          symbol,
          textAlign: TextAlign.center,
          style: ChessPieces.getPieceStyle(
            fontSize: fontSize,
            isWhite: isWhite,
          ),
        ),
      ],
    );
  }

  int _algebraicToIndex(String algebraic) {
    final file = algebraic.codeUnitAt(0) - 'a'.codeUnitAt(0);
    final rank = algebraic.codeUnitAt(1) - '1'.codeUnitAt(0);
    return rank * 8 + file;
  }

  String _indexToAlgebraic(int index) {
    final file = index % 8;
    final rank = index ~/ 8;
    return String.fromCharCode('a'.codeUnitAt(0) + file) +
        String.fromCharCode('1'.codeUnitAt(0) + rank);
  }
}
