import 'package:flutter/material.dart';
import 'package:chess/chess.dart' as chess;
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../core/app_router.dart';
import '../core/constants.dart';
import '../models/difficulty.dart';

/// Data class for a preset endgame position.
class _EndgamePosition {
  final String name;
  final String fen;
  final String description;
  final IconData icon;
  final List<String> heuristics;

  const _EndgamePosition({
    required this.name,
    required this.fen,
    required this.description,
    required this.icon,
    required this.heuristics,
  });
}

const _positions = <_EndgamePosition>[
  _EndgamePosition(
    name: 'K+Q vs K',
    fen: '8/8/8/8/4k3/8/6Q1/4K3 w - - 0 1',
    description: 'Mop-up eval, depth boost +3',
    icon: Icons.star,
    heuristics: ['mop-up eval', 'depth boost', 'king-edge'],
  ),
  _EndgamePosition(
    name: 'K+R vs K',
    fen: '8/8/8/3k4/8/8/8/R3K3 w - - 0 1',
    description: 'King-edge bonus, depth boost',
    icon: Icons.castle,
    heuristics: ['mop-up eval', 'depth boost', 'king-edge'],
  ),
  _EndgamePosition(
    name: 'K+B+B vs K',
    fen: '8/8/8/3k4/8/8/2B5/2BK4 w - - 0 1',
    description: 'KBB corner driving bonus',
    icon: Icons.church,
    heuristics: ['KBB corner', 'mop-up eval'],
  ),
  _EndgamePosition(
    name: 'K+B+N vs K',
    fen: '8/8/8/3k4/8/8/1N6/2BK4 w - - 0 1',
    description: 'KBN correct-corner bonus',
    icon: Icons.pets,
    heuristics: ['KBN corner', 'mop-up eval'],
  ),
  _EndgamePosition(
    name: 'K+R+P vs K+R',
    fen: '8/5k2/8/8/4P3/8/8/R3K2r w - - 0 1',
    description: 'Passed pawn, rook behind passer',
    icon: Icons.trending_up,
    heuristics: ['passed pawn', 'rook behind passer'],
  ),
  _EndgamePosition(
    name: 'K+PP vs K',
    fen: '8/8/4k3/8/3PP3/8/8/4K3 w - - 0 1',
    description: 'Connected passers, king proximity',
    icon: Icons.people,
    heuristics: ['connected passers', 'king proximity'],
  ),
  _EndgamePosition(
    name: 'Near-Stalemate',
    fen: 'k7/2Q5/1K6/8/8/8/8/8 w - - 0 1',
    description: 'Stalemate avoidance heuristic',
    icon: Icons.warning_amber_rounded,
    heuristics: ['stalemate avoidance'],
  ),
  _EndgamePosition(
    name: '50-Move Edge',
    fen: '8/8/8/8/4k3/8/6Q1/4K3 w - - 45 60',
    description: '50-move rule score decay',
    icon: Icons.timer,
    heuristics: ['50-move decay'],
  ),
];

/// Screen for picking an endgame position and playing it against the engine.
class EndgameTestScreen extends StatefulWidget {
  const EndgameTestScreen({super.key});

  @override
  State<EndgameTestScreen> createState() => _EndgameTestScreenState();
}

