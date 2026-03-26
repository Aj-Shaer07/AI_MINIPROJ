import 'package:flutter/material.dart';

/// App color palette — dark mode with gold/amber accents.
class AppColors {
  AppColors._();

  // Backgrounds
  static const Color background = Color(0xFF0D0D0D);
  static const Color surface = Color(0xFF1A1A1A);
  static const Color surfaceLight = Color(0xFF222222);
  static const Color card = Color(0xFF1E1E1E);

  // Accents (shifted to green theme)
  static const Color primary = Color(0xFF52C98A); // Fresh green
  static const Color primaryLight = Color(0xFF7FE3AE);
  static const Color secondary = Color(0xFF2F9E6F); // Deep green accent
  static const Color accent = Color(0xFF00D4AA); // Teal green

  // Text
  static const Color textPrimary = Color(0xFFF5F5F5);
  static const Color textSecondary = Color(0xFFB0B0B0);
  static const Color textMuted = Color(0xFF6A6A6A);

  // Board
  static const Color boardLight = Color(0xFFF0D9B5);
  static const Color boardDark = Color(0xFFB58863);
  static const Color boardHighlight = Color(0x6646B888);
  static const Color boardLastMove = Color(0x4452C98A);
  static const Color boardCheck = Color(0xFFE53E3E);
  static const Color moveDot = Color(0x5546B888);
  static const Color captureRing = Color(0x6646B888);

  // Status
  static const Color success = Color(0xFF48BB78);
  static const Color warning = Color(0xFFECC94B);
  static const Color error = Color(0xFFFC8181);

  // Gradients
  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0D0D0D), Color(0xFF141414), Color(0xFF1A1A1A)],
  );

  static const LinearGradient cardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF1E1E1E), Color(0xFF252525)],
  );

  static const LinearGradient goldGradient = LinearGradient(
    colors: [Color(0xFF52C98A), Color(0xFF7FE3AE), Color(0xFF52C98A)],
  );
}
