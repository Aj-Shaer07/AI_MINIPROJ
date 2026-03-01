import 'package:flutter/material.dart';

/// Difficulty levels for the chess AI engine.
enum Difficulty {
  beginner(
    depth: 2,
    label: 'Beginner',
    description: 'Basic tactics, limited lookahead',
    icon: Icons.child_care,
  ),
  easy(
    depth: 3,
    label: 'Easy',
    description: 'Sees simple combinations',
    icon: Icons.directions_walk,
  ),
  medium(
    depth: 4,
    label: 'Medium',
    description: 'Strong positional play',
    icon: Icons.directions_run,
  ),
  hard(
    depth: 5,
    label: 'Hard',
    description: 'Deep tactical + positional',
    icon: Icons.fitness_center,
  ),
  expert(
    depth: 6,
    label: 'Expert',
    description: 'Maximum engine strength',
    icon: Icons.military_tech,
  );

  final int depth;
  final String label;
  final String description;
  final IconData icon;

  const Difficulty({
    required this.depth,
    required this.label,
    required this.description,
    required this.icon,
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
