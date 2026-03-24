import 'package:chess/chess.dart' as chess;
import 'difficulty.dart';

/// Tracks the state of a chess game in progress.
class GameState {
  final chess.Chess board;
  final Difficulty difficulty;
  final bool playerIsWhite;
  final String initialFen; // Store the initial fen to reconstruct history
  final List<String> moveHistory;
  final List<chess.Move> moveHistoryObjects; // Store actual moves for playback
  final List<String> capturedByWhite; // pieces white has captured
  final List<String> capturedByBlack; // pieces black has captured
  bool isEngineThinking;

  // Coach and Analysis metadata
  final List<String?> moveCategories;
  final List<String?> moveComments;
  final List<List<Map<String, dynamic>>?> moveAlternatives;

  GameState({
    required this.difficulty,
    required this.playerIsWhite,
    chess.Chess? board,
    String? fen,
  }) : board =
           board ?? (fen != null ? chess.Chess.fromFEN(fen) : chess.Chess()),
       initialFen = fen ?? chess.Chess.DEFAULT_POSITION,
       moveHistory = [],
       moveHistoryObjects = [],
       capturedByWhite = [],
       capturedByBlack = [],
       isEngineThinking = false,
       moveCategories = [],
       moveComments = [],
       moveAlternatives = [];

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

  /// Reconstructs the board state up to a specific move index.
  /// Index is 0-based and corresponds to the length of moves applied.
  /// If index == moveHistoryObjects.length, it returns current state.
  chess.Chess getBoardAtMove(int index) {
    if (index < 0 || index > moveHistoryObjects.length) {
      return chess.Chess.fromFEN(board.fen); // Fallback
    }
    final reviewBoard = chess.Chess.fromFEN(initialFen);
    for (int i = 0; i < index; i++) {
        reviewBoard.move(moveHistoryObjects[i]);
    }
    return reviewBoard;
  }
}
