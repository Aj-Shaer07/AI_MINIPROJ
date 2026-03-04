import 'package:flutter/material.dart';

/// Chess clock timer presets.
enum TimerOption {
  none(label: 'No Timer', seconds: 0, icon: Icons.timer_off),
  oneMin(label: '1 min', seconds: 60, icon: Icons.looks_one),
  threeMin(label: '3 min', seconds: 180, icon: Icons.looks_3),
  fiveMin(label: '5 min', seconds: 300, icon: Icons.looks_5),
  tenMin(label: '10 min', seconds: 600, icon: Icons.filter_none),
  fifteenMin(label: '15 min', seconds: 900, icon: Icons.schedule),
  thirtyMin(label: '30 min', seconds: 1800, icon: Icons.hourglass_bottom);

  final String label;
  final int seconds;
  final IconData icon;

  const TimerOption({
    required this.label,
    required this.seconds,
    required this.icon,
  });

  bool get hasTimer => seconds > 0;

  String formatTime(int remainingSeconds) {
    final m = remainingSeconds ~/ 60;
    final s = remainingSeconds % 60;
    return '${m.toString().padLeft(1, '0')}:${s.toString().padLeft(2, '0')}';
  }
}
