import 'package:flutter/material.dart';

import '../core/constants.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../engine/explainer.dart';

class ExplainPopup extends StatelessWidget {
  final Map<String, dynamic>? explanationData;
  final bool visible;

  const ExplainPopup({
    super.key,
    required this.explanationData,
    required this.visible,
  });

  static const Duration popupDuration = Duration(milliseconds: 5000);

  static const Map<String, Color> _accentColors = {
    Explainer.keyMate: Color(0xFF39D98A),
    Explainer.keyGreatMove: Color(0xFF28C76F),
    Explainer.keyNiceCapture: Color(0xFF2DCE89),
    Explainer.keyCheck: Color(0xFF00B8D9),
    Explainer.keyNotGoodMove: Color(0xFFF6C453),
    Explainer.keyBlunder: Color(0xFFFF6B6B),
    'DEVELOPMENT': Color(0xFF8BD3FF),
    'ENGINE_REASON': Color(0xFF5DADE2),
  };

  @override
  Widget build(BuildContext context) {
    final key = explanationData?['key'] as String?;
    final message = explanationData?['text'] as String?;
    final piece = (explanationData?['piece'] as String? ?? 'n').toLowerCase();

    final show = visible && message != null && message.isNotEmpty;
    final accent = _accentColors[key] ?? AppColors.primary;
    final pieceSymbol = ChessPieces.getSymbol(piece, true);

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      child: !show
          ? const SizedBox.shrink()
          : Container(
              key: ValueKey<String>(key ?? 'none'),
              width: double.infinity,
              constraints: const BoxConstraints(minHeight: 60),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    const Color(0xFF191A1F),
                    accent.withValues(alpha: 0.13),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: accent.withValues(alpha: 0.75)),
                boxShadow: [
                  BoxShadow(
                    color: accent.withValues(alpha: 0.2),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Container(
                    width: 34,
                    height: 34,
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                    ),
                    child: Center(
                      child: Text(
                        pieceSymbol,
                        style: AppTextStyles.titleLarge.copyWith(
                          color: accent,
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      message,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.bodyMedium.copyWith(
                        color: AppColors.textPrimary,
                        height: 1.25,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
