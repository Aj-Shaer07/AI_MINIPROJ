import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

/// Animated engine evaluation bar.
class EvalBar extends StatelessWidget {
  final int evalCp;
  final bool isVertical;

  const EvalBar({super.key, required this.evalCp, this.isVertical = false});

  @override
  Widget build(BuildContext context) {
    // Clamp eval to displayable range (-1000 to +1000 cp)
    final clampedEval = evalCp.clamp(-1000, 1000);
    // Convert to 0.0 .. 1.0 where 0.5 = even
    final whiteRatio = (clampedEval + 1000) / 2000;

    final evalText = _formatEval(evalCp);

    if (isVertical) {
      return Container(
        width: 28,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.2)),
        ),
        clipBehavior: Clip.antiAlias,
        child: LayoutBuilder(
          builder: (context, constraints) {
            return Stack(
              children: [
                // Black portion (top)
                Container(color: AppColors.surface),
                // White portion (bottom)
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 500),
                    curve: Curves.easeInOut,
                    height: constraints.maxHeight * whiteRatio,
                    color: AppColors.textPrimary,
                  ),
                ),
                // Eval text
                Positioned(
                  top: 4,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: RotatedBox(
                      quarterTurns: 0,
                      child: Text(
                        evalText,
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          color: whiteRatio > 0.5
                              ? AppColors.surface
                              : AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      );
    }

    // Horizontal bar
    return Container(
      height: 24,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.2)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          Container(color: AppColors.surface),
          AnimatedFractionallySizedBox(
            duration: const Duration(milliseconds: 500),
            curve: Curves.easeInOut,
            widthFactor: whiteRatio,
            child: Container(color: AppColors.textPrimary),
          ),
          Center(
            child: Text(
              evalText,
              style: AppTextStyles.bodySmall.copyWith(
                fontWeight: FontWeight.w700,
                color: whiteRatio > 0.5
                    ? AppColors.surface
                    : AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatEval(int cp) {
    if (cp.abs() >= 90000) {
      final mateIn = (100000 - cp.abs() + 1) ~/ 2;
      return cp > 0 ? '+M$mateIn' : '-M$mateIn';
    }
    final pawnUnits = cp / 100;
    return pawnUnits >= 0
        ? '+${pawnUnits.toStringAsFixed(1)}'
        : pawnUnits.toStringAsFixed(1);
  }
}
