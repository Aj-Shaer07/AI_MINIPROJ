import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

class GamePlaybackControls extends StatelessWidget {
  final VoidCallback? onFirst;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;
  final VoidCallback? onLast;

  const GamePlaybackControls({
    super.key,
    this.onFirst,
    this.onPrevious,
    this.onNext,
    this.onLast,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.15)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildBtn(Icons.first_page, onFirst),
          const SizedBox(width: 8),
          _buildBtn(Icons.navigate_before, onPrevious),
          const SizedBox(width: 8),
          _buildBtn(Icons.navigate_next, onNext),
          const SizedBox(width: 8),
          _buildBtn(Icons.last_page, onLast),
        ],
      ),
    );
  }

  Widget _buildBtn(IconData icon, VoidCallback? onTap) {
    final disabled = onTap == null;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 200),
        opacity: disabled ? 0.3 : 1.0,
        child: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, size: 24, color: AppColors.textPrimary),
        ),
      ),
    );
  }
}
