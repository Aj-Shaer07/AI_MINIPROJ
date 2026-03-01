/// Result from the chess engine search.
class EngineResult {
  final String? bestMoveUci;
  final int evalCp;
  final int depth;
  final int nodes;
  final int timeMs;

  const EngineResult({
    required this.bestMoveUci,
    required this.evalCp,
    required this.depth,
    required this.nodes,
    required this.timeMs,
  });

  bool get hasMove => bestMoveUci != null && bestMoveUci!.isNotEmpty;

  String get evalDisplay {
    if (evalCp.abs() >= 90000) {
      final mateIn = (100000 - evalCp.abs() + 1) ~/ 2;
      return evalCp > 0 ? '+M$mateIn' : '-M$mateIn';
    }
    final pawnUnits = evalCp / 100;
    return pawnUnits >= 0
        ? '+${pawnUnits.toStringAsFixed(1)}'
        : pawnUnits.toStringAsFixed(1);
  }
}