class _EndgameTestScreenState extends State<EndgameTestScreen>
    with SingleTickerProviderStateMixin {
  int? _selectedIndex;
  bool _playerIsWhite = true;
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    )..forward();
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeIn);
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    super.dispose();
  }

  void _launchGame() {
    if (_selectedIndex == null) return;
    final pos = _positions[_selectedIndex!];
    Navigator.pushNamed(
      context,
      AppRouter.game,
      arguments: {
        'difficulty': Difficulty.hard, // use Hard (depth 5) for endgame testing
        'playerIsWhite': _playerIsWhite,
        'timerSeconds': 0,
        'fen': pos.fen,
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppColors.backgroundGradient),
        child: SafeArea(
          child: FadeTransition(
            opacity: _fadeAnim,
            child: Column(
              children: [
                _buildHeader(),
                Expanded(child: _buildGrid()),
                _buildBottomBar(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─── Header ──────────────────────────────────────────
  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(
              Icons.arrow_back_ios_new,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(width: 8),
          ShaderMask(
            shaderCallback: (bounds) =>
                AppColors.goldGradient.createShader(bounds),
            child: Text(
              '♚ Endgame Tester',
              style: AppTextStyles.headlineLarge.copyWith(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Position Grid ───────────────────────────────────
  Widget _buildGrid() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth > 700 ? 4 : 2;
        return GridView.builder(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            childAspectRatio: 1.0,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
          ),
          itemCount: _positions.length,
          itemBuilder: (context, index) => _buildCard(index),
        );
      },
    );
  }

  Widget _buildCard(int index) {
    final pos = _positions[index];
    final isSelected = _selectedIndex == index;

    return GestureDetector(
      onTap: () => setState(() => _selectedIndex = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
        decoration: BoxDecoration(
          gradient: isSelected ? null : AppColors.cardGradient,
          color: isSelected ? AppColors.accent.withValues(alpha: 0.15) : null,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected
                ? AppColors.accent
                : AppColors.textMuted.withValues(alpha: 0.15),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: AppColors.accent.withValues(alpha: 0.2),
                    blurRadius: 16,
                    spreadRadius: 2,
                  ),
                ]
              : [],
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top row: icon + number
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppColors.accent.withValues(alpha: 0.2)
                          : AppColors.surface,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      pos.icon,
                      size: 20,
                      color: isSelected ? AppColors.accent : AppColors.primary,
                    ),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '#${index + 1}',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textMuted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),

              const Spacer(),

              // Mini board preview
              _MiniBoard(fen: pos.fen),

              const SizedBox(height: 10),

              // Name
              Text(
                pos.name,
                style: AppTextStyles.titleMedium.copyWith(
                  color: isSelected ? AppColors.accent : AppColors.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),

              const SizedBox(height: 4),

              // Description
              Text(
                pos.description,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textMuted,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),

              const SizedBox(height: 6),

              // Heuristic chips
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: pos.heuristics.take(2).map((h) {
                  return Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppColors.accent.withValues(alpha: 0.15)
                          : AppColors.surface,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      h,
                      style: TextStyle(
                        fontSize: 9,
                        color: isSelected
                            ? AppColors.accent
                            : AppColors.textMuted,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ─── Bottom Bar ──────────────────────────────────────
  Widget _buildBottomBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(
          top: BorderSide(color: AppColors.textMuted.withValues(alpha: 0.1)),
        ),
      ),
      child: Row(
        children: [
          // Color toggle
          Text('Play as:', style: AppTextStyles.bodyMedium),
          const SizedBox(width: 10),
          _colorButton('♔ White', true),
          const SizedBox(width: 8),
          _colorButton('♚ Black', false),

          const Spacer(),

          // Selected position info
          if (_selectedIndex != null)
            Flexible(
              child: Text(
                _positions[_selectedIndex!].name,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.accent,
                  fontWeight: FontWeight.w600,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),

          const SizedBox(width: 12),

          // Play button
          ElevatedButton.icon(
            onPressed: _selectedIndex != null ? _launchGame : null,
            icon: const Icon(Icons.play_arrow_rounded, size: 22),
            label: Text('PLAY', style: AppTextStyles.button),
            style: ElevatedButton.styleFrom(
              backgroundColor: _selectedIndex != null
                  ? AppColors.accent
                  : AppColors.textMuted.withValues(alpha: 0.2),
              foregroundColor: _selectedIndex != null
                  ? Colors.black
                  : AppColors.textMuted,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _colorButton(String label, bool isWhite) {
    final selected = _playerIsWhite == isWhite;
    return GestureDetector(
      onTap: () => setState(() => _playerIsWhite = isWhite),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: selected
              ? AppColors.accent.withValues(alpha: 0.2)
              : AppColors.card,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: selected ? AppColors.accent : Colors.transparent,
            width: 1.5,
          ),
        ),
        child: Text(
          label,
          style: AppTextStyles.bodySmall.copyWith(
            color: selected ? AppColors.accent : AppColors.textSecondary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

// ─── Mini Board Widget ─────────────────────────────────
/// A tiny, non-interactive chessboard preview rendered from a FEN string.
class _MiniBoard extends StatelessWidget {
  final String fen;
  const _MiniBoard({required this.fen});

  @override
  Widget build(BuildContext context) {
    final board = chess.Chess.fromFEN(fen);

    return SizedBox(
      width: 13.0 * 8,
      height: 13.0 * 8,
      child: CustomPaint(painter: _MiniBoardPainter(board)),
    );
  }
}

class _MiniBoardPainter extends CustomPainter {
  final chess.Chess board;
  _MiniBoardPainter(this.board);

  @override
  void paint(Canvas canvas, Size size) {
    final sq = size.width / 8;

    for (int rank = 0; rank < 8; rank++) {
      for (int file = 0; file < 8; file++) {
        final x = file * sq;
        final y = rank * sq;
        final isLight = (rank + file) % 2 == 0;

        // Draw square
        canvas.drawRect(
          Rect.fromLTWH(x, y, sq, sq),
          Paint()
            ..color = isLight
                ? const Color(0xFFF0D9B5)
                : const Color(0xFFB58863),
        );

        // Draw piece using ChessPieces.getSymbol (same as main board)
        final algebraic =
            String.fromCharCode('a'.codeUnitAt(0) + file) +
            (8 - rank).toString();
        final piece = board.get(algebraic);
        if (piece != null) {
          final isWhite = piece.color == chess.Color.WHITE;
          final symbol = ChessPieces.getSymbol(piece.type.toString(), isWhite);

          final tp = TextPainter(
            text: TextSpan(
              text: symbol,
              style: TextStyle(
                fontSize: sq * 0.75,
                color: isWhite
                    ? const Color(0xFFFFF8E6)
                    : const Color(0xFF1A1510),
              ),
            ),
            textDirection: TextDirection.ltr,
          )..layout();
          tp.paint(
            canvas,
            Offset(x + (sq - tp.width) / 2, y + (sq - tp.height) / 2),
          );
        }
      }
    }

    // Border
    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()
        ..color = const Color(0xFF4A3A2A)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );
  }

  @override
  bool shouldRepaint(covariant _MiniBoardPainter old) => false;
}
