import 'package:flutter/material.dart';

/// App color palette — dark mode with gold/amber accents.
class AppColors {
  AppColors._();

  // Backgrounds
  static const Color background = Color(0xFF0D0D0D);
  static const Color surface = Color(0xFF1A1A2E);
  static const Color surfaceLight = Color(0xFF16213E);
  static const Color card = Color(0xFF1E1E30);

  // Accents
  static const Color primary = Color(0xFFE2B714); // Gold
  static const Color primaryLight = Color(0xFFF5D565);
  static const Color secondary = Color(0xFFFF6B35); // Warm orange
  static const Color accent = Color(0xFF00D4AA); // Teal green

  // Text
  static const Color textPrimary = Color(0xFFF5F5F5);
  static const Color textSecondary = Color(0xFFB0B0C0);
  static const Color textMuted = Color(0xFF6A6A7A);

  // Board
  static const Color boardLight = Color(0xFFF0D9B5);
  static const Color boardDark = Color(0xFFB58863);
  static const Color boardHighlight = Color(0x6646B888);
  static const Color boardLastMove = Color(0x44E2B714);
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
    colors: [Color(0xFF0D0D0D), Color(0xFF1A1A2E), Color(0xFF0F3460)],
  );

  static const LinearGradient cardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF1E1E30), Color(0xFF2A2A40)],
  );

  static const LinearGradient goldGradient = LinearGradient(
    colors: [Color(0xFFE2B714), Color(0xFFF5D565), Color(0xFFE2B714)],
  );
}
