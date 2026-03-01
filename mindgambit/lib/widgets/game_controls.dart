import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

/// Row of game control buttons.
class GameControls extends StatelessWidget {
  final VoidCallback onNewGame;
  final VoidCallback onUndo;
  final VoidCallback onResign;
  final VoidCallback onFlipBoard;
  final bool canUndo;
  final bool gameOver;

  const GameControls({
    super.key,
    required this.onNewGame,
    required this.onUndo,
    required this.onResign,
    required this.onFlipBoard,
    required this.canUndo,
    required this.gameOver,
  });

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: [
        _buildButton(
          icon: Icons.add,
          label: 'New',
          onTap: onNewGame,
          color: AppColors.accent,
        ),
        _buildButton(
          icon: Icons.undo,
          label: 'Undo',
          onTap: canUndo ? onUndo : null,
          color: AppColors.primary,
        ),
        _buildButton(
          icon: Icons.flip,
          label: 'Flip',
          onTap: onFlipBoard,
          color: AppColors.secondary,
        ),
        if (!gameOver)
          _buildButton(
            icon: Icons.flag,
            label: 'Resign',
            onTap: onResign,
            color: AppColors.error,
          ),
      ],
    );
  }

  Widget _buildButton({
    required IconData icon,
    required String label,
    VoidCallback? onTap,
    Color color = AppColors.primary,
  }) {
    final isDisabled = onTap == null;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 200),
        opacity: isDisabled ? 0.3 : 1.0,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: color.withValues(alpha: 0.3)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 18, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: AppTextStyles.bodySmall.copyWith(
                  color: color,
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
