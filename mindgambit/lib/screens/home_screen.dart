import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../core/app_router.dart';
import '../core/constants.dart';

/// Modern landing page matching the product hero screenshot style.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with TickerProviderStateMixin {
  late AnimationController _fadeController;
  late AnimationController _glowController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 900),
      vsync: this,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOutCubic,
    );
    _fadeController.forward();

    _glowController = AnimationController(
      duration: const Duration(milliseconds: 2200),
      vsync: this,
    )..repeat(reverse: true);
    _glowAnimation = Tween<double>(begin: 0.25, end: 0.55).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _glowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF070B16),
                  Color(0xFF0B1320),
                  Color(0xFF0C1117),
                ],
              ),
            ),
          ),
          Positioned(
            left: -120,
            top: 120,
            child: AnimatedBuilder(
              animation: _glowAnimation,
              builder: (context, _) {
                return Container(
                  width: 320,
                  height: 320,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.accent.withValues(
                      alpha: _glowAnimation.value * 0.35,
                    ),
                  ),
                );
              },
            ),
          ),
          Positioned(
            right: -140,
            bottom: -40,
            child: AnimatedBuilder(
              animation: _glowAnimation,
              builder: (context, _) {
                return Container(
                  width: 360,
                  height: 360,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.primary.withValues(
                      alpha: _glowAnimation.value * 0.2,
                    ),
                  ),
                );
              },
            ),
          ),
          SafeArea(
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: Column(
                children: [
                  Container(
                    height: 56,
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.05),
                      border: Border(
                        bottom: BorderSide(
                          color: Colors.white.withValues(alpha: 0.06),
                        ),
                      ),
                    ),
                    child: Row(
                      children: [
                        Text(
                          'Chess AI',
                          style: AppTextStyles.headlineMedium.copyWith(
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Center(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 980),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              // Board at the top
                              _buildBoardPreview(360),
                              const SizedBox(height: 24),
                              _buildHeroText(),
                              const SizedBox(height: 28),
                              // Primary CTA at the bottom
                              Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  ElevatedButton(
                                    onPressed: () {
                                      Navigator.pushNamed(
                                        context,
                                        AppRouter.difficulty,
                                      );
                                    },
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: const Color(0xFF52C98A),
                                      foregroundColor: const Color(0xFF0C2318),
                                      elevation: 0,
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 32,
                                        vertical: 18,
                                      ),
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(14),
                                      ),
                                    ),
                                    child: Text(
                                      'Start Game',
                                      style: AppTextStyles.titleMedium.copyWith(
                                        color: const Color(0xFF0C2318),
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
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

  Widget _buildHeroText() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Play Chess Online',
          style: AppTextStyles.displayMedium.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w800,
            fontSize: 62,
            height: 0.96,
          ),
        ),
        const SizedBox(height: 18),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 540),
          child: Text(
            'Challenge our AI engine and sharpen your skills. Beautiful interface, smart opponent, real-time analysis.',
            style: AppTextStyles.titleLarge.copyWith(
              color: AppColors.textSecondary,
              height: 1.55,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBoardPreview(double size) {
    return Container(
      width: size,
      height: size,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.28),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 28,
            spreadRadius: 2,
          ),
          BoxShadow(
            color: AppColors.accent.withValues(alpha: 0.08),
            blurRadius: 50,
            spreadRadius: 8,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: GridView.builder(
          itemCount: 64,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 8,
          ),
          itemBuilder: (context, index) {
            final row = index ~/ 8;
            final col = index % 8;
            final isLight = (row + col).isEven;
            final symbol = _pieceSymbol(row, col);
            final isWhite = row >= 6;
            final pieceColor = isWhite
                ? const Color(0xFFFAF7EE)
                : const Color(0xFF1B1B1B);

            return Container(
              color: isLight
                  ? const Color(0xFFE9D7B8)
                  : const Color(0xFFB38963),
              child: Center(
                child: Text(
                  symbol,
                  style: AppTextStyles.titleLarge.copyWith(
                    color: pieceColor,
                    fontWeight: FontWeight.w800,
                    fontSize: 26,
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  String _pieceSymbol(int row, int col) {
    const backRank = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'];
    if (row == 0) return ChessPieces.getSymbol(backRank[col], false);
    if (row == 1) return ChessPieces.blackPawn;
    if (row == 6) return ChessPieces.whitePawn;
    if (row == 7) return ChessPieces.getSymbol(backRank[col], true);
    return '';
  }
}
