import 'package:chess/chess.dart' as chess;
import 'difficulty.dart';

/// Tracks the state of a chess game in progress.
class GameState {
  final chess.Chess board;
  final Difficulty difficulty;
  final bool playerIsWhite;
  final List<String> moveHistory;
  final List<String> capturedByWhite; // pieces white has captured
  final List<String> capturedByBlack; // pieces black has captured
  bool isEngineThinking;

  GameState({
    required this.difficulty,
    required this.playerIsWhite,
    chess.Chess? board,
    String? fen,
  }) : board =
           board ?? (fen != null ? chess.Chess.fromFEN(fen) : chess.Chess()),
       moveHistory = [],
       capturedByWhite = [],
       capturedByBlack = [],
       isEngineThinking = false;

  bool get isPlayerTurn =>
      (playerIsWhite && board.turn == chess.Color.WHITE) ||
      (!playerIsWhite && board.turn == chess.Color.BLACK);

  bool get isGameOver => board.game_over;

  String get statusText {
    if (board.in_checkmate) {
      final winner = board.turn == chess.Color.WHITE ? 'Black' : 'White';
      return 'Checkmate! $winner wins';
    }
    if (board.in_stalemate) return 'Stalemate — Draw';
    if (board.in_threefold_repetition) return 'Draw by repetition';
    if (board.insufficient_material) return 'Draw — Insufficient material';
    if (board.in_draw) return 'Draw';
    if (board.in_check) {
      final checked = board.turn == chess.Color.WHITE ? 'White' : 'Black';
      return '$checked is in check!';
    }
    if (isEngineThinking) return 'Engine is thinking...';
    return isPlayerTurn ? 'Your turn' : 'Engine\'s turn';
  }

  String get resultText {
    if (board.in_checkmate) {
      final winner = board.turn == chess.Color.WHITE ? 'Black' : 'White';
      if ((winner == 'White' && playerIsWhite) ||
          (winner == 'Black' && !playerIsWhite)) {
        return 'You Win! 🎉';
      }
      return 'You Lose 😔';
    }
    return 'Draw 🤝';
  }
}
