import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:chess/chess.dart' as chess;
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../models/difficulty.dart';
import '../models/game_state.dart';
import '../engine/engine.dart';
import '../engine/explainer.dart';
import '../engine/evaluation.dart';
import '../engine/search.dart' as engine_search;
import '../widgets/chess_board_widget.dart';
import '../widgets/promotion_dialog.dart';
import '../widgets/move_history_panel.dart';
import '../widgets/eval_bar.dart';
import '../widgets/coach_feedback_panel.dart';
import '../screens/post_game_analysis_screen.dart';

/// Main game screen — portrait-first layout matching the Chess AI screenshots.
class GameScreen extends StatefulWidget {
  final Difficulty difficulty;
  final bool playerIsWhite;
  final int timerSeconds;
  final bool enableCoachMode;
  final String? fen;

  const GameScreen({
    super.key,
    required this.difficulty,
    required this.playerIsWhite,
    this.timerSeconds = 0,
    this.enableCoachMode = false,
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
  Map<String, dynamic> _engineRawInfo = {};
  final ScrollController _moveScrollController = ScrollController();
  String? _premoveFrom;
  String? _premoveTo;
  DateTime? _lastTick;
  double _tickRemainderMs = 0;

  // ── Coach state (persistent, not timed) ──────────────
  Map<String, dynamic>? _lastCoachData; // {key, text, bestSan}

  // ── Review mode ──────────────────────────────────────
  int? _reviewMoveIndex;
  bool get _isReviewMode =>
      _reviewMoveIndex != null &&
      _reviewMoveIndex! < _gameState.moveHistory.length;

  // ── Chess clock ──────────────────────────────────────
  late int _whiteTimeLeft;
  late int _blackTimeLeft;
  Timer? _clockTimer;
  bool get _hasTimer => widget.timerSeconds > 0;

  // ──────────────────────────────────────────────────────
  // Init / Dispose
  // ──────────────────────────────────────────────────────
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

  // ──────────────────────────────────────────────────────
  // Chess Clock
  // ──────────────────────────────────────────────────────
  void _startClock() {
    _clockTimer?.cancel();
    _lastTick = DateTime.now();
    _tickRemainderMs = 0;
    _clockTimer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (_gameState.isGameOver) return;
      final now = DateTime.now();
      final last = _lastTick ?? now;
      final elapsedMs = now.difference(last).inMilliseconds.toDouble();
      _lastTick = now;
      if (elapsedMs <= 0) return;

      _tickRemainderMs += elapsedMs;
      int wholeSeconds = (_tickRemainderMs ~/ 1000);
      _tickRemainderMs = _tickRemainderMs % 1000;
      if (wholeSeconds <= 0) return;

      setState(() {
        if (_gameState.board.turn == chess.Color.WHITE) {
          _whiteTimeLeft -= wholeSeconds;
          if (_whiteTimeLeft <= 0) {
            _whiteTimeLeft = 0;
            _clockTimer?.cancel();
            _showTimeoutDialog(isWhite: true);
          }
        } else {
          _blackTimeLeft -= wholeSeconds;
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
          "Time's Up!",
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

  // ──────────────────────────────────────────────────────
  // Move Logic
  // ──────────────────────────────────────────────────────
  void _onSquareTapped(int squareIndex) {
    if (_gameState.isGameOver) return;
    if (_hasTimer &&
        ((_gameState.board.turn == chess.Color.WHITE && _whiteTimeLeft <= 0) ||
            (_gameState.board.turn == chess.Color.BLACK &&
                _blackTimeLeft <= 0))) {
      return;
    }

    final sqName = _indexToAlgebraic(squareIndex);
    final piece = _gameState.board.get(sqName);

    // If it's not the player's turn, treat taps as premove planning.
    if (!_gameState.isPlayerTurn || _gameState.isEngineThinking) {
      _handlePremoveTap(squareIndex, sqName, piece);
      return;
    }

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
          _reviewMoveIndex = null;
          _premoveFrom = null;
          _premoveTo = null;
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

  void _handlePremoveTap(int squareIndex, String sqName, chess.Piece? piece) {
    final isPlayersPiece =
        piece != null &&
        ((piece.color == chess.Color.WHITE && _gameState.playerIsWhite) ||
            (piece.color == chess.Color.BLACK && !_gameState.playerIsWhite));

    // First tap must be one of the player's pieces.
    if (_premoveFrom == null) {
      if (!isPlayersPiece) return;
      setState(() {
        _premoveFrom = sqName;
        _premoveTo = null;
        _selectedSquare = squareIndex;
        _legalMoves = [];
      });
      return;
    }

    // Second tap sets destination; allow tapping same square to cancel.
    if (_premoveFrom == sqName) {
      setState(() {
        _premoveFrom = null;
        _premoveTo = null;
        _selectedSquare = null;
      });
      return;
    }

    setState(() {
      _premoveTo = sqName;
      _selectedSquare = null;
    });
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
      _reviewMoveIndex = null;
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

  // ──────────────────────────────────────────────────────
  // Execute a player move + store coach annotation
  // ──────────────────────────────────────────────────────
  void _executeMove(chess.Move move) {
    final boardBefore = chess.Chess.fromFEN(_gameState.board.fen);
    final prevEval = evaluate(boardBefore);
    // Clear any pending premove once we make an actual move.
    _premoveFrom = null;
    _premoveTo = null;
    _lastTick = DateTime.now();
    _tickRemainderMs = 0;

    // Track captures
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
    _gameState.moveHistoryObjects.add(move);

    // ── Coach annotation ─────────────────────────────
    String? category;
    String? comment;
    String? bestSan;
    List<Map<String, dynamic>>? altList;

    if (widget.enableCoachMode) {
      try {
        final currEval = evaluate(_gameState.board);
        final moverIsWhite = boardBefore.turn == chess.Color.WHITE;
        final sign = moverIsWhite ? 1 : -1;
        final delta = (currEval - prevEval) * sign;

        // Find top alternatives for mildly inaccurate moves as well.
        if (delta <= -25) {
          final boardForSearch = chess.Chess.fromFEN(boardBefore.fen);
          final best = engine_search.searchWithInfo(
            boardForSearch,
            5,
            engineIsBlack: boardBefore.turn == chess.Color.BLACK,
          );

          final suggestions = <Map<String, dynamic>>[];
          final rawAlts = (best.info['alternatives'] as List<dynamic>? ?? [])
              .whereType<Map>()
              .toList();

          for (final raw in rawAlts) {
            final moveUci = raw['move_uci']?.toString();
            if (moveUci == null || moveUci.length < 4) continue;

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

            final suggestedMove = boardBefore
                .generate_moves()
                .where(
                  (m) =>
                      m.fromAlgebraic == fromSq &&
                      m.toAlgebraic == toSq &&
                      m.promotion == promo,
                )
                .firstOrNull;
            if (suggestedMove == null) continue;

            suggestions.add({
              'san': boardBefore.move_to_san(suggestedMove),
              'eval_cp': (raw['eval_cp'] as int?) ?? 0,
            });
          }

          if (suggestions.isEmpty && best.move != null) {
            suggestions.add({
              'san': boardBefore.move_to_san(best.move!),
              'eval_cp': (best.info['eval_cp'] as int?) ?? 0,
            });
          }

          // Keep only genuinely different ideas from the played move.
          String normSan(String s) =>
              s.replaceAll(RegExp(r'[+#?!]'), '').trim();
          final playedNorm = normSan(san);
          final filtered = suggestions.where((s) {
            final moveSan = s['san']?.toString() ?? '';
            return normSan(moveSan) != playedNorm;
          }).toList();

          final finalSuggestions = filtered.isNotEmpty ? filtered : suggestions;

          if (finalSuggestions.isNotEmpty) {
            bestSan = finalSuggestions.first['san'] as String?;
            altList = finalSuggestions.take(3).toList();
          }
        }

        final explanation = Explainer.analyzeMove(
          boardBefore,
          _gameState.board,
          move,
          prevEval,
          currEval,
          bestMoveSan: bestSan,
        );

        if (explanation != null) {
          category = explanation['key'] as String?;
          comment = explanation['text'] as String?;
          setState(() {
            _lastCoachData = {
              'category': category,
              'comment': comment,
              'bestSan': bestSan,
              'alternatives': altList,
            };
          });
        } else {
          // Always provide at least one useful coaching takeaway.
          category = 'DEVELOPMENT';
          comment = _buildFallbackCoachComment(
            deltaCp: delta,
            playedSan: san,
            bestMoveSan: bestSan,
          );
          setState(() {
            _lastCoachData = {
              'category': category,
              'comment': comment,
              'bestSan': bestSan,
              'alternatives': altList,
            };
          });
        }
      } catch (_) {
        category = 'DEVELOPMENT';
        comment =
            'Solid move. Keep improving your least active piece and king safety.';
        setState(() {
          _lastCoachData = {
            'category': category,
            'comment': comment,
            'bestSan': bestSan,
            'alternatives': altList,
          };
        });
      }
    } else {
      setState(() => _lastCoachData = null);
    }

    // Store annotation in game state
    _gameState.moveCategories.add(category);
    _gameState.moveComments.add(comment);
    _gameState.moveAlternatives.add(altList);

    setState(() => _lastMove = move);
    _scrollMoveHistory();

    if (!_gameState.isGameOver && !_gameState.isPlayerTurn) {
      _scheduleEngineMove();
    }
    if (_gameState.isGameOver) _showGameOverDialog();
  }

  // ──────────────────────────────────────────────────────
  // Engine move + annotation
  // ──────────────────────────────────────────────────────
  void _scheduleEngineMove() {
    setState(() => _gameState.isEngineThinking = true);

    Future.delayed(const Duration(milliseconds: 100), () async {
      try {
        final engineTurnIsWhite = _gameState.board.turn == chess.Color.WHITE;
        final engineThinkStart = DateTime.now();

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
            final boardBeforeEngine = chess.Chess.fromFEN(_gameState.board.fen);
            final moverPiece = boardBeforeEngine.get(move.fromAlgebraic);
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
            _gameState.moveHistoryObjects.add(move);

            // On web, heavy engine work can block UI; reconcile elapsed time so clocks stay accurate.
            if (kIsWeb && _hasTimer) {
              final elapsedSec = DateTime.now()
                  .difference(engineThinkStart)
                  .inSeconds;
              if (elapsedSec > 0) {
                if (engineTurnIsWhite) {
                  _whiteTimeLeft = (_whiteTimeLeft - elapsedSec).clamp(
                    0,
                    99999,
                  );
                  if (_whiteTimeLeft <= 0) {
                    _whiteTimeLeft = 0;
                    _gameState.isEngineThinking = false;
                    _showTimeoutDialog(isWhite: true);
                    return;
                  }
                } else {
                  _blackTimeLeft = (_blackTimeLeft - elapsedSec).clamp(
                    0,
                    99999,
                  );
                  if (_blackTimeLeft <= 0) {
                    _blackTimeLeft = 0;
                    _gameState.isEngineThinking = false;
                    _showTimeoutDialog(isWhite: false);
                    return;
                  }
                }
              }
            }

            // Coach for engine move
            String? engineCategory;
            String? engineComment;

            if (widget.enableCoachMode) {
              try {
                final engineExplanation = Explainer.explainMove(
                  boardBeforeEngine,
                  move,
                  {'depth': result.depth, 'nodes': result.nodes},
                );
                final narrative =
                    (engineExplanation['narrative'] as List<dynamic>? ?? [])
                        .whereType<String>()
                        .toList();
                final primaryLine = narrative.isNotEmpty
                    ? narrative.first
                    : 'The move improves activity and keeps pressure.';

                engineCategory = 'ENGINE_REASON';
                engineComment = 'Engine played $san: $primaryLine';

                setState(() {
                  _lastCoachData = {
                    'category': engineCategory,
                    'comment': engineComment,
                    'bestSan': null,
                    'alternatives': null,
                  };
                });
              } catch (_) {
                engineCategory = 'ENGINE_REASON';
                engineComment =
                    'Engine played $san (${moverPiece?.type.name.toLowerCase() ?? 'piece'} move).';
                setState(() {
                  _lastCoachData = {
                    'category': engineCategory,
                    'comment': engineComment,
                    'bestSan': null,
                    'alternatives': null,
                  };
                });
              }
            }

            // Store engine annotation
            _gameState.moveCategories.add(engineCategory);
            _gameState.moveComments.add(engineComment);
            _gameState.moveAlternatives.add(null);

            setState(() {
              _lastMove = move;
              _engineRawInfo = {
                'eval_cp': result.evalCp,
                'depth': result.depth,
                'time_ms': result.timeMs,
                'nodes': result.nodes,
              };
              _gameState.isEngineThinking = false;
              _lastTick = DateTime.now();
              _tickRemainderMs = 0;
            });
            _scrollMoveHistory();
            _tryExecutePremoveIfReady();
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

  void _tryExecutePremoveIfReady() {
    if (_premoveFrom == null || _premoveTo == null) return;
    if (!_gameState.isPlayerTurn || _gameState.isEngineThinking) return;

    final move = _gameState.board
        .generate_moves()
        .where(
          (m) => m.fromAlgebraic == _premoveFrom && m.toAlgebraic == _premoveTo,
        )
        .firstOrNull;

    setState(() {
      _selectedSquare = null;
    });

    if (move != null) {
      _premoveFrom = null;
      _premoveTo = null;
      _executeMove(move);
    } else {
      _premoveFrom = null;
      _premoveTo = null;
    }
  }

  // ──────────────────────────────────────────────────────
  // Dialogs
  // ──────────────────────────────────────────────────────
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
          if (_gameState.moveHistory.isNotEmpty)
            TextButton.icon(
              onPressed: () {
                Navigator.of(ctx).pop();
                _openAnalysis();
              },
              icon: const Icon(Icons.analytics_outlined, size: 18),
              label: const Text('Analyze Game'),
              style: TextButton.styleFrom(foregroundColor: AppColors.accent),
            ),
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

  void _openAnalysis() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => PostGameAnalysisScreen(gameState: _gameState),
      ),
    );
  }

  void _showResignDialog() {
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
              _showPostResignOptionsDialog();
            },
            child: Text('Resign', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }

  void _showPostResignOptionsDialog() {
    _clockTimer?.cancel();
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text('You Resigned', style: AppTextStyles.headlineMedium),
        content: Text(
          'Would you like to go home or review the game?',
          style: AppTextStyles.bodyMedium,
        ),
        actions: [
          if (_gameState.moveHistory.isNotEmpty)
            TextButton.icon(
              onPressed: () {
                Navigator.of(ctx).pop();
                _openAnalysis();
              },
              icon: const Icon(Icons.analytics_outlined, size: 18),
              label: const Text('Post-Game Analysis'),
              style: TextButton.styleFrom(foregroundColor: AppColors.accent),
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

  // ──────────────────────────────────────────────────────
  // New game / Undo
  // ──────────────────────────────────────────────────────
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
      _engineRawInfo = {};
      _lastCoachData = null;
      _reviewMoveIndex = null;
      _premoveFrom = null;
      _premoveTo = null;
      _lastTick = DateTime.now();
      _whiteTimeLeft = widget.timerSeconds;
      _blackTimeLeft = widget.timerSeconds;
    });
    if (_hasTimer) _startClock();
    if (!_gameState.isPlayerTurn && !_gameState.isGameOver) {
      _scheduleEngineMove();
    }
  }

  void _undoMove() {
    if (_gameState.moveHistory.length < 2) return;
    _gameState.board.undo_move();
    _gameState.board.undo_move();
    final len = _gameState.moveHistory.length;
    if (len >= 2) {
      _gameState.moveHistory.removeRange(len - 2, len);
      _gameState.moveHistoryObjects.removeRange(len - 2, len);
      _gameState.moveCategories.removeRange(len - 2, len);
      _gameState.moveComments.removeRange(len - 2, len);
      _gameState.moveAlternatives.removeRange(len - 2, len);
    }
    setState(() {
      _selectedSquare = null;
      _legalMoves = [];
      _lastMove = null;
      _lastCoachData = null;
      _reviewMoveIndex = null;
    });
  }

  // ──────────────────────────────────────────────────────
  // Review/Playback
  // ──────────────────────────────────────────────────────
  void _goToFirstMove() {
    if (_gameState.moveHistory.isEmpty) return;
    setState(() => _reviewMoveIndex = 0);
  }

  void _goToPreviousMove() {
    if (_gameState.moveHistory.isEmpty) return;
    setState(() {
      _reviewMoveIndex =
          (_reviewMoveIndex ?? _gameState.moveHistory.length) - 1;
      if (_reviewMoveIndex! < 0) _reviewMoveIndex = 0;
    });
  }

  void _goToNextMove() {
    if (_gameState.moveHistory.isEmpty) return;
    setState(() {
      if (_reviewMoveIndex == null) return;
      _reviewMoveIndex = _reviewMoveIndex! + 1;
      if (_reviewMoveIndex! >= _gameState.moveHistory.length) {
        _reviewMoveIndex = null;
      }
    });
  }

  void _goToLastMove() {
    setState(() => _reviewMoveIndex = null);
  }

  void _goToMove(int index) {
    if (index >= _gameState.moveHistory.length - 1) {
      setState(() => _reviewMoveIndex = null);
    } else {
      setState(() => _reviewMoveIndex = index + 1);
    }
  }

  String _indexToAlgebraic(int index) {
    final file = index % 8;
    final rank = index ~/ 8;
    return String.fromCharCode('a'.codeUnitAt(0) + file) +
        String.fromCharCode('1'.codeUnitAt(0) + rank);
  }

  bool _isActiveTimer(bool isWhiteSide) {
    if (_gameState.isGameOver) return false;
    return (isWhiteSide && _gameState.board.turn == chess.Color.WHITE) ||
        (!isWhiteSide && _gameState.board.turn == chess.Color.BLACK);
  }

  // ──────────────────────────────────────────────────────
  // Build
  // ──────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppColors.backgroundGradient),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth > 800) {
                return _buildWideLayout(constraints);
              }
              return _buildPortraitLayout(constraints);
            },
          ),
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────
  // Wide (Desktop / Landscape) Layout
  // ──────────────────────────────────────────────────────
  Widget _buildWideLayout(BoxConstraints constraints) {
    final boardMaxSize = (constraints.maxHeight - 120).clamp(300.0, 640.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildTitleBar(),
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Board column
              Padding(
                padding: const EdgeInsets.only(left: 24, right: 16),
                child: SizedBox(
                  width: boardMaxSize,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _buildPlayerLabel(isTop: true),
                      const SizedBox(height: 4),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Eval bar
                          SizedBox(
                            width: 24,
                            child: _buildVerticalEvalBar(boardMaxSize),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: ChessBoardWidget(
                              board: _isReviewMode
                                  ? _gameState.getBoardAtMove(_reviewMoveIndex!)
                                  : _gameState.board,
                              boardFlipped: _boardFlipped,
                              selectedSquare: _selectedSquare,
                              legalMoves: _legalMoves,
                              lastMove: _isReviewMode
                                  ? (_reviewMoveIndex! > 0
                                        ? _gameState
                                              .moveHistoryObjects[_reviewMoveIndex! -
                                              1]
                                        : null)
                                  : _lastMove,
                              onSquareTapped: _onSquareTapped,
                              enabled:
                                  _gameState.isPlayerTurn &&
                                  !_gameState.isEngineThinking &&
                                  !_isReviewMode,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      _buildPlayerLabel(isTop: false),
                    ],
                  ),
                ),
              ),
              // Right info panel
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

  Widget _buildVerticalEvalBar(double boardHeight) {
    final cp = _engineRawInfo['eval_cp'] as int? ?? 0;
    return SizedBox(
      height: boardHeight,
      child: EvalBar(evalCp: cp, isVertical: true),
    );
  }

  // ──────────────────────────────────────────────────────
  // Portrait Layout (primary phone layout)
  // ──────────────────────────────────────────────────────
  Widget _buildPortraitLayout(BoxConstraints constraints) {
    return Stack(
      children: [
        // Main scrollable content
        SingleChildScrollView(
          child: Column(
            children: [
              _buildTitleBar(),
              const SizedBox(height: 4),
              // Top player label (opponent)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: _buildPlayerLabel(isTop: true),
              ),
              const SizedBox(height: 6),
              // Board + Eval bar in a Row
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Vertical eval bar
                    SizedBox(
                      width: 24,
                      child: AspectRatio(
                        aspectRatio: 1 / 8,
                        child: EvalBar(
                          evalCp: _engineRawInfo['eval_cp'] as int? ?? 0,
                          isVertical: true,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    // Board
                    Expanded(
                      child: ChessBoardWidget(
                        board: _isReviewMode
                            ? _gameState.getBoardAtMove(_reviewMoveIndex!)
                            : _gameState.board,
                        boardFlipped: _boardFlipped,
                        selectedSquare: _selectedSquare,
                        legalMoves: _legalMoves,
                        lastMove: _isReviewMode
                            ? (_reviewMoveIndex! > 0
                                  ? _gameState
                                        .moveHistoryObjects[_reviewMoveIndex! -
                                        1]
                                  : null)
                            : _lastMove,
                        onSquareTapped: _onSquareTapped,
                        enabled:
                            _gameState.isPlayerTurn &&
                            !_gameState.isEngineThinking &&
                            !_isReviewMode,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 6),
              // Bottom player label (you)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: _buildPlayerLabel(isTop: false),
              ),
              const SizedBox(height: 8),
              // Coach comments text box
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: _buildCoachTextBox(),
              ),
              // Bottom padding to prevent overlap with action bar
              const SizedBox(height: 80),
            ],
          ),
        ),
        // Fixed action bar at bottom
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.surface,
              border: Border(
                top: BorderSide(
                  color: AppColors.textMuted.withValues(alpha: 0.1),
                ),
              ),
            ),
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
            child: _buildCompactActions(),
          ),
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────
  // Coach Text Box
  // ──────────────────────────────────────────────────────
  Widget _buildCoachTextBox() {
    if (_lastCoachData == null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: AppColors.textMuted.withValues(alpha: 0.12),
          ),
        ),
        child: Text(
          _gameState.isEngineThinking
              ? 'Engine is thinking...'
              : 'Make a move to get coach feedback.',
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
            fontStyle: FontStyle.italic,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      );
    }

    final comment = (_lastCoachData!['comment'] ?? '').toString().trim();
    final category = (_lastCoachData!['category'] ?? 'DEVELOPMENT').toString();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.accent.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.lightbulb_outline, size: 14, color: AppColors.accent),
              const SizedBox(width: 6),
              Text(
                category,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.accent,
                  fontWeight: FontWeight.w700,
                  fontSize: 10,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            comment.isEmpty
                ? 'Keep improving piece activity and king safety.'
                : comment,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textPrimary,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  // ──────────────────────────────────────────────────────
  // Coach area (below board in portrait)
  // ──────────────────────────────────────────────────────
  List<Map<String, dynamic>>? _normalizeAlternatives(dynamic raw) {
    if (raw is! List) return null;
    final out = <Map<String, dynamic>>[];
    for (final item in raw) {
      if (item is! Map) continue;
      final sanRaw = item['san'];
      final evalRaw = item['eval_cp'];
      if (sanRaw == null) continue;
      final evalCp = evalRaw is num
          ? evalRaw.toInt()
          : int.tryParse('$evalRaw') ?? 0;
      out.add({'san': sanRaw.toString(), 'eval_cp': evalCp});
    }
    return out;
  }

  Widget _buildStatusBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.12)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: _gameState.isEngineThinking
                      ? Colors.orangeAccent
                      : AppColors.primary,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                _gameState.isEngineThinking
                    ? 'Engine thinking...'
                    : _gameState.statusText,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          if (_engineRawInfo.containsKey('eval_cp'))
            Text(
              _formatEval(_engineRawInfo['eval_cp'] as int? ?? 0),
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
                fontFamily: 'monospace',
              ),
            ),
        ],
      ),
    );
  }

  String _formatEval(int cp) {
    if (cp.abs() >= 90000) {
      final m = (100000 - cp.abs() + 1) ~/ 2;
      return cp > 0 ? '+M$m' : '-M$m';
    }
    final v = cp / 100.0;
    return v >= 0 ? '+${v.toStringAsFixed(1)}' : v.toStringAsFixed(1);
  }

  String _buildFallbackCoachComment({
    required int deltaCp,
    required String playedSan,
    String? bestMoveSan,
  }) {
    if (deltaCp <= -180) {
      if (bestMoveSan != null) {
        return 'That move allowed a big swing. Consider $bestMoveSan to stay safer and keep pressure.';
      }
      return 'That move allowed a big swing. Scan checks, captures, and threats before committing.';
    }

    if (deltaCp <= -70) {
      if (bestMoveSan != null) {
        return 'Playable, but less accurate. $bestMoveSan keeps better control of key squares.';
      }
      return 'Playable, but less accurate. Improve your least active piece and reduce tactical risks.';
    }

    if (deltaCp >= 90) {
      return '$playedSan is strong. You gained activity and practical pressure.';
    }

    return '$playedSan is a reasonable move. Keep coordinating pieces and contesting the center.';
  }

  // ──────────────────────────────────────────────────────
  // Compact bottom action bar (portrait)
  // ──────────────────────────────────────────────────────
  Widget _buildCompactActions() {
    return Row(
      children: [
        _compactBtn(Icons.history, 'History', _showHistorySheet),
        const SizedBox(width: 8),
        _compactBtn(
          _gameState.isGameOver ? Icons.add : Icons.undo,
          _gameState.isGameOver ? 'New' : 'Undo',
          _gameState.isGameOver
              ? _newGame
              : (_gameState.moveHistory.length >= 2 &&
                        !_gameState.isEngineThinking
                    ? _undoMove
                    : null),
          color: _gameState.isGameOver ? AppColors.accent : null,
        ),
        const SizedBox(width: 8),
        _compactBtn(
          Icons.flip,
          'Flip',
          () => setState(() => _boardFlipped = !_boardFlipped),
        ),
        const SizedBox(width: 8),
        if (_gameState.isGameOver && _gameState.moveHistory.isNotEmpty)
          _compactBtn(
            Icons.analytics_outlined,
            'Analyze',
            _openAnalysis,
            color: AppColors.accent,
          )
        else
          _compactBtn(
            _gameState.isGameOver ? Icons.flag_outlined : Icons.outlined_flag,
            _gameState.isGameOver ? 'Done' : 'Resign',
            _gameState.isGameOver
                ? () => Navigator.of(context).popUntil((r) => r.isFirst)
                : _showResignDialog,
            color: AppColors.error.withValues(alpha: 0.8),
          ),
      ],
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
            padding: const EdgeInsets.symmetric(vertical: 9),
            decoration: BoxDecoration(
              color: AppColors.card,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: AppColors.textMuted.withValues(alpha: 0.12),
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

  // ──────────────────────────────────────────────────────
  // History Bottom Sheet
  // ──────────────────────────────────────────────────────
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
                          Tab(text: 'Engine Stats'),
                        ],
                      ),
                      Expanded(
                        child: TabBarView(
                          children: [
                            // Move History tab
                            MoveHistoryPanel(
                              moves: _gameState.moveHistory,
                              scrollController: scrollController,
                              selectedIndex: _reviewMoveIndex,
                              onMoveTap: _goToMove,
                              moveCategories: _gameState.moveCategories,
                            ),
                            // Engine Stats tab
                            _buildEngineStatsSheet(),
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

  Widget _buildEngineStatsSheet() {
    if (_engineRawInfo.isEmpty) {
      return Center(
        child: Text(
          'No engine data yet.',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textMuted),
        ),
      );
    }
    final rows = <(String, String)>[
      ('Eval (cp)', (_engineRawInfo['eval_cp'] ?? '-').toString()),
      ('Depth', (_engineRawInfo['depth'] ?? '-').toString()),
      (
        'Time (s)',
        ((_engineRawInfo['time_ms'] as int? ?? 0) / 1000.0).toStringAsFixed(2),
      ),
      ('Nodes', (_engineRawInfo['nodes'] ?? '-').toString()),
    ];
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: rows.map((r) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    r.$1,
                    style: AppTextStyles.bodyMedium.copyWith(
                      color: AppColors.textMuted,
                    ),
                  ),
                ),
                Text(
                  r.$2,
                  style: AppTextStyles.bodyMedium.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  // ──────────────────────────────────────────────────────
  // Title Bar
  // ──────────────────────────────────────────────────────
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
          if (widget.enableCoachMode)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              margin: const EdgeInsets.only(right: 8),
              decoration: BoxDecoration(
                color: AppColors.accent.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.lightbulb_outline,
                    size: 12,
                    color: AppColors.accent,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Coach',
                    style: AppTextStyles.labelSmall.copyWith(
                      color: AppColors.accent,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                    ),
                  ),
                ],
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

  // ──────────────────────────────────────────────────────
  // Player Label
  // ──────────────────────────────────────────────────────
  Widget _buildPlayerLabel({required bool isTop}) {
    final isEngine = isTop;
    final isWhiteSide = isTop ? !widget.playerIsWhite : widget.playerIsWhite;
    final label = isEngine ? 'Engine' : 'You';
    final colorLetter = isWhiteSide ? 'W' : 'B';
    final timeLeft = isWhiteSide ? _whiteTimeLeft : _blackTimeLeft;

    return Row(
      children: [
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
                fontSize: 13,
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
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
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
                fontSize: 17,
              ),
            ),
          ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────
  // Wide layout right panel
  // ──────────────────────────────────────────────────────
  Widget _buildInfoPanel() {
    return Column(
      children: [
        // Move history + playback controls
        Expanded(
          flex: 3,
          child: Column(
            children: [
              Expanded(
                child: MoveHistoryPanel(
                  moves: _gameState.moveHistory,
                  scrollController: _moveScrollController,
                  selectedIndex: _reviewMoveIndex,
                  onMoveTap: _goToMove,
                  moveCategories: _gameState.moveCategories,
                ),
              ),
              const SizedBox(height: 8),
              _buildPlaybackControls(),
            ],
          ),
        ),
        const SizedBox(height: 12),
        // Coach feedback or engine stats
        Expanded(flex: 4, child: _buildCoachPanelWide()),
        const SizedBox(height: 12),
        _buildWideActionButtons(),
      ],
    );
  }

  Widget _buildCoachPanelWide() {
    if (_lastCoachData == null) {
      return Container(
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
            Text(
              'COACH FEEDBACK',
              style: AppTextStyles.labelSmall.copyWith(
                letterSpacing: 1.2,
                color: AppColors.textMuted,
              ),
            ),
            const Spacer(),
            Center(
              child: Text(
                _gameState.isEngineThinking
                    ? 'Analyzing...'
                    : 'Waiting for your next move.',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textMuted,
                ),
                textAlign: TextAlign.center,
              ),
            ),
            const Spacer(),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      child: CoachFeedbackPanel(
        category: (_lastCoachData!['category'] ?? 'DEVELOPMENT').toString(),
        comment: (_lastCoachData!['comment'] ?? '').toString(),
        bestAlternativeSan: _lastCoachData!['bestSan']?.toString(),
        alternatives: _normalizeAlternatives(_lastCoachData!['alternatives']),
      ),
    );
  }

  Widget _buildEngineEvalWide() {
    final rows = <(String, String)>[];
    if (_engineRawInfo.isNotEmpty) {
      rows.addAll([
        ('Eval (cp)', (_engineRawInfo['eval_cp'] ?? '-').toString()),
        ('Depth', (_engineRawInfo['depth'] ?? '-').toString()),
        (
          'Time (s)',
          ((_engineRawInfo['time_ms'] as int? ?? 0) / 1000.0).toStringAsFixed(
            2,
          ),
        ),
        ('Nodes', (_engineRawInfo['nodes'] ?? '-').toString()),
      ]);
    }
    return Container(
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
          Text(
            'ENGINE EVALUATION',
            style: AppTextStyles.labelSmall.copyWith(
              letterSpacing: 1.2,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 10),
          if (rows.isEmpty)
            Expanded(
              child: Center(
                child: Text(
                  'No data yet.',
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textMuted,
                  ),
                ),
              ),
            )
          else
            ...rows.map(
              (r) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        r.$1,
                        style: AppTextStyles.bodyMedium.copyWith(
                          color: AppColors.textMuted,
                        ),
                      ),
                    ),
                    Text(
                      r.$2,
                      style: AppTextStyles.bodyMedium.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildPlaybackControls() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _pbBtn(
          Icons.first_page,
          _gameState.moveHistory.isNotEmpty ? _goToFirstMove : null,
        ),
        const SizedBox(width: 6),
        _pbBtn(
          Icons.chevron_left,
          _reviewMoveIndex != 0 && _gameState.moveHistory.isNotEmpty
              ? _goToPreviousMove
              : null,
        ),
        const SizedBox(width: 6),
        _pbBtn(Icons.chevron_right, _isReviewMode ? _goToNextMove : null),
        const SizedBox(width: 6),
        _pbBtn(Icons.last_page, _isReviewMode ? _goToLastMove : null),
      ],
    );
  }

  Widget _pbBtn(IconData icon, VoidCallback? onTap) {
    final disabled = onTap == null;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 150),
        opacity: disabled ? 0.3 : 1.0,
        child: Container(
          width: 34,
          height: 34,
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: AppColors.textMuted.withValues(alpha: 0.15),
            ),
          ),
          child: Icon(icon, size: 18, color: AppColors.textPrimary),
        ),
      ),
    );
  }

  Widget _buildWideActionButtons() {
    return Column(
      children: [
        if (!_gameState.isGameOver)
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: _showResignDialog,
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
        if (_gameState.isGameOver) ...[
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
          if (_gameState.moveHistory.isNotEmpty) ...[
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _openAnalysis,
                icon: const Icon(Icons.analytics_outlined, size: 18),
                label: Text('Analyze Game', style: AppTextStyles.button),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.accent,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
          ],
        ],
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _wideSmallBtn(
                Icons.undo,
                'Undo',
                _gameState.moveHistory.length >= 2 &&
                        !_gameState.isEngineThinking
                    ? _undoMove
                    : null,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _wideSmallBtn(
                Icons.flip,
                'Flip',
                () => setState(() => _boardFlipped = !_boardFlipped),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _wideSmallBtn(IconData icon, String label, VoidCallback? onTap) {
    final disabled = onTap == null;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 200),
        opacity: disabled ? 0.3 : 1.0,
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
