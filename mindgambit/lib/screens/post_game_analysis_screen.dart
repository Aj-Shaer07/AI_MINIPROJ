import 'package:flutter/material.dart';
import 'package:chess/chess.dart' as chess;
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../models/game_state.dart';
import '../widgets/chess_board_widget.dart';
import '../widgets/eval_bar.dart';
import '../widgets/coach_feedback_panel.dart';
import '../engine/evaluation.dart';

/// Full post-game analysis screen.
/// Shows every move with category annotations, allows walking through the game,
/// displays per-move coach feedback, and summarizes blunders/good moves.
class PostGameAnalysisScreen extends StatefulWidget {
  final GameState gameState;

  const PostGameAnalysisScreen({super.key, required this.gameState});

  @override
  State<PostGameAnalysisScreen> createState() => _PostGameAnalysisScreenState();
}

class _PostGameAnalysisScreenState extends State<PostGameAnalysisScreen> {
  int _selectedMoveIndex = -1; // -1 = before any move (start position)
  final ScrollController _moveListScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // Start at last move
    if (widget.gameState.moveHistory.isNotEmpty) {
      _selectedMoveIndex = widget.gameState.moveHistory.length - 1;
    }
  }

  @override
  void dispose() {
    _moveListScrollController.dispose();
    super.dispose();
  }

  chess.Chess get _currentBoard {
    if (_selectedMoveIndex < 0) {
      return chess.Chess.fromFEN(widget.gameState.initialFen);
    }
    return widget.gameState.getBoardAtMove(_selectedMoveIndex + 1);
  }

  chess.Move? get _lastMoveOnBoard {
    if (_selectedMoveIndex < 0) return null;
    final objs = widget.gameState.moveHistoryObjects;
    if (_selectedMoveIndex < objs.length) return objs[_selectedMoveIndex];
    return null;
  }

  int get _evalCp {
    try {
      return evaluate(_currentBoard);
    } catch (_) {
      return 0;
    }
  }

  // ── Summary stats ─────────────────────────────────
  int get _blunderCount =>
      widget.gameState.moveCategories.where((c) => c == 'BLUNDER').length;
  int get _inaccuracyCount => widget.gameState.moveCategories
      .where((c) => c == 'NOT_GOOD_MOVE' || c == 'INACCURACY')
      .length;
  int get _goodMoveCount => widget.gameState.moveCategories
      .where((c) => c == 'GOOD_MOVE' || c == 'GREAT_MOVE' || c == 'BEST_MOVE')
      .length;

  // ── Navigation ─────────────────────────────────────
  void _goTo(int index) {
    setState(() => _selectedMoveIndex = index);
    _scrollToMove(index);
  }

  void _prev() {
    if (_selectedMoveIndex > -1) _goTo(_selectedMoveIndex - 1);
  }

  void _next() {
    if (_selectedMoveIndex < widget.gameState.moveHistory.length - 1) {
      _goTo(_selectedMoveIndex + 1);
    }
  }

  void _scrollToMove(int index) {
    if (!_moveListScrollController.hasClients) return;
    // Each pair row is ~40 dp high. Pair index = index ~/ 2.
    final pairIndex = index ~/ 2;
    final offset = pairIndex * 40.0;
    _moveListScrollController.animateTo(
      offset.clamp(0, _moveListScrollController.position.maxScrollExtent),
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeOut,
    );
  }

  // ── Category colour helpers ─────────────────────────
  static const Map<String, Color> _catColors = {
    'MATE': Color(0xFF39D98A),
    'GREAT_MOVE': Color(0xFF28C76F),
    'NICE_CAPTURE': Color(0xFF2DCE89),
    'CHECK': Color(0xFF00B8D9),
    'NOT_GOOD_MOVE': Color(0xFFF6C453),
    'BLUNDER': Color(0xFFFF6B6B),
    'INACCURACY': Color(0xFFF6C453),
    'GOOD_MOVE': Color(0xFF2DCE89),
    'BEST_MOVE': AppColors.primary,
    'DEVELOPMENT': Color(0xFF8BD3FF),
    'ENGINE_REASON': Color(0xFF5DADE2),
  };

  static const Map<String, IconData> _catIcons = {
    'MATE': Icons.emoji_events,
    'GREAT_MOVE': Icons.star,
    'NICE_CAPTURE': Icons.bolt,
    'CHECK': Icons.warning_amber_rounded,
    'NOT_GOOD_MOVE': Icons.help_outline,
    'BLUNDER': Icons.error_outline,
    'INACCURACY': Icons.help_outline,
    'GOOD_MOVE': Icons.thumb_up_alt_outlined,
    'BEST_MOVE': Icons.military_tech,
    'DEVELOPMENT': Icons.school_outlined,
    'ENGINE_REASON': Icons.psychology,
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppColors.backgroundGradient),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(),
              _buildSummaryBar(),
              Expanded(
                child: LayoutBuilder(
                  builder: (ctx, constraints) {
                    if (constraints.maxWidth > 700) {
                      return _buildWideLayout();
                    }
                    return _buildPortraitLayout();
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Header ─────────────────────────────────────────
  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
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
            'Game Analysis',
            style: AppTextStyles.headlineMedium.copyWith(
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
              '${widget.gameState.moveHistory.length} moves',
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

  // ── Summary Bar ─────────────────────────────────────
  Widget _buildSummaryBar() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.1)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _summaryChip(
            icon: Icons.error_outline,
            label: 'Blunders',
            count: _blunderCount,
            color: const Color(0xFFFF6B6B),
          ),
          _summaryDivider(),
          _summaryChip(
            icon: Icons.help_outline,
            label: 'Inaccuracies',
            count: _inaccuracyCount,
            color: const Color(0xFFF6C453),
          ),
          _summaryDivider(),
          _summaryChip(
            icon: Icons.thumb_up_alt_outlined,
            label: 'Good Moves',
            count: _goodMoveCount,
            color: const Color(0xFF2DCE89),
          ),
        ],
      ),
    );
  }

  Widget _summaryDivider() => Container(
    width: 1,
    height: 32,
    color: AppColors.textMuted.withValues(alpha: 0.15),
  );

  Widget _summaryChip({
    required IconData icon,
    required String label,
    required int count,
    required Color color,
  }) {
    return Column(
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 4),
            Text(
              '$count',
              style: AppTextStyles.titleMedium.copyWith(
                color: color,
                fontWeight: FontWeight.w800,
                fontSize: 18,
              ),
            ),
          ],
        ),
        Text(
          label,
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textMuted,
            fontSize: 10,
          ),
        ),
      ],
    );
  }

  // ── Portrait Layout ─────────────────────────────────
  Widget _buildPortraitLayout() {
    return Column(
      children: [
        // Board area with eval bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Eval bar
              SizedBox(
                width: 24,
                child: AspectRatio(
                  aspectRatio: 1 / 8,
                  child: EvalBar(evalCp: _evalCp, isVertical: true),
                ),
              ),
              const SizedBox(width: 8),
              // Board
              Expanded(
                child: ChessBoardWidget(
                  board: _currentBoard,
                  boardFlipped: !widget.gameState.playerIsWhite,
                  selectedSquare: null,
                  legalMoves: const [],
                  lastMove: _lastMoveOnBoard,
                  onSquareTapped: (_) {},
                  enabled: false,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        // Nav controls
        _buildNavControls(),
        const SizedBox(height: 8),
        // Coach feedback for selected move
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildSelectedMoveCard(),
        ),
        const SizedBox(height: 8),
        // Move list
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: _buildMoveList(),
          ),
        ),
      ],
    );
  }

  // ── Wide Layout ─────────────────────────────────────
  Widget _buildWideLayout() {
    return Row(
      children: [
        // Left: board + controls + coach
        Expanded(
          flex: 5,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 8, 16),
            child: Column(
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 24,
                      child: AspectRatio(
                        aspectRatio: 1 / 8,
                        child: EvalBar(evalCp: _evalCp, isVertical: true),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ChessBoardWidget(
                        board: _currentBoard,
                        boardFlipped: !widget.gameState.playerIsWhite,
                        selectedSquare: null,
                        legalMoves: const [],
                        lastMove: _lastMoveOnBoard,
                        onSquareTapped: (_) {},
                        enabled: false,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                _buildNavControls(),
                const SizedBox(height: 8),
                _buildSelectedMoveCard(),
              ],
            ),
          ),
        ),
        // Right: move list
        Expanded(
          flex: 3,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 16, 16),
            child: _buildMoveList(),
          ),
        ),
      ],
    );
  }

  // ── Nav Controls ────────────────────────────────────
  Widget _buildNavControls() {
    final hasPrev = _selectedMoveIndex > -1;
    final hasNext =
        _selectedMoveIndex < widget.gameState.moveHistory.length - 1;
    final moveNum = _selectedMoveIndex >= 0
        ? '${_selectedMoveIndex ~/ 2 + 1}${_selectedMoveIndex % 2 == 0 ? '. White' : '. Black'}'
        : 'Start';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _navBtn(Icons.first_page, () => _goTo(-1), hasPrev),
          const SizedBox(width: 8),
          _navBtn(Icons.chevron_left, _prev, hasPrev),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              moveNum,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
          ),
          const SizedBox(width: 12),
          _navBtn(Icons.chevron_right, _next, hasNext),
          const SizedBox(width: 8),
          _navBtn(
            Icons.last_page,
            () => _goTo(widget.gameState.moveHistory.length - 1),
            hasNext,
          ),
        ],
      ),
    );
  }

  Widget _navBtn(IconData icon, VoidCallback onTap, bool enabled) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 150),
        opacity: enabled ? 1.0 : 0.3,
        child: Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: AppColors.textMuted.withValues(alpha: 0.15),
            ),
          ),
          child: Icon(icon, size: 20, color: AppColors.textPrimary),
        ),
      ),
    );
  }

  // ── Selected Move Coach Card ──────────────────────────
  Widget _buildSelectedMoveCard() {
    if (_selectedMoveIndex < 0) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.1)),
        ),
        child: Text(
          'Navigate through the moves to see analysis.',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textMuted),
          textAlign: TextAlign.center,
        ),
      );
    }

    final cats = widget.gameState.moveCategories;
    final comms = widget.gameState.moveComments;
    final alts = widget.gameState.moveAlternatives;

    final cat = _selectedMoveIndex < cats.length
        ? cats[_selectedMoveIndex]
        : null;
    final comm = _selectedMoveIndex < comms.length
        ? comms[_selectedMoveIndex]
        : null;
    final rawAltList = _selectedMoveIndex < alts.length
        ? alts[_selectedMoveIndex]
        : null;
    final altList = _normalizeAlternatives(rawAltList);

    final san = widget.gameState.moveHistory[_selectedMoveIndex];
    final resolvedCat = cat ?? 'DEVELOPMENT';
    final resolvedComment = (comm ?? '').trim().isEmpty
        ? 'Review $san: try to improve piece coordination and check tactical threats before committing.'
        : comm!;

    // Extract best alternative SAN if present
    String? bestAlt;
    if (altList != null && altList.isNotEmpty) {
      bestAlt = altList.first['san']?.toString();
    }

    return CoachFeedbackPanel(
      category: resolvedCat,
      comment: resolvedComment,
      alternatives: altList,
      bestAlternativeSan: bestAlt,
    );
  }

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

  // ── Move List ────────────────────────────────────────
  Widget _buildMoveList() {
    final moves = widget.gameState.moveHistory;
    if (moves.isEmpty) {
      return Center(
        child: Text(
          'No moves recorded.',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textMuted),
        ),
      );
    }

    final cats = widget.gameState.moveCategories;

    // Build white/black move pairs.
    final pairs =
        <
          ({
            int number,
            String white,
            String? black,
            String? wCat,
            String? bCat,
          })
        >[];
    for (int i = 0; i < moves.length; i += 2) {
      pairs.add((
        number: (i ~/ 2) + 1,
        white: moves[i],
        black: i + 1 < moves.length ? moves[i + 1] : null,
        wCat: i < cats.length ? cats[i] : null,
        bCat: i + 1 < cats.length ? cats[i + 1] : null,
      ));
    }

    return Container(
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Heading
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
            child: Text(
              'MOVE LIST',
              style: AppTextStyles.labelSmall.copyWith(
                color: AppColors.textMuted,
                letterSpacing: 1.0,
              ),
            ),
          ),
          Divider(
            height: 1,
            color: AppColors.textMuted.withValues(alpha: 0.12),
          ),
          Expanded(
            child: ListView.builder(
              controller: _moveListScrollController,
              padding: const EdgeInsets.symmetric(vertical: 4),
              itemCount: pairs.length,
              itemBuilder: (context, idx) {
                final pair = pairs[idx];
                final wIdx = idx * 2;
                final bIdx = idx * 2 + 1;
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 5,
                  ),
                  decoration: BoxDecoration(
                    color: idx % 2 == 0
                        ? Colors.transparent
                        : AppColors.surface.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 28,
                        child: Text(
                          '${pair.number}.',
                          style: AppTextStyles.bodySmall.copyWith(
                            color: AppColors.textMuted,
                          ),
                        ),
                      ),
                      Expanded(child: _moveCell(pair.white, pair.wCat, wIdx)),
                      const SizedBox(width: 4),
                      Expanded(
                        child: pair.black != null
                            ? _moveCell(pair.black!, pair.bCat, bIdx)
                            : const SizedBox(),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _moveCell(String san, String? cat, int moveIdx) {
    final isSelected = moveIdx == _selectedMoveIndex;
    final color = cat != null ? (_catColors[cat] ?? AppColors.textMuted) : null;
    final icon = cat != null ? _catIcons[cat] : null;

    return GestureDetector(
      onTap: () => _goTo(moveIdx),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primary.withValues(alpha: 0.18)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: isSelected
              ? Border.all(color: AppColors.primary.withValues(alpha: 0.4))
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              san,
              style: AppTextStyles.bodyMedium.copyWith(
                color: isSelected ? AppColors.primary : AppColors.textPrimary,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            if (icon != null) ...[
              const SizedBox(width: 3),
              Icon(icon, size: 12, color: color),
            ],
          ],
        ),
      ),
    );
  }
}
