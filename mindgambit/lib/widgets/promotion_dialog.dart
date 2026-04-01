import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../core/constants.dart';

/// Dialog for selecting pawn promotion piece.
class PromotionDialog extends StatelessWidget {
  final bool isWhite;

  const PromotionDialog({super.key, required this.isWhite});

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Promote to',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildPieceButton(context, 'Q', 'q'),
                _buildPieceButton(context, 'R', 'r'),
                _buildPieceButton(context, 'B', 'b'),
                _buildPieceButton(context, 'N', 'n'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPieceButton(
    BuildContext context,
    String pieceChar,
    String returnValue,
  ) {
    return GestureDetector(
      onTap: () => Navigator.of(context).pop(returnValue),
      child: Container(
        width: 60,
        height: 60,
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
        ),
        child: Center(
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Outline
              Text(
                ChessPieces.getSymbol(pieceChar, isWhite),
                style: ChessPieces.getPieceOutlineStyle(
                  fontSize: 40,
                  isWhite: isWhite,
                ),
              ),
              // Fill
              Text(
                ChessPieces.getSymbol(pieceChar, isWhite),
                style: ChessPieces.getPieceStyle(
                  fontSize: 40,
                  isWhite: isWhite,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Show promotion dialog and return selected piece (q/r/b/n) or null.
Future<String?> showPromotionDialog(BuildContext context, bool isWhite) {
  return showDialog<String>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => PromotionDialog(isWhite: isWhite),
  );
}
