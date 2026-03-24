import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

class CoachFeedbackPanel extends StatelessWidget {
  final String category;
  final String comment;
  final List<Map<String, dynamic>>? alternatives;
  final String? bestAlternativeSan;

  const CoachFeedbackPanel({
    super.key,
    required this.category,
    required this.comment,
    this.alternatives,
    this.bestAlternativeSan,
  });

  static const Map<String, Color> _categoryColors = {
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

  static const Map<String, IconData> _categoryIcons = {
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

  static String _labelFor(String cat) {
    switch (cat) {
      case 'BLUNDER':
        return 'Blunder';
      case 'NOT_GOOD_MOVE':
        return 'Inaccuracy';
      case 'INACCURACY':
        return 'Inaccuracy';
      case 'GREAT_MOVE':
        return 'Great Move';
      case 'GOOD_MOVE':
        return 'Good Move';
      case 'BEST_MOVE':
        return 'Best Move';
      case 'NICE_CAPTURE':
        return 'Nice Capture';
      case 'CHECK':
        return 'Check';
      case 'MATE':
        return 'Checkmate';
      case 'DEVELOPMENT':
        return 'Development';
      case 'ENGINE_REASON':
        return 'Engine Reasoning';
      default:
        return cat.replaceAll('_', ' ');
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _categoryColors[category] ?? AppColors.primary;
    final icon = _categoryIcons[category] ?? Icons.chat_bubble_outline;

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(14),
        border: Border(
          left: BorderSide(color: color, width: 3),
          top: BorderSide(color: AppColors.textMuted.withValues(alpha: 0.1)),
          right: BorderSide(color: AppColors.textMuted.withValues(alpha: 0.1)),
          bottom: BorderSide(color: AppColors.textMuted.withValues(alpha: 0.1)),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Category badge + icon row
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.18),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(icon, size: 16, color: color),
                ),
                const SizedBox(width: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    _labelFor(category),
                    style: AppTextStyles.labelSmall.copyWith(
                      color: color,
                      fontWeight: FontWeight.w800,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            // Comment text
            Text(
              comment.trim().isEmpty
                  ? 'No comment generated for this move.'
                  : comment,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textPrimary,
                height: 1.45,
                fontWeight: FontWeight.w500,
              ),
            ),
            // Best alternative suggestion
            if (bestAlternativeSan != null &&
                bestAlternativeSan!.trim().isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 7,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: AppColors.primary.withValues(alpha: 0.25),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.lightbulb_outline,
                      size: 15,
                      color: AppColors.primary,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Possible better move: ',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textMuted,
                      ),
                    ),
                    Text(
                      bestAlternativeSan!,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
            ],
            // Additional alternatives
            if (alternatives != null && alternatives!.isNotEmpty) ...[
              const SizedBox(height: 10),
              Divider(
                height: 1,
                color: AppColors.textMuted.withValues(alpha: 0.15),
              ),
              const SizedBox(height: 8),
              Text(
                'TOP ALTERNATIVES',
                style: AppTextStyles.labelSmall.copyWith(
                  color: AppColors.textMuted,
                  letterSpacing: 0.8,
                  fontSize: 10,
                ),
              ),
              const SizedBox(height: 6),
              ...alternatives!.take(3).map((alt) {
                final san = alt['san'] ?? '?';
                final rawCp = alt['eval_cp'];
                final cp = rawCp is num
                    ? rawCp.toInt()
                    : int.tryParse('$rawCp') ?? 0;
                final evalVal = (cp / 100.0).toStringAsFixed(1);
                final evalStr = cp >= 0 ? '+$evalVal' : evalVal;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 7,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          san.toString(),
                          style: AppTextStyles.bodySmall.copyWith(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        evalStr,
                        style: AppTextStyles.bodySmall.copyWith(
                          color: cp >= 0
                              ? Colors.greenAccent
                              : Colors.redAccent,
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ] else ...[
              const SizedBox(height: 10),
              Text(
                'No stronger alternative found for this move at current depth.',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textMuted,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
