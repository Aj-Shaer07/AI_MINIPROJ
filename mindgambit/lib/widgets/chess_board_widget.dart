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
  }) {
    Color bgColor = isLight ? AppColors.boardLight : AppColors.boardDark;

    // Last move highlight
    if (lastMove != null) {
      final fromSq = _algebraicToIndex(lastMove!.fromAlgebraic);
      final toSq = _algebraicToIndex(lastMove!.toAlgebraic);
      if (squareIndex == fromSq || squareIndex == toSq) {
        bgColor = Color.lerp(bgColor, AppColors.primary, 0.3)!;
      }
    }

    // Selected square highlight
    final isSelected = selectedSquare == squareIndex;
    if (isSelected) {
      bgColor = Color.lerp(bgColor, AppColors.accent, 0.4)!;
    }

    // Check highlight
    final sqName = _indexToAlgebraic(squareIndex);
    final pieceAtSquare = board.get(sqName);

    if (board.in_check) {
      final kingColor = board.turn;
      if (pieceAtSquare != null &&
          pieceAtSquare.type == chess.PieceType.KING &&
          pieceAtSquare.color == kingColor) {
        bgColor = Color.lerp(bgColor, AppColors.boardCheck, 0.6)!;
      }
    }

    // Legal move indicator
    final isLegalTarget = legalMoves.any(
      (m) => _algebraicToIndex(m.toAlgebraic) == squareIndex,
    );

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

  /// Build a piece widget with clear black/white distinction.
  Widget _buildPiece(chess.Piece piece, double squareSize) {
    final isWhite = piece.color == chess.Color.WHITE;
    final symbol = ChessPieces.getSymbol(piece.type.toString(), isWhite);

    // White pieces: white fill with dark outline
    // Black pieces: dark fill with lighter outline
    return Stack(
      alignment: Alignment.center,
      children: [
        // Shadow/outline layer
        Text(
          symbol,
          style: TextStyle(
            fontSize: squareSize * 0.72,
            height: 1.0,
            foreground: Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = 1.5
              ..color = isWhite ? Colors.black87 : Colors.black54,
          ),
        ),
        // Fill layer
        Text(
          symbol,
          style: TextStyle(
            fontSize: squareSize * 0.72,
            height: 1.0,
            color: isWhite ? Colors.white : Colors.black87,
            shadows: [
              Shadow(
                color: Colors.black.withValues(alpha: 0.4),
                offset: const Offset(1, 1),
                blurRadius: 3,
              ),
            ],
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
