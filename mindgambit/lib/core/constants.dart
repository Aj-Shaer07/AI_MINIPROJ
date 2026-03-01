/// Unicode chess piece symbols.
class ChessPieces {
  ChessPieces._();

  // White outlined pieces (U+2654-2659)
  static const String whiteKing = '♔';
  static const String whiteQueen = '♕';
  static const String whiteRook = '♖';
  static const String whiteBishop = '♗';
  static const String whiteKnight = '♘';
  static const String whitePawn = '♙';

  // Black filled pieces (U+265A-265F)
  static const String blackKing = '♚';
  static const String blackQueen = '♛';
  static const String blackRook = '♜';
  static const String blackBishop = '♝';
  static const String blackKnight = '♞';
  static const String blackPawn = '♟';

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
}
