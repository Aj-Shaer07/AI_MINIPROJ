import 'dart:async';
import 'package:flutter/material.dart';
import 'package:chess/chess.dart' as chess;
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../models/difficulty.dart';
import '../models/game_state.dart';
import '../engine/engine.dart';
import '../widgets/chess_board_widget.dart';
import '../widgets/promotion_dialog.dart';

/// Main game screen matching the "Chess AI" screenshot layout.
class GameScreen extends StatefulWidget {
  final Difficulty difficulty;
  final bool playerIsWhite;
  final int timerSeconds;
  final bool enableExplanation;
  final String? fen;

  const GameScreen({
    super.key,
    required this.difficulty,
    required this.playerIsWhite,
    this.timerSeconds = 0,
    this.enableExplanation = true,
    this.fen,
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
  Map<String, dynamic> _engineInfo = {};
  final ScrollController _moveScrollController = ScrollController();

  // Chess clock
  late int _whiteTimeLeft;
  late int _blackTimeLeft;
  Timer? _clockTimer;
  bool get _hasTimer => widget.timerSeconds > 0;

  @override
  void initState() {
    super.initState();
    _gameState = GameState(
      difficulty: widget.difficulty,
      playerIsWhite: widget.playerIsWhite,
      fen: widget.fen,
    );
    _boardFlipped = !widget.playerIsWhite;
    _whiteTimeLeft = widget.timerSeconds;
    _blackTimeLeft = widget.timerSeconds;

    if (_hasTimer) _startClock();

    if (!_gameState.isPlayerTurn && !_gameState.isGameOver) {
      _scheduleEngineMove();
    }
  }

  @override
  void dispose() {
    _clockTimer?.cancel();
    _moveScrollController.dispose();
    super.dispose();
  }

  // ─── Chess Clock ───────────────────────────────────────
  void _startClock() {
    _clockTimer?.cancel();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_gameState.isGameOver || _gameState.isEngineThinking) return;

      setState(() {
        if (_gameState.board.turn == chess.Color.WHITE) {
          _whiteTimeLeft--;
          if (_whiteTimeLeft <= 0) {
            _whiteTimeLeft = 0;
            _clockTimer?.cancel();
            _showTimeoutDialog(isWhite: true);
          }
        } else {
          _blackTimeLeft--;
          if (_blackTimeLeft <= 0) {
            _blackTimeLeft = 0;
            _clockTimer?.cancel();
            _showTimeoutDialog(isWhite: false);
          }
        }
      });
    });
  }

  void _showTimeoutDialog({required bool isWhite}) {
    final loser = isWhite ? 'White' : 'Black';
    final winner = isWhite ? 'Black' : 'White';
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          'Time\'s Up!',
          style: AppTextStyles.headlineMedium,
          textAlign: TextAlign.center,
        ),
        content: Text(
          '$loser ran out of time.\n$winner wins!',
          style: AppTextStyles.bodyMedium,
          textAlign: TextAlign.center,
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

  String _formatTime(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString()}:${s.toString().padLeft(2, '0')}';
  }

  // ─── Move Logic ────────────────────────────────────────
  void _onSquareTapped(int squareIndex) {
    if (_gameState.isGameOver || _gameState.isEngineThinking) return;
    if (!_gameState.isPlayerTurn) return;
    if (_hasTimer &&
        ((_gameState.board.turn == chess.Color.WHITE && _whiteTimeLeft <= 0) ||
            (_gameState.board.turn == chess.Color.BLACK &&
                _blackTimeLeft <= 0)))
      return;

    final sqName = _indexToAlgebraic(squareIndex);
    final piece = _gameState.board.get(sqName);

    if (_selectedSquare != null) {
      final fromSq = _indexToAlgebraic(_selectedSquare!);
      final toSq = sqName;
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

      if (piece != null && piece.color == _gameState.board.turn) {
        _selectSquare(squareIndex);
        return;
      }
      setState(() {
        _selectedSquare = null;
        _legalMoves = [];
      });
    } else {
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

    if (move != null) _executeMove(move);
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
    final captured = _gameState.board.get(move.toAlgebraic);
    if (captured != null) {
      if (captured.color == chess.Color.WHITE) {
        _gameState.capturedByBlack.add(captured.type.toString());
      } else {
        _gameState.capturedByWhite.add(captured.type.toString());
      }
    }
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
    if (_gameState.isGameOver) _showGameOverDialog();
  }

  void _scheduleEngineMove() {
    setState(() => _gameState.isEngineThinking = true);

    Future.delayed(const Duration(milliseconds: 100), () async {
      try {
        final result = await ChessEngine.findBestMove(
          fen: _gameState.board.fen,
          difficulty: _gameState.difficulty,
          engineIsBlack: _gameState.playerIsWhite,
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

          var move = _gameState.board
              .generate_moves()
              .where(
                (m) =>
                    m.fromAlgebraic == fromSq &&
                    m.toAlgebraic == toSq &&
                    m.promotion == promo,
              )
              .firstOrNull;
          move ??= _gameState.board
              .generate_moves()
              .where((m) => m.fromAlgebraic == fromSq && m.toAlgebraic == toSq)
              .firstOrNull;

          if (move != null) {
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
              _engineInfo = {
                'eval_cp': result.evalCp,
                'depth': result.depth,
                'time_ms': result.timeMs,
                'nodes': result.nodes,
                'explanation':
                    widget.enableExplanation ? result.explanation : null,
                'alternatives':
                    widget.enableExplanation ? result.alternatives : const [],
              };
              _gameState.isEngineThinking = false;
            });
            _scrollMoveHistory();
            if (_gameState.isGameOver) _showGameOverDialog();
          } else {
            setState(() => _gameState.isEngineThinking = false);
          }
        } else {
          setState(() => _gameState.isEngineThinking = false);
        }
      } catch (e) {
        debugPrint('[GameScreen] ENGINE ERROR: $e');
        if (mounted) setState(() => _gameState.isEngineThinking = false);
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
    _clockTimer?.cancel();
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
    _clockTimer?.cancel();
    setState(() {
      _gameState = GameState(
        difficulty: widget.difficulty,
        playerIsWhite: widget.playerIsWhite,
        fen: widget.fen,
      );
      _selectedSquare = null;
      _legalMoves = [];
      _lastMove = null;
      _evalCp = 0;
      _engineInfo = {};
      _whiteTimeLeft = widget.timerSeconds;
      _blackTimeLeft = widget.timerSeconds;
    });
    if (_hasTimer) _startClock();
    if (!_gameState.isPlayerTurn && !_gameState.isGameOver)
      _scheduleEngineMove();
  }

  void _undoMove() {
    if (_gameState.moveHistory.length < 2) return;
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
              _clockTimer?.cancel();
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

  // ─── Build ─────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppColors.backgroundGradient),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              // Use landscape-style layout for wide screens, portrait for narrow ones
              if (constraints.maxWidth > 800) {
                return _buildWideLayout(constraints);
              }
              return _buildNarrowLayout(constraints);
            },
          ),
        ),
      ),
    );
  }

  // ─── Wide (Desktop/Landscape) Layout ───────────────────
  Widget _buildWideLayout(BoxConstraints constraints) {
    final boardMaxSize =
        constraints.maxHeight - 120; // leave room for labels + timer
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildTitleBar(),
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Left: Board area with player labels
              Padding(
                padding: const EdgeInsets.only(left: 24, right: 16),
                child: SizedBox(
                  width: boardMaxSize.clamp(300, 640).toDouble(),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _buildPlayerLabel(isTop: true),
                      const SizedBox(height: 4),
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
                      const SizedBox(height: 4),
                      _buildPlayerLabel(isTop: false),
                    ],
                  ),
                ),
              ),

              // Right: Info panel
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(0, 16, 24, 16),
                  child: _buildInfoPanel(),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Narrow (Portrait) Layout ──────────────────────────
  Widget _buildNarrowLayout(BoxConstraints constraints) {
    final showExplainButton = widget.enableExplanation;

    return Column(
      children: [
        _buildTitleBar(),
        const SizedBox(height: 4),
        // Top player label
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildPlayerLabel(isTop: true),
        ),
        const SizedBox(height: 4),
        // Board
        Expanded(
          child: Padding(
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
        ),
        const SizedBox(height: 4),
        // Bottom player label
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildPlayerLabel(isTop: false),
        ),
        const SizedBox(height: 8),
        // Compact action bar
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: _buildCompactActions(showExplainButton: showExplainButton),
        ),
      ],
    );
  }

  // ─── Compact Action Bar (Phone) ────────────────────────
  Widget _buildCompactActions({required bool showExplainButton}) {
    return Row(
      children: [
        _compactBtn(Icons.history, 'History', _showHistorySheet),
        const SizedBox(width: 8),
        if (showExplainButton) ...[
          _compactBtn(
            Icons.lightbulb_outline,
            'Explain',
            _hasShortExplanation ? _showPortraitExplanationPopup : null,
            color: AppColors.primary,
          ),
          const SizedBox(width: 8),
        ],
        _compactBtn(
          Icons.undo,
          'Undo',
          _gameState.moveHistory.length >= 2 && !_gameState.isEngineThinking
              ? _undoMove
              : null,
        ),
        const SizedBox(width: 8),
        _compactBtn(
          Icons.flip,
          'Flip',
          () => setState(() => _boardFlipped = !_boardFlipped),
        ),
        const SizedBox(width: 8),
        if (!_gameState.isGameOver)
          _compactBtn(
            Icons.flag_outlined,
            'Resign',
            _resign,
            color: AppColors.error,
          ),
        if (_gameState.isGameOver)
          _compactBtn(Icons.add, 'New', _newGame, color: AppColors.accent),
      ],
    );
  }

  bool get _hasShortExplanation {
    if (!widget.enableExplanation) return false;
    final explanation = _engineInfo['explanation'];
    if (explanation is! Map<String, dynamic>) return false;
    final narrative = explanation['narrative'];
    return narrative is List && narrative.isNotEmpty;
  }

  void _showPortraitExplanationPopup() {
    final explanation = _engineInfo['explanation'] as Map<String, dynamic>?;
    if (explanation == null) return;

    final narrative = (explanation['narrative'] as List<dynamic>? ?? [])
        .whereType<String>()
        .toList();
    final shortLines = narrative.take(2).toList();
    final scoreCp = explanation['after_eval_cp'] as int? ?? _evalCp;
    final scoreText = (scoreCp / 100.0).toStringAsFixed(2);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text('AI Explanation', style: AppTextStyles.titleLarge),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Eval: ${scoreCp >= 0 ? '+' : ''}$scoreText',
              style: AppTextStyles.bodyMedium.copyWith(
                color: scoreCp >= 0 ? Colors.greenAccent : Colors.redAccent,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 10),
            if (shortLines.isEmpty)
              Text(
                'No explanation available yet. Play a move and try again.',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textMuted,
                ),
              ),
            for (final line in shortLines)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  '- $line',
                  style: AppTextStyles.bodyMedium,
                ),
              ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Close', style: TextStyle(color: AppColors.primary)),
          ),
        ],
      ),
    );
  }

  Widget _compactBtn(
    IconData icon,
    String label,
    VoidCallback? onTap, {
    Color? color,
  }) {
    final c = color ?? AppColors.textSecondary;
    final disabled = onTap == null;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 200),
          opacity: disabled ? 0.3 : 1.0,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.card,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: AppColors.textMuted.withValues(alpha: 0.15),
              ),
            ),
            child: Column(
              children: [
                Icon(icon, size: 18, color: c),
                const SizedBox(height: 2),
                Text(
                  label,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: c,
                    fontWeight: FontWeight.w600,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─── History Bottom Sheet ──────────────────────────────
  void _showHistorySheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.65,
        minChildSize: 0.3,
        maxChildSize: 0.9,
        builder: (_, scrollController) => Container(
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // Handle bar
              Padding(
                padding: const EdgeInsets.only(top: 12, bottom: 8),
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppColors.textMuted,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              // Tabs: Move History & Engine Eval
              Expanded(
                child: DefaultTabController(
                  length: 2,
                  child: Column(
                    children: [
                      TabBar(
                        indicatorColor: AppColors.primary,
                        labelColor: AppColors.primary,
                        unselectedLabelColor: AppColors.textMuted,
                        tabs: const [
                          Tab(text: 'Move History'),
                          Tab(text: 'Engine Eval'),
                        ],
                      ),
                      Expanded(
                        child: TabBarView(
                          children: [
                            // Move History tab
                            _buildSheetMoveHistory(scrollController),
                            // Engine Eval tab
                            _buildSheetEngineEval(scrollController),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSheetMoveHistory(ScrollController scrollController) {
    if (_gameState.moveHistory.isEmpty) {
      return Center(
        child: Text(
          'Moves will appear here',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textMuted),
        ),
      );
    }
    return ListView.builder(
      controller: scrollController,
      padding: const EdgeInsets.all(14),
      itemCount: (_gameState.moveHistory.length + 1) ~/ 2,
      itemBuilder: (context, index) {
        final whiteMove = _gameState.moveHistory[index * 2];
        final blackMove = (index * 2 + 1 < _gameState.moveHistory.length)
            ? _gameState.moveHistory[index * 2 + 1]
            : null;
        return Container(
          padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
          decoration: BoxDecoration(
            color: index % 2 == 0
                ? Colors.transparent
                : AppColors.surface.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Row(
            children: [
              SizedBox(
                width: 32,
                child: Text(
                  '${index + 1}.',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textMuted,
                  ),
                ),
              ),
              Expanded(child: _moveWithIcon(whiteMove, true)),
              Expanded(
                child: blackMove != null
                    ? _moveWithIcon(blackMove, false)
                    : const SizedBox(),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _moveWithIcon(String san, bool isWhite) {
    String icon;
    if (san.startsWith('O-O')) {
      icon = isWhite ? '♔' : '♚';
    } else if (san.startsWith('K')) {
      icon = isWhite ? '♔' : '♚';
    } else if (san.startsWith('Q')) {
      icon = isWhite ? '♕' : '♛';
    } else if (san.startsWith('R')) {
      icon = isWhite ? '♖' : '♜';
    } else if (san.startsWith('B')) {
      icon = isWhite ? '♗' : '♝';
    } else if (san.startsWith('N')) {
      icon = isWhite ? '♘' : '♞';
    } else {
      icon = isWhite ? '♙' : '♟';
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(icon, style: const TextStyle(fontSize: 16)),
        const SizedBox(width: 4),
        Text(
          san,
          style: AppTextStyles.bodyMedium.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
      ],
    );
  }

  Widget _buildSheetEngineEval(ScrollController scrollController) {
    return ListView(
      controller: scrollController,
      padding: const EdgeInsets.all(14),
      children: [
        _evalRow('Eval (cp)', _evalCp),
        _evalRow('Depth', _engineInfo['depth'] ?? 0),
        _evalRow('Time (s)', ((_engineInfo['time_ms'] ?? 0) / 1000).round()),
        _evalRow('Nodes', _engineInfo['nodes'] ?? 0),
        _evalRow('Q-Nodes', _engineInfo['qnodes'] ?? 0),
        _evalRow('Cutoffs', _engineInfo['cutoffs'] ?? 0),
        _evalRow('TT Hits', _engineInfo['tt_hits'] ?? 0),
        _evalRow('TT Probes', _engineInfo['tt_probes'] ?? 0),
        _evalRow('Max Ply', _engineInfo['max_ply'] ?? 0),
        _evalRow('Max Q-Ply', _engineInfo['max_qply'] ?? 0),
      ],
    );
  }

  // ─── Title Bar ─────────────────────────────────────────
  Widget _buildTitleBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => Navigator.pop(context),
            child: const Icon(
              Icons.arrow_back_ios,
              color: AppColors.textPrimary,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Text(
            'Chess AI',
            style: AppTextStyles.headlineLarge.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
          const Spacer(),
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

  // ─── Player Label with Timer ───────────────────────────
  Widget _buildPlayerLabel({required bool isTop}) {
    // Top label = opponent, Bottom label = player
    final isEngine = isTop ? true : false;
    final isWhiteSide = isTop
        ? (!widget.playerIsWhite) // top is the opponent's color
        : widget.playerIsWhite;
    final label = isEngine ? 'Engine' : 'You';
    final colorLetter = isWhiteSide ? 'W' : 'B';
    final timeLeft = isWhiteSide ? _whiteTimeLeft : _blackTimeLeft;

    return Row(
      children: [
        // Color badge
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: isWhiteSide ? Colors.white : Colors.black,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: AppColors.textMuted.withValues(alpha: 0.3),
            ),
          ),
          child: Center(
            child: Text(
              colorLetter,
              style: TextStyle(
                color: isWhiteSide ? Colors.black : Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 14,
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Text(
          label,
          style: AppTextStyles.titleMedium.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        if (_gameState.isEngineThinking && isEngine) ...[
          const SizedBox(width: 8),
          SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: AppColors.primary,
            ),
          ),
        ],
        const Spacer(),
        if (_hasTimer)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: _isActiveTimer(isWhiteSide)
                    ? AppColors.primary.withValues(alpha: 0.5)
                    : AppColors.textMuted.withValues(alpha: 0.2),
              ),
            ),
            child: Text(
              _formatTime(timeLeft),
              style: AppTextStyles.titleLarge.copyWith(
                fontFamily: 'monospace',
                fontWeight: FontWeight.w700,
                color: timeLeft <= 30
                    ? AppColors.error
                    : _isActiveTimer(isWhiteSide)
                    ? AppColors.textPrimary
                    : AppColors.textMuted,
                fontSize: 18,
              ),
            ),
          ),
      ],
    );
  }

  bool _isActiveTimer(bool isWhiteSide) {
    if (_gameState.isGameOver) return false;
    return (isWhiteSide && _gameState.board.turn == chess.Color.WHITE) ||
        (!isWhiteSide && _gameState.board.turn == chess.Color.BLACK);
  }

  // ─── Right Info Panel ──────────────────────────────────
  Widget _buildInfoPanel() {
    return Column(
      children: [
        // Move History
        _buildMoveHistorySection(),
        const SizedBox(height: 12),
        // Engine Evaluation
        _buildEngineEvalSection(),
        const SizedBox(height: 12),
        // Action buttons
        _buildActionButtons(),
      ],
    );
  }

  Widget _buildMoveHistorySection() {
    final isWhiteTurn = _gameState.board.turn == chess.Color.WHITE;
    return Expanded(
      flex: 3,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.1)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                Text(
                  'Move History',
                  style: AppTextStyles.titleMedium.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.circle,
                        size: 8,
                        color: isWhiteTurn ? Colors.white : AppColors.textMuted,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        isWhiteTurn ? "White's Turn" : "Black's Turn",
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            // Move list
            Expanded(
              child: _gameState.moveHistory.isEmpty
                  ? Center(
                      child: Text(
                        'Moves will appear here',
                        style: AppTextStyles.bodyMedium.copyWith(
                          color: AppColors.textMuted,
                        ),
                      ),
                    )
                  : ListView.builder(
                      controller: _moveScrollController,
                      itemCount: (_gameState.moveHistory.length + 1) ~/ 2,
                      itemBuilder: (context, index) {
                        final whiteMove = _gameState.moveHistory[index * 2];
                        final blackMove =
                            (index * 2 + 1 < _gameState.moveHistory.length)
                            ? _gameState.moveHistory[index * 2 + 1]
                            : null;
                        final isLast =
                            index ==
                            (_gameState.moveHistory.length + 1) ~/ 2 - 1;
                        return Container(
                          padding: const EdgeInsets.symmetric(
                            vertical: 3,
                            horizontal: 8,
                          ),
                          decoration: BoxDecoration(
                            color: index % 2 == 0
                                ? Colors.transparent
                                : AppColors.surface.withValues(alpha: 0.3),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Row(
                            children: [
                              SizedBox(
                                width: 28,
                                child: Text(
                                  '${index + 1}.',
                                  style: AppTextStyles.bodySmall.copyWith(
                                    color: AppColors.textMuted,
                                  ),
                                ),
                              ),
                              Expanded(
                                child: Text(
                                  whiteMove,
                                  style: AppTextStyles.bodyMedium.copyWith(
                                    color: isLast && blackMove == null
                                        ? AppColors.primary
                                        : AppColors.textPrimary,
                                    fontWeight: isLast && blackMove == null
                                        ? FontWeight.w600
                                        : FontWeight.w400,
                                  ),
                                ),
                              ),
                              Expanded(
                                child: Text(
                                  blackMove ?? '',
                                  style: AppTextStyles.bodyMedium.copyWith(
                                    color: isLast && blackMove != null
                                        ? AppColors.primary
                                        : AppColors.textPrimary,
                                    fontWeight: isLast && blackMove != null
                                        ? FontWeight.w600
                                        : FontWeight.w400,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEngineEvalSection() {
    if (!widget.enableExplanation) {
      return Expanded(
        flex: 4,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: AppColors.textMuted.withValues(alpha: 0.1),
            ),
          ),
          child: Center(
            child: Text(
              'AI explanation is turned off for this game.',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textMuted,
              ),
            ),
          ),
        ),
      );
    }

    final hasExplanation =
        _engineInfo.containsKey('explanation') &&
        _engineInfo['explanation'] != null;

    if (!hasExplanation) {
      // Fallback empty view or older basic view
      return Expanded(
        flex: 4,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: AppColors.textMuted.withValues(alpha: 0.1),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '🤔 AI REASONING',
                style: AppTextStyles.labelLarge.copyWith(
                  letterSpacing: 1.5,
                  fontSize: 12,
                ),
              ),
              const Spacer(),
              Center(
                child: Text(
                  _gameState.isEngineThinking
                      ? 'Thinking...'
                      : 'No explanation available.',
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textMuted,
                  ),
                ),
              ),
              const Spacer(),
            ],
          ),
        ),
      );
    }

    final explanation = _engineInfo['explanation'] as Map<String, dynamic>;
    final scoreCp = explanation['after_eval_cp'] as int? ?? 0;
    final gamePhase = explanation['game_phase'] as String? ?? 'Middlegame';

    // Formatted evaluation
    String evalStr;
    if (scoreCp.abs() >= 90000) {
      final mateIn = (100000 - scoreCp.abs() + 1) ~/ 2;
      evalStr = scoreCp > 0 ? '+M$mateIn' : '-M$mateIn';
    } else {
      final pawnUnits = scoreCp / 100.0;
      evalStr = pawnUnits >= 0
          ? '+${pawnUnits.toStringAsFixed(2)}'
          : pawnUnits.toStringAsFixed(2);
    }

    return Expanded(
      flex: 4,
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.1)),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  border: Border(
                    bottom: BorderSide(
                      color: AppColors.textMuted.withValues(alpha: 0.1),
                    ),
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '🤔 AI REASONING',
                      style: AppTextStyles.labelLarge.copyWith(
                        letterSpacing: 1.5,
                        fontSize: 12,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      gamePhase.toUpperCase(),
                      style: AppTextStyles.labelSmall.copyWith(
                        color: AppColors.textMuted,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ],
                ),
              ),

              // Content Area
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(14),
                  children: [
                    // Top Eval Score & Depth
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          evalStr,
                          style: AppTextStyles.displayMedium.copyWith(
                            color: scoreCp >= 0
                                ? Colors.greenAccent
                                : Colors.redAccent,
                            fontSize: 28,
                            height: 1.0,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Padding(
                          padding: const EdgeInsets.only(bottom: 3),
                          child: Text(
                            'Depth ${_engineInfo['depth'] ?? 0}',
                            style: AppTextStyles.bodySmall.copyWith(
                              color: AppColors.textMuted,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    // Bar Chart
                    Text(
                      'EVALUATION COMPONENTS',
                      style: AppTextStyles.labelSmall.copyWith(
                        color: AppColors.textMuted,
                        letterSpacing: 1.0,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _buildBreakdownChart(
                      explanation['full_breakdown_after']
                              as Map<String, dynamic>? ??
                          {},
                    ),
                    const SizedBox(height: 16),

                    // Narrative
                    Text(
                      'WHY THIS MOVE?',
                      style: AppTextStyles.labelSmall.copyWith(
                        color: AppColors.textMuted,
                        letterSpacing: 1.0,
                      ),
                    ),
                    const SizedBox(height: 6),
                    _buildNarrative(
                      explanation['narrative'] as List<dynamic>? ?? [],
                    ),
                    const SizedBox(height: 16),

                    // Alternatives
                    Text(
                      'TOP ALTERNATIVES',
                      style: AppTextStyles.labelSmall.copyWith(
                        color: AppColors.textMuted,
                        letterSpacing: 1.0,
                      ),
                    ),
                    const SizedBox(height: 6),
                    _buildAlternatives(
                      _engineInfo['alternatives'] as List<dynamic>? ?? [],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBreakdownChart(Map<String, dynamic> bk) {
    if (bk.isEmpty) return const SizedBox();

    // Group the granular keys into major categories
    int material =
        (bk['material_mg_white'] ?? 0) +
        (bk['material_eg_white'] ?? 0) -
        (bk['material_mg_black'] ?? 0) -
        (bk['material_eg_black'] ?? 0);
    int pst =
        (bk['pst_mg_white'] ?? 0) +
        (bk['pst_eg_white'] ?? 0) -
        (bk['pst_mg_black'] ?? 0) -
        (bk['pst_eg_black'] ?? 0);
    int structure =
        (bk['doubled_pawns_mg'] ?? 0) +
        (bk['doubled_pawns_eg'] ?? 0) +
        (bk['isolated_pawns_mg'] ?? 0) +
        (bk['isolated_pawns_eg'] ?? 0) +
        (bk['passed_pawns_mg'] ?? 0) +
        (bk['passed_pawns_eg'] ?? 0) +
        (bk['connected_passers_eg'] ?? 0);
    int kingSafety =
        (bk['king_shield_mg'] ?? 0) + (bk['king_prox_passer_eg'] ?? 0);
    int mobility =
        (bk['rook_open_file_mg'] ?? 0) +
        (bk['rook_open_file_eg'] ?? 0) +
        (bk['rook_semi_open_mg'] ?? 0) +
        (bk['rook_semi_open_eg'] ?? 0) +
        (bk['bishop_pair_mg'] ?? 0) +
        (bk['bishop_pair_eg'] ?? 0);
    int tactical =
        (bk['hanging_penalty_mg'] ?? 0) + (bk['hanging_penalty_eg'] ?? 0);

    final isWhiteTurn = _gameState.board.turn == chess.Color.WHITE;
    if (!isWhiteTurn) {
      // The breakdown is stored absolute (White positive). If black just moved, negate to show from Black's perspective?
      // Actually, standard AI panels always show absolute (White positive), so we'll keep it absolute, but colored.
    }

    Widget bar(String label, int val, Color color) {
      // scale up slightly so small differences are visible, max 300cp
      final widthFactor = (val.abs() / 300.0).clamp(0.0, 1.0);
      return Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(
          children: [
            SizedBox(
              width: 70,
              child: Text(
                label,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
            Expanded(
              child: Stack(
                alignment: val >= 0
                    ? Alignment.centerLeft
                    : Alignment.centerRight,
                children: [
                  Container(
                    height: 8,
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  FractionallySizedBox(
                    widthFactor: widthFactor.isNaN ? 0 : widthFactor,
                    child: Container(
                      height: 8,
                      decoration: BoxDecoration(
                        color: color,
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(
              width: 45,
              child: Text(
                '${val > 0 ? '+' : ''}${(val / 100.0).toStringAsFixed(1)}',
                style: AppTextStyles.bodySmall.copyWith(
                  color: val > 0
                      ? Colors.greenAccent
                      : (val < 0 ? Colors.redAccent : AppColors.textMuted),
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.right,
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        bar(
          'Material',
          material,
          material >= 0 ? Colors.green.shade400 : Colors.red.shade400,
        ),
        bar(
          'Position',
          pst,
          pst >= 0 ? Colors.green.shade400 : Colors.red.shade400,
        ),
        bar(
          'Structure',
          structure,
          structure >= 0 ? Colors.green.shade300 : Colors.red.shade300,
        ),
        bar(
          'King Safety',
          kingSafety,
          kingSafety >= 0 ? Colors.green.shade300 : Colors.red.shade300,
        ),
        bar(
          'Activity',
          mobility,
          mobility >= 0 ? Colors.green.shade200 : Colors.red.shade200,
        ),
        bar(
          'Tactics',
          tactical,
          tactical >= 0 ? Colors.green.shade200 : Colors.red.shade200,
        ),
      ],
    );
  }

  Widget _buildNarrative(List<dynamic> sentences) {
    if (sentences.isEmpty) {
      return Text(
        "No narrative available.",
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: sentences.map((s) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '• ',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.primary,
                ),
              ),
              Expanded(
                child: Text(
                  s.toString(),
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textPrimary,
                    height: 1.3,
                  ),
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildAlternatives(List<dynamic> alts) {
    if (alts.isEmpty) {
      return Text(
        "No alternatives found.",
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
      );
    }

    // Get current side to determine +/- formatting correctly actually evaluate returns absolute, so it's fine.
    return Row(
      children: alts.map((m) {
        final uci = m['move_uci'] as String;
        int cp = (m['eval_cp'] as num).toInt();

        String evalStr;
        if (cp.abs() >= 90000) {
          final mateIn = (100000 - cp.abs() + 1) ~/ 2;
          evalStr = cp > 0 ? '+M$mateIn' : '-M$mateIn';
        } else {
          final pawnUnits = cp / 100.0;
          evalStr = pawnUnits >= 0
              ? '+${pawnUnits.toStringAsFixed(1)}'
              : pawnUnits.toStringAsFixed(1);
        }

        return Expanded(
          child: Container(
            margin: const EdgeInsets.only(right: 6),
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
            decoration: BoxDecoration(
              color: AppColors.surface.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: AppColors.textMuted.withValues(alpha: 0.1),
              ),
            ),
            child: Column(
              children: [
                Text(
                  uci,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  evalStr,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _evalRow(String label, num value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          Text(
            value.toString(),
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return Column(
      children: [
        // Resign button
        if (!_gameState.isGameOver)
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: _resign,
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                side: BorderSide(
                  color: AppColors.textMuted.withValues(alpha: 0.3),
                ),
              ),
              child: Text(
                'Resign',
                style: AppTextStyles.titleMedium.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          ),
        if (_gameState.isGameOver)
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _newGame,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: Text('New Game', style: AppTextStyles.button),
            ),
          ),
        const SizedBox(height: 8),
        // Secondary actions row
        Row(
          children: [
            Expanded(
              child: _smallActionButton(
                icon: Icons.undo,
                label: 'Undo',
                onTap:
                    _gameState.moveHistory.length >= 2 &&
                        !_gameState.isEngineThinking
                    ? _undoMove
                    : null,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _smallActionButton(
                icon: Icons.flip,
                label: 'Flip',
                onTap: () => setState(() => _boardFlipped = !_boardFlipped),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _smallActionButton({
    required IconData icon,
    required String label,
    VoidCallback? onTap,
  }) {
    final isDisabled = onTap == null;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 200),
        opacity: isDisabled ? 0.3 : 1.0,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: AppColors.textMuted.withValues(alpha: 0.15),
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 16, color: AppColors.textSecondary),
              const SizedBox(width: 6),
              Text(
                label,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
