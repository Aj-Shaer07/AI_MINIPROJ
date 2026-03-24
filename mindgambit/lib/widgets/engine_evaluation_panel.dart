import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

class EngineEvaluationPanel extends StatelessWidget {
  final Map<String, dynamic> engineInfo;
  final bool enableCoachMode;
  final bool isEngineThinking;
  final bool isPortraitLayout;

  const EngineEvaluationPanel({
    super.key,
    required this.engineInfo,
    required this.enableCoachMode,
    required this.isEngineThinking,
    this.isPortraitLayout = false,
  });

  @override
  Widget build(BuildContext context) {
    if (isPortraitLayout) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: AppColors.textMuted.withValues(alpha: 0.1),
          ),
        ),
        child: Center(
          child: Text(
            'Coach explanation popup is available in portrait mode.',
            textAlign: TextAlign.center,
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textMuted,
            ),
          ),
        ),
      );
    }

    if (!enableCoachMode) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: AppColors.textMuted.withValues(alpha: 0.1),
          ),
        ),
        child: Center(
          child: Text(
            'Coach Mode is turned off for this game.',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textMuted,
            ),
          ),
        ),
      );
    }

    final hasExplanation =
        engineInfo.containsKey('explanation') &&
        engineInfo['explanation'] != null;

    if (!hasExplanation) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: AppColors.textMuted.withValues(alpha: 0.1),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '🤔 AI REASONING',
              style: AppTextStyles.labelLarge.copyWith(
                letterSpacing: 1.5,
                fontSize: 12,
              ),
            ),
            const Spacer(),
            Center(
              child: Text(
                isEngineThinking
                    ? 'Thinking...'
                    : 'No explanation available.',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textMuted,
                ),
              ),
            ),
            const Spacer(),
          ],
        ),
      );
    }

    final explanation = engineInfo['explanation'] as Map<String, dynamic>;
    final scoreCp = explanation['after_eval_cp'] as int? ?? 0;
    final gamePhase = explanation['game_phase'] as String? ?? 'Middlegame';

    String evalStr;
    if (scoreCp.abs() >= 90000) {
      final mateIn = (100000 - scoreCp.abs() + 1) ~/ 2;
      evalStr = scoreCp > 0 ? '+M$mateIn' : '-M$mateIn';
    } else {
      final pawnUnits = scoreCp / 100.0;
      evalStr = pawnUnits >= 0
          ? '+${pawnUnits.toStringAsFixed(2)}'
          : pawnUnits.toStringAsFixed(2);
    }

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.textMuted.withValues(alpha: 0.1)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 10,
              ),
              decoration: BoxDecoration(
                color: AppColors.surface,
                border: Border(
                  bottom: BorderSide(
                    color: AppColors.textMuted.withValues(alpha: 0.1),
                  ),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '🤔 AI REASONING',
                    style: AppTextStyles.labelLarge.copyWith(
                      letterSpacing: 1.5,
                      fontSize: 12,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  Text(
                    gamePhase.toUpperCase(),
                    style: AppTextStyles.labelSmall.copyWith(
                      color: AppColors.textMuted,
                      letterSpacing: 1.0,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(14),
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        evalStr,
                        style: AppTextStyles.displayMedium.copyWith(
                          color: scoreCp >= 0
                              ? Colors.greenAccent
                              : Colors.redAccent,
                          fontSize: 28,
                          height: 1.0,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 3),
                        child: Text(
                          'Depth ${engineInfo['depth'] ?? 0}',
                          style: AppTextStyles.bodySmall.copyWith(
                            color: AppColors.textMuted,
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (explanation.containsKey('move_category')) ...[
                    const SizedBox(height: 12),
                    _buildMoveCategory(explanation['move_category'] as String),
                  ],
                  const SizedBox(height: 16),
                  Text(
                    'EVALUATION COMPONENTS',
                    style: AppTextStyles.labelSmall.copyWith(
                      color: AppColors.textMuted,
                      letterSpacing: 1.0,
                    ),
                  ),
                  const SizedBox(height: 8),
                  _buildBreakdownChart(
                    explanation['full_breakdown_after']
                            as Map<String, dynamic>? ??
                        {},
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'WHY THIS MOVE?',
                    style: AppTextStyles.labelSmall.copyWith(
                      color: AppColors.textMuted,
                      letterSpacing: 1.0,
                    ),
                  ),
                  const SizedBox(height: 6),
                  _buildNarrative(
                    explanation['narrative'] as List<dynamic>? ?? [],
                  ),
                  const SizedBox(height: 16),
                  if ((engineInfo['alternatives'] as List<dynamic>?)?.isNotEmpty ?? false) ...[
                    Text(
                      'TOP ALTERNATIVES',
                      style: AppTextStyles.labelSmall.copyWith(
                        color: AppColors.textMuted,
                        letterSpacing: 1.0,
                      ),
                    ),
                    const SizedBox(height: 6),
                    _buildAlternatives(
                      engineInfo['alternatives'] as List<dynamic>? ?? [],
                    ),
                  ]
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMoveCategory(String category) {
    Color color;
    IconData icon;
    String label;
    
    switch (category) {
      case 'BLUNDER':
        color = Colors.redAccent;
        icon = Icons.error_outline;
        label = 'Blunder';
        break;
      case 'INACCURACY':
        color = Colors.orangeAccent;
        icon = Icons.warning_amber_rounded;
        label = 'Inaccuracy';
        break;
      case 'GOOD_MOVE':
        color = Colors.greenAccent;
        icon = Icons.check_circle_outline;
        label = 'Good Move';
        break;
      case 'GREAT_MOVE':
        color = Colors.blueAccent;
        icon = Icons.star_border;
        label = 'Great Move';
        break;
      case 'BEST_MOVE':
      default:
        color = AppColors.primary;
        icon = Icons.military_tech;
        label = 'Best Move';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: color,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBreakdownChart(Map<String, dynamic> bk) {
    if (bk.isEmpty) return const SizedBox();

    int material =
        (bk['material_mg_white'] ?? 0) +
        (bk['material_eg_white'] ?? 0) -
        (bk['material_mg_black'] ?? 0) -
        (bk['material_eg_black'] ?? 0);
    int pst =
        (bk['pst_mg_white'] ?? 0) +
        (bk['pst_eg_white'] ?? 0) -
        (bk['pst_mg_black'] ?? 0) -
        (bk['pst_eg_black'] ?? 0);
    int mobility =
        (bk['mobility_mg_white'] ?? 0) +
        (bk['mobility_eg_white'] ?? 0) -
        (bk['mobility_mg_black'] ?? 0) -
        (bk['mobility_eg_black'] ?? 0);
    int structure =
        (bk['passed_pawns_mg'] ?? 0) +
        (bk['passed_pawns_eg'] ?? 0) +
        (bk['isolated_pawns_mg'] ?? 0) +
        (bk['doubled_pawns_mg'] ?? 0);
    int kingSafety =
        (bk['king_shield_mg'] ?? 0) - (bk['hanging_penalty_mg'] ?? 0);

    return Column(
      children: [
        _barRow('Material', material, 500, AppColors.primary),
        _barRow('Position (PST)', pst, 100, Colors.tealAccent),
        _barRow('Mobility', mobility, 50, Colors.orangeAccent),
        _barRow('Structure', structure, 100, Colors.purpleAccent),
        _barRow('King Safety', kingSafety, 100, Colors.redAccent),
      ],
    );
  }

  Widget _barRow(String label, int val, int maxRange, Color color) {
    // Normalize -maxRange to +maxRange into 0.0 to 1.0
    // A value of 0 should be exactly 0.5 (center)
    final clamped = val.clamp(-maxRange, maxRange);
    final percent = ((clamped / maxRange) + 1.0) / 2.0;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(
            width: 90,
            child: Text(
              label,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
                fontSize: 11,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final width = constraints.maxWidth;
                final center = width / 2;
                final isPositive = percent >= 0.5;
                final barWidth = (percent - 0.5).abs() * 2 * center;

                return Stack(
                  alignment: Alignment.center,
                  children: [
                    // Background track
                    Container(
                      height: 6,
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                    // Active bar
                    Positioned(
                      left: isPositive ? center : null,
                      right: !isPositive ? center : null,
                      width: barWidth,
                      child: Container(
                        height: 6,
                        decoration: BoxDecoration(
                          color: color,
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                    ),
                    // Center line
                    Positioned(
                      child: Container(width: 2, height: 10, color: Colors.grey),
                    ),
                  ],
                );
              },
            ),
          ),
          SizedBox(
            width: 40,
            child: Text(
              val > 0 ? '+${val / 100}' : '${val / 100}',
              textAlign: TextAlign.right,
              style: AppTextStyles.bodySmall.copyWith(
                color: val >= 0 ? Colors.greenAccent : Colors.redAccent,
                fontWeight: FontWeight.w600,
                fontSize: 11,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNarrative(List<dynamic> items) {
    if (items.isEmpty) {
      return Text(
        'No detailed narrative available.',
        style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: items.map<Widget>((item) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.only(top: 6, right: 8),
                child: Icon(Icons.circle, size: 6, color: AppColors.primary),
              ),
              Expanded(
                child: Text(
                  item.toString(),
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textPrimary,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildAlternatives(List<dynamic> alts) {
    if (alts.isEmpty) return const SizedBox();
    return Column(
      children: alts.map((alt) {
        final aMap = alt as Map<String, dynamic>;
        final san = aMap['san'] ?? '?';
        final cp = aMap['eval_cp'] as int? ?? 0;
        final evalStr = cp >= 0 ? '+${cp / 100}' : '${cp / 100}';

        return Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: AppColors.surface.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                san.toString(),
                style: AppTextStyles.bodyMedium.copyWith(
                  fontWeight: FontWeight.w600,
                  fontFamily: 'monospace',
                ),
              ),
              Text(
                evalStr,
                style: AppTextStyles.bodySmall.copyWith(
                  color: cp >= 0 ? Colors.greenAccent : Colors.redAccent,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
