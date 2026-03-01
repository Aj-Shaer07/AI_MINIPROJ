import 'package:flutter/material.dart';

import 'package:chess/chess.dart' as chess;
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../models/difficulty.dart';
import '../models/game_state.dart';
import '../engine/engine.dart';
import '../widgets/chess_board_widget.dart';
import '../widgets/promotion_dialog.dart';
import '../widgets/move_history_panel.dart';
import '../widgets/captured_pieces_bar.dart';
import '../widgets/eval_bar.dart';
import '../widgets/game_controls.dart';

/// Main game screen — responsive for portrait and landscape.
class GameScreen extends StatefulWidget {
  final Difficulty difficulty;
  final bool playerIsWhite;

  const GameScreen({
    super.key,
    required this.difficulty,
    required this.playerIsWhite,
  });

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  late GameState _gameState;
  int? _selectedSquare;
  List<chess.Move> _legalMoves = [];
  chess.Move? _lastMove;
  bool _boardFlipped = false;
  int _evalCp = 0;
  final ScrollController _moveScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _gameState = GameState(
      difficulty: widget.difficulty,
      playerIsWhite: widget.playerIsWhite,
    );
    _boardFlipped = !widget.playerIsWhite;

    // If engine moves first, trigger it
    if (!_gameState.isPlayerTurn && !_gameState.isGameOver) {
      _scheduleEngineMove();
    }
  }

  @override
  void dispose() {
    _moveScrollController.dispose();
    super.dispose();
  }

  void _onSquareTapped(int squareIndex) {
    if (_gameState.isGameOver || _gameState.isEngineThinking) return;
    if (!_gameState.isPlayerTurn) return;

    final sqName = _indexToAlgebraic(squareIndex);
    final piece = _gameState.board.get(sqName);

    if (_selectedSquare != null) {
      // Try to make a move
      final fromSq = _indexToAlgebraic(_selectedSquare!);
      final toSq = sqName;

      // Check if it's a promotion move
      final fromPiece = _gameState.board.get(fromSq);
      final isPromotion =
          fromPiece != null &&
          fromPiece.type == chess.PieceType.PAWN &&
          ((fromPiece.color == chess.Color.WHITE && toSq[1] == '8') ||
              (fromPiece.color == chess.Color.BLACK && toSq[1] == '1'));

      if (isPromotion) {
        _handlePromotion(fromSq, toSq);
        return;
      }

      final success = _tryMove(fromSq, toSq);
      if (success) {
        setState(() {
          _selectedSquare = null;
          _legalMoves = [];
        });
        return;
      }

      // If tapped own piece, select it instead
      if (piece != null && piece.color == _gameState.board.turn) {
        _selectSquare(squareIndex);
        return;
      }

      setState(() {
        _selectedSquare = null;
        _legalMoves = [];
      });
    } else {
      // Select piece
      if (piece != null && piece.color == _gameState.board.turn) {
        _selectSquare(squareIndex);
      }
    }
  }

  void _selectSquare(int squareIndex) {
    final sqName = _indexToAlgebraic(squareIndex);
    final moves = _gameState.board
        .generate_moves()
        .where((m) => m.fromAlgebraic == sqName)
        .toList();

    setState(() {
      _selectedSquare = squareIndex;
      _legalMoves = moves;
    });
  }

  Future<void> _handlePromotion(String fromSq, String toSq) async {
    final isWhite = _gameState.board.turn == chess.Color.WHITE;
    final promo = await showPromotionDialog(context, isWhite);
    if (promo == null) return;

    chess.PieceType promoType;
    switch (promo) {
      case 'q':
        promoType = chess.PieceType.QUEEN;
      case 'r':
        promoType = chess.PieceType.ROOK;
      case 'b':
        promoType = chess.PieceType.BISHOP;
      case 'n':
        promoType = chess.PieceType.KNIGHT;
      default:
        promoType = chess.PieceType.QUEEN;
    }

    final move = _gameState.board
        .generate_moves()
        .where(
          (m) =>
              m.fromAlgebraic == fromSq &&
              m.toAlgebraic == toSq &&
              m.promotion == promoType,
        )
        .firstOrNull;

    if (move != null) {
      _executeMove(move);
    }

    setState(() {
      _selectedSquare = null;
      _legalMoves = [];
    });
  }

  bool _tryMove(String fromSq, String toSq) {
    final move = _gameState.board
        .generate_moves()
        .where(
          (m) =>
              m.fromAlgebraic == fromSq &&
              m.toAlgebraic == toSq &&
              m.promotion == null,
        )
        .firstOrNull;

    if (move == null) return false;
    _executeMove(move);
    return true;
  }

  void _executeMove(chess.Move move) {
    // Track captured piece
    final captured = _gameState.board.get(move.toAlgebraic);
    if (captured != null) {
      if (captured.color == chess.Color.WHITE) {
        _gameState.capturedByBlack.add(captured.type.toString());
      } else {
        _gameState.capturedByWhite.add(captured.type.toString());
      }
    }
    // En passant capture
    if (move.flags & chess.Chess.BITS_EP_CAPTURE != 0) {
      final pawnColor = _gameState.board.turn == chess.Color.WHITE
          ? chess.Color.BLACK
          : chess.Color.WHITE;
      if (pawnColor == chess.Color.WHITE) {
        _gameState.capturedByBlack.add('p');
      } else {
        _gameState.capturedByWhite.add('p');
      }
    }

    final san = _gameState.board.move_to_san(move);
    _gameState.board.move(move);
    _gameState.moveHistory.add(san);

    setState(() {
      _lastMove = move;
    });

    _scrollMoveHistory();

    if (!_gameState.isGameOver && !_gameState.isPlayerTurn) {
      _scheduleEngineMove();
    }

    if (_gameState.isGameOver) {
      _showGameOverDialog();
    }
  }

  void _scheduleEngineMove() {
    setState(() => _gameState.isEngineThinking = true);

    Future.delayed(const Duration(milliseconds: 100), () async {
      try {
        debugPrint(
          '[GameScreen] Engine thinking... FEN: ${_gameState.board.fen}',
        );
        final result = await ChessEngine.findBestMove(
          fen: _gameState.board.fen,
          difficulty: _gameState.difficulty,
          engineIsBlack: _gameState.playerIsWhite,
        );

        debugPrint(
          '[GameScreen] Engine result: move=${result.bestMoveUci} eval=${result.evalCp} depth=${result.depth} nodes=${result.nodes} time=${result.timeMs}ms',
        );

        if (!mounted) return;

        if (result.hasMove) {
          final moveUci = result.bestMoveUci!;
          final fromSq = moveUci.substring(0, 2);
          final toSq = moveUci.substring(2, 4);
          chess.PieceType? promo;
          if (moveUci.length > 4) {
            switch (moveUci[4]) {
              case 'q':
                promo = chess.PieceType.QUEEN;
              case 'r':
                promo = chess.PieceType.ROOK;
              case 'b':
                promo = chess.PieceType.BISHOP;
              case 'n':
                promo = chess.PieceType.KNIGHT;
            }
          }

          // Try matching with specific promotion first, then without
          var move = _gameState.board
              .generate_moves()
              .where(
                (m) =>
                    m.fromAlgebraic == fromSq &&
                    m.toAlgebraic == toSq &&
                    m.promotion == promo,
              )
              .firstOrNull;

          // Fallback: try matching just from/to without promotion filter
          move ??= _gameState.board
              .generate_moves()
              .where((m) => m.fromAlgebraic == fromSq && m.toAlgebraic == toSq)
              .firstOrNull;

          debugPrint(
            '[GameScreen] Found legal move: ${move != null} from=$fromSq to=$toSq promo=$promo',
          );

          if (move != null) {
            // Track captured piece
            final captured = _gameState.board.get(move.toAlgebraic);
            if (captured != null) {
              if (captured.color == chess.Color.WHITE) {
                _gameState.capturedByBlack.add(captured.type.toString());
              } else {
                _gameState.capturedByWhite.add(captured.type.toString());
              }
            }

            final san = _gameState.board.move_to_san(move);
            _gameState.board.move(move);
            _gameState.moveHistory.add(san);

            setState(() {
              _lastMove = move;
              _evalCp = result.evalCp;
              _gameState.isEngineThinking = false;
            });

            _scrollMoveHistory();

            if (_gameState.isGameOver) {
              _showGameOverDialog();
            }
          } else {
            debugPrint(
              '[GameScreen] ERROR: Could not find legal move for engine result: $moveUci',
            );
            debugPrint(
              '[GameScreen] Available moves: ${_gameState.board.generate_moves().map((m) => "${m.fromAlgebraic}${m.toAlgebraic}").toList()}',
            );
            setState(() => _gameState.isEngineThinking = false);
          }
        } else {
          debugPrint('[GameScreen] Engine returned no move');
          setState(() => _gameState.isEngineThinking = false);
        }
      } catch (e, stackTrace) {
        debugPrint('[GameScreen] ENGINE ERROR: $e');
        debugPrint('[GameScreen] Stack: $stackTrace');
        if (mounted) {
          setState(() => _gameState.isEngineThinking = false);
        }
      }
    });
  }

  void _scrollMoveHistory() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_moveScrollController.hasClients) {
        _moveScrollController.animateTo(
          _moveScrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showGameOverDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          'Game Over',
          style: AppTextStyles.headlineMedium,
          textAlign: TextAlign.center,
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _gameState.resultText,
              style: AppTextStyles.displayMedium.copyWith(
                color: AppColors.primary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              _gameState.statusText,
              style: AppTextStyles.bodyMedium,
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              _newGame();
            },
            child: Text('New Game', style: TextStyle(color: AppColors.primary)),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.of(context).popUntil((route) => route.isFirst);
            },
            child: Text(
              'Home',
              style: TextStyle(color: AppColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  void _newGame() {
    setState(() {
      _gameState = GameState(
        difficulty: widget.difficulty,
        playerIsWhite: widget.playerIsWhite,
      );
      _selectedSquare = null;
      _legalMoves = [];
      _lastMove = null;
      _evalCp = 0;
    });

    if (!_gameState.isPlayerTurn && !_gameState.isGameOver) {
      _scheduleEngineMove();
    }
  }

  void _undoMove() {
    if (_gameState.moveHistory.length < 2) return;
    // Undo both engine and player move
    _gameState.board.undo_move();
    _gameState.board.undo_move();
    if (_gameState.moveHistory.length >= 2) {
      _gameState.moveHistory.removeLast();
      _gameState.moveHistory.removeLast();
    }
    setState(() {
      _selectedSquare = null;
      _legalMoves = [];
      _lastMove = null;
    });
  }

  void _resign() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text('Resign?', style: AppTextStyles.headlineMedium),
        content: Text(
          'Are you sure you want to resign?',
          style: AppTextStyles.bodyMedium,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              'Cancel',
              style: TextStyle(color: AppColors.textSecondary),
            ),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              Navigator.of(context).popUntil((route) => route.isFirst);
            },
            child: Text('Resign', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }

  String _indexToAlgebraic(int index) {
    final file = index % 8;
    final rank = index ~/ 8;
    return String.fromCharCode('a'.codeUnitAt(0) + file) +
        String.fromCharCode('1'.codeUnitAt(0) + rank);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppColors.backgroundGradient),
        child: SafeArea(
          child: OrientationBuilder(
            builder: (context, orientation) {
              if (orientation == Orientation.landscape) {
                return _buildLandscapeLayout();
              }
              return _buildPortraitLayout();
            },
          ),
        ),
      ),
    );
  }

  Widget _buildPortraitLayout() {
    return Column(
      children: [
        // Top bar
        _buildTopBar(),

        // Status
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Text(
            _gameState.statusText,
            style: AppTextStyles.bodyMedium.copyWith(
              color: _gameState.board.in_check
                  ? AppColors.error
                  : AppColors.textSecondary,
            ),
          ),
        ),

        // Eval bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: EvalBar(evalCp: _evalCp),
        ),
        const SizedBox(height: 8),

        // Captured pieces (opponent)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: CapturedPiecesBar(
            capturedPieces: widget.playerIsWhite
                ? _gameState.capturedByBlack
                : _gameState.capturedByWhite,
            isWhitePieces: !widget.playerIsWhite,
          ),
        ),

        // Chessboard
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: ChessBoardWidget(
            board: _gameState.board,
            boardFlipped: _boardFlipped,
            selectedSquare: _selectedSquare,
            legalMoves: _legalMoves,
            lastMove: _lastMove,
            onSquareTapped: _onSquareTapped,
            enabled: _gameState.isPlayerTurn && !_gameState.isEngineThinking,
          ),
        ),

        // Captured pieces (player)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: CapturedPiecesBar(
            capturedPieces: widget.playerIsWhite
                ? _gameState.capturedByWhite
                : _gameState.capturedByBlack,
            isWhitePieces: widget.playerIsWhite,
          ),
        ),

        const SizedBox(height: 8),

        // Move history
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: MoveHistoryPanel(
              moves: _gameState.moveHistory,
              scrollController: _moveScrollController,
            ),
          ),
        ),

        const SizedBox(height: 8),

        // Controls
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: GameControls(
            onNewGame: _newGame,
            onUndo: _undoMove,
            onResign: _resign,
            onFlipBoard: () => setState(() => _boardFlipped = !_boardFlipped),
            canUndo:
                _gameState.moveHistory.length >= 2 &&
                !_gameState.isEngineThinking,
            gameOver: _gameState.isGameOver,
          ),
        ),
      ],
    );
  }

  Widget _buildLandscapeLayout() {
    return Row(
      children: [
        // Left: eval bar + board
        Expanded(
          flex: 5,
          child: Row(
            children: [
              // Vertical eval bar
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 16,
                ),
                child: EvalBar(evalCp: _evalCp, isVertical: true),
              ),
              // Board
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CapturedPiecesBar(
                        capturedPieces: widget.playerIsWhite
                            ? _gameState.capturedByBlack
                            : _gameState.capturedByWhite,
                        isWhitePieces: !widget.playerIsWhite,
                      ),
                      Flexible(
                        child: ChessBoardWidget(
                          board: _gameState.board,
                          boardFlipped: _boardFlipped,
                          selectedSquare: _selectedSquare,
                          legalMoves: _legalMoves,
                          lastMove: _lastMove,
                          onSquareTapped: _onSquareTapped,
                          enabled:
                              _gameState.isPlayerTurn &&
                              !_gameState.isEngineThinking,
                        ),
                      ),
                      CapturedPiecesBar(
                        capturedPieces: widget.playerIsWhite
                            ? _gameState.capturedByWhite
                            : _gameState.capturedByBlack,
                        isWhitePieces: widget.playerIsWhite,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),

        // Right: info panel
        Expanded(
          flex: 3,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                // Status + difficulty
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.arrow_back_ios, size: 20),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          widget.difficulty.label,
                          style: AppTextStyles.labelLarge,
                        ),
                        Text(
                          _gameState.statusText,
                          style: AppTextStyles.bodySmall.copyWith(
                            color: _gameState.board.in_check
                                ? AppColors.error
                                : null,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 8),

                // Move history
                Expanded(
                  child: MoveHistoryPanel(
                    moves: _gameState.moveHistory,
                    scrollController: _moveScrollController,
                  ),
                ),
                const SizedBox(height: 8),

                // Controls
                GameControls(
                  onNewGame: _newGame,
                  onUndo: _undoMove,
                  onResign: _resign,
                  onFlipBoard: () =>
                      setState(() => _boardFlipped = !_boardFlipped),
                  canUndo:
                      _gameState.moveHistory.length >= 2 &&
                      !_gameState.isEngineThinking,
                  gameOver: _gameState.isGameOver,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTopBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 16, 0),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(
              Icons.arrow_back_ios,
              color: AppColors.textPrimary,
              size: 20,
            ),
          ),
          Expanded(
            child: Text(
              'MindGambit',
              style: AppTextStyles.titleLarge,
              textAlign: TextAlign.center,
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              widget.difficulty.label,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
