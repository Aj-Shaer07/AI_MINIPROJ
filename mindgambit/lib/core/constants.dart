import 'package:flutter/material.dart';

/// Unicode chess piece symbols with Android compatibility optimizations.
class ChessPieces {
  ChessPieces._();

  // White outlined pieces (U+2654-2659)
  static const String whiteKing = '♔';
  static const String whiteQueen = '♕';
  static const String whiteRook = '♖';
  static const String whiteBishop = '♗';
  static const String whiteKnight = '♘';
  static const String whitePawn = '♙'; // White pawn - outlined

  // Black filled pieces (U+265A-265F)
  static const String blackKing = '♚';
  static const String blackQueen = '♛';
  static const String blackRook = '♜';
  static const String blackBishop = '♝';
  static const String blackKnight = '♞';
  static const String blackPawn = '♟'; // Black pawn - filled

  /// Get unicode symbol for a piece type string (from chess package: p/n/b/r/q/k) and color.
  static String getSymbol(String pieceType, bool isWhite) {
    switch (pieceType.toLowerCase()) {
      case 'k':
        return isWhite ? whiteKing : blackKing;
      case 'q':
        return isWhite ? whiteQueen : blackQueen;
      case 'r':
        return isWhite ? whiteRook : blackRook;
      case 'b':
        return isWhite ? whiteBishop : blackBishop;
      case 'n':
        return isWhite ? whiteKnight : blackKnight;
      case 'p':
        return isWhite ? whitePawn : blackPawn;
      default:
        return '?';
    }
  }

  /// Get piece value for captured piece display ordering.
  static int getValue(String pieceType) {
    switch (pieceType.toLowerCase()) {
      case 'q':
        return 9;
      case 'r':
        return 5;
      case 'b':
        return 3;
      case 'n':
        return 3;
      case 'p':
        return 1;
      default:
        return 0;
    }
  }

  /// Get optimized TextStyle for chess pieces with Android compatibility.
  /// Ensures consistent rendering across devices with proper font fallbacks.
  static TextStyle getPieceStyle({
    required double fontSize,
    required bool isWhite,
  }) {
    final fillColor = isWhite
        ? const Color(0xFFF7F7F7)
        : const Color(0xFF121212);

    return TextStyle(
      fontSize: fontSize,
      height: 1.0,
      color: fillColor,
      fontWeight: FontWeight.bold,
      letterSpacing: 0.0,
    );
  }

  /// Get optimized TextStyle with stroke for chess pieces (outline effect).
  static TextStyle getPieceOutlineStyle({
    required double fontSize,
    required bool isWhite,
  }) {
    final outlineColor = isWhite
        ? const Color(0xFF1E1E1E)
        : const Color(0xFFE7D7BA);

    return TextStyle(
      fontSize: fontSize,
      height: 1.0,
      fontWeight: FontWeight.bold,
      letterSpacing: 0.0,
      foreground: Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2
        ..color = outlineColor,
    );
  }
}
