import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

/// Scrollable move history panel showing SAN notation and optional annotations.
class MoveHistoryPanel extends StatelessWidget {
  final List<String> moves;
  final ScrollController? scrollController;
  final int? selectedIndex;
  final ValueChanged<int>? onMoveTap;
  final List<String?>? moveCategories;

  const MoveHistoryPanel({
    super.key,
    required this.moves,
    this.scrollController,
    this.selectedIndex,
    this.onMoveTap,
    this.moveCategories,
  });

  Widget _buildMoveContent(String move, String? category, bool isSelected, bool isLast) {
    Color textColor = isLast && selectedIndex == null
        ? AppColors.primary
        : (isSelected ? AppColors.primary : AppColors.textPrimary);
    FontWeight weight = (isLast || isSelected) ? FontWeight.w600 : FontWeight.w400;

    if (category == null) {
      return Text(move, style: AppTextStyles.bodyMedium.copyWith(color: textColor, fontWeight: weight));
    }

    Color catColor;
    IconData? catIcon;
    switch (category) {
      case 'MATE': catColor = const Color(0xFF39D98A); catIcon = Icons.emoji_events; break;
      case 'GREAT_MOVE': catColor = const Color(0xFF28C76F); catIcon = Icons.star; break;
      case 'NICE_CAPTURE': catColor = const Color(0xFF2DCE89); catIcon = Icons.bolt; break;
      case 'CHECK': catColor = const Color(0xFF00B8D9); catIcon = Icons.warning_amber_rounded; break;
      case 'NOT_GOOD_MOVE': catColor = const Color(0xFFF6C453); catIcon = Icons.help_outline; break;
      case 'BLUNDER': catColor = const Color(0xFFFF6B6B); catIcon = Icons.error_outline; break;
      case 'INACCURACY': catColor = const Color(0xFFF6C453); catIcon = Icons.help_outline; break;
      case 'GOOD_MOVE': catColor = const Color(0xFF2DCE89); catIcon = Icons.thumb_up_alt_outlined; break;
      case 'BEST_MOVE': catColor = AppColors.primary; catIcon = Icons.military_tech; break;
      default: catColor = Colors.transparent; catIcon = null;
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(move, style: AppTextStyles.bodyMedium.copyWith(color: textColor, fontWeight: weight)),
        if (catIcon != null) ...[
          const SizedBox(width: 4),
          Icon(catIcon, size: 14, color: catColor),
        ]
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (moves.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Center(
          child: Text('No moves yet', style: AppTextStyles.bodyMedium),
        ),
      );
    }

    // Group moves into pairs (white + black)
    final pairs = <({int number, String white, String? black, String? whiteCategory, String? blackCategory})>[];
    for (int i = 0; i < moves.length; i += 2) {
      pairs.add((
        number: (i ~/ 2) + 1,
        white: moves[i],
        black: (i + 1 < moves.length) ? moves[i + 1] : null,
        whiteCategory: (moveCategories != null && i < moveCategories!.length) ? moveCategories![i] : null,
        blackCategory: (moveCategories != null && i + 1 < moveCategories!.length) ? moveCategories![i + 1] : null,
      ));
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(12),
      ),
      child: ListView.builder(
        controller: scrollController,
        shrinkWrap: true,
        itemCount: pairs.length,
        itemBuilder: (context, index) {
          final pair = pairs[index];
          final isLast = index == pairs.length - 1;
          return Container(
            padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
            decoration: BoxDecoration(
              color: index % 2 == 0
                  ? Colors.transparent
                  : AppColors.surface.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Row(
              children: [
                SizedBox(
                  width: 32,
                  child: Text(
                    '${pair.number}.',
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.textMuted,
                    ),
                  ),
                ),
                Expanded(
                  child: InkWell(
                    onTap: () => onMoveTap?.call(index * 2),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                      decoration: BoxDecoration(
                        color: selectedIndex == index * 2
                            ? AppColors.primary.withValues(alpha: 0.2)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: _buildMoveContent(
                        pair.white,
                        pair.whiteCategory,
                        selectedIndex == index * 2,
                        isLast && pair.black == null,
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: pair.black != null
                      ? InkWell(
                          onTap: () => onMoveTap?.call(index * 2 + 1),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                            decoration: BoxDecoration(
                              color: selectedIndex == index * 2 + 1
                                  ? AppColors.primary.withValues(alpha: 0.2)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: _buildMoveContent(
                              pair.black!,
                              pair.blackCategory,
                              selectedIndex == index * 2 + 1,
                              isLast && pair.black != null,
                            ),
                          ),
                        )
                      : const SizedBox.shrink(),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
