import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../theme/app_colors.dart';

/// Displays captured pieces for a side.
class CapturedPiecesBar extends StatelessWidget {
  final List<String> capturedPieces;
  final bool isWhitePieces;

  const CapturedPiecesBar({
    super.key,
    required this.capturedPieces,
    required this.isWhitePieces,
  });

  @override
  Widget build(BuildContext context) {
    if (capturedPieces.isEmpty) {
      return const SizedBox(height: 24);
    }

    // Sort by value descending
    final sorted = List<String>.from(capturedPieces)
      ..sort(
        (a, b) => ChessPieces.getValue(b).compareTo(ChessPieces.getValue(a)),
      );

    return SizedBox(
      height: 24,
      child: Row(
        children: sorted.map((p) {
          return Padding(
            padding: const EdgeInsets.only(right: 2),
            child: Text(
              ChessPieces.getSymbol(p, isWhitePieces),
              style: TextStyle(
                fontSize: 18,
                color: AppColors.textSecondary.withValues(alpha: 0.8),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
