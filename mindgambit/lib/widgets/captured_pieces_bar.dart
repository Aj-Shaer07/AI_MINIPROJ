import 'package:flutter/material.dart';
import '../core/constants.dart';

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
          final symbol = ChessPieces.getSymbol(p, isWhitePieces);
          return Padding(
            padding: const EdgeInsets.only(right: 6),
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Outline for better visibility in small sizes
                Text(
                  symbol,
                  style: ChessPieces.getPieceOutlineStyle(
                    fontSize: 16,
                    isWhite: isWhitePieces,
                  ),
                ),
                // Fill
                Text(
                  symbol,
                  style: ChessPieces.getPieceStyle(
                    fontSize: 16,
                    isWhite: isWhitePieces,
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}
