import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

/// Scrollable move history panel showing SAN notation.
class MoveHistoryPanel extends StatelessWidget {
  final List<String> moves;
  final ScrollController? scrollController;

  const MoveHistoryPanel({
    super.key,
    required this.moves,
    this.scrollController,
  });

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
    final pairs = <({int number, String white, String? black})>[];
    for (int i = 0; i < moves.length; i += 2) {
      pairs.add((
        number: (i ~/ 2) + 1,
        white: moves[i],
        black: (i + 1 < moves.length) ? moves[i + 1] : null,
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
                  child: Text(
                    pair.white,
                    style: AppTextStyles.bodyMedium.copyWith(
                      color: isLast && pair.black == null
                          ? AppColors.primary
                          : AppColors.textPrimary,
                      fontWeight: isLast && pair.black == null
                          ? FontWeight.w600
                          : FontWeight.w400,
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    pair.black ?? '',
                    style: AppTextStyles.bodyMedium.copyWith(
                      color: isLast && pair.black != null
                          ? AppColors.primary
                          : AppColors.textPrimary,
                      fontWeight: isLast && pair.black != null
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
    );
  }
}
