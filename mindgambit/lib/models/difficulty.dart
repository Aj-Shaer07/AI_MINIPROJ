import 'package:flutter/material.dart';

/// Difficulty levels for the chess AI engine.
enum Difficulty {
  beginner(
    depth: 3,
    label: 'Beginner Bot',
    description: 'Makes random-ish moves. Perfect for beginners.',
    icon: Icons.child_care,
    emoji: '🤖',
    elo: 800,
  ),
  easy(
    depth: 5,
    label: 'Casual Bot',
    description: 'Plays basic tactics. A good casual opponent.',
    icon: Icons.sentiment_satisfied,
    emoji: '😊',
    elo: 1200,
  ),
  medium(
    depth: 4,
    label: 'Intermediate Bot',
    description: 'Understands strategy and plans ahead.',
    icon: Icons.sentiment_very_satisfied,
    emoji: '🧐',
    elo: 1500,
  ),
  hard(
    depth: 7,
    label: 'Advanced Bot',
    description: 'Aggressive and hard to beat. Plays deep combinations.',
    icon: Icons.local_fire_department,
    emoji: '🔥',
    elo: 2000,
  ),
  expert(
    depth: 6,
    label: 'Expert Bot',
    description: 'Near-perfect play. Only for the brave.',
    icon: Icons.military_tech,
    emoji: '🤖',
    elo: 2500,
  );

  final int depth;
  final String label;
  final String description;
  final IconData icon;
  final String emoji;
  final int elo;

  const Difficulty({
    required this.depth,
    required this.label,
    required this.description,
    required this.icon,
    required this.emoji,
    required this.elo,
  });

  /// Algorithm techniques active at this level.
  List<String> get techniques {
    switch (this) {
      case Difficulty.beginner:
        return ['Alpha-Beta', 'Quiescence', 'PeSTO Eval'];
      case Difficulty.easy:
        return ['Alpha-Beta', 'Quiescence', 'PeSTO Eval', 'Move Ordering'];
      case Difficulty.medium:
        return [
          'Alpha-Beta',
          'Quiescence',
          'PeSTO Eval',
          'Move Ordering',
          'Transposition Table',
        ];
      case Difficulty.hard:
        return [
          'Alpha-Beta',
          'LMR',
          'PVS',
          'Quiescence',
          'PeSTO Eval',
          'TT',
          'Killer Heuristic',
        ];
      case Difficulty.expert:
        return [
          'Alpha-Beta',
          'LMR',
          'PVS',
          'Aspiration Windows',
          'Quiescence',
          'PeSTO Eval',
          'TT',
          'Killer + History',
        ];
    }
  }
}
