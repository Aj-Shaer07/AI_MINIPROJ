import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'core/app_router.dart';
import 'screens/home_screen.dart';
import 'screens/difficulty_screen.dart';
import 'screens/game_screen.dart';
import 'screens/endgame_test_screen.dart';
import 'models/difficulty.dart';

class MindGambitApp extends StatelessWidget {
  const MindGambitApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MindGambit',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      initialRoute: AppRouter.home,
      onGenerateRoute: (settings) {
        switch (settings.name) {
          case AppRouter.home:
            return MaterialPageRoute(builder: (_) => const HomeScreen());
          case AppRouter.difficulty:
            return MaterialPageRoute(builder: (_) => const DifficultyScreen());
          case AppRouter.endgameTest:
            return MaterialPageRoute(builder: (_) => const EndgameTestScreen());
          case AppRouter.game:
            final args = settings.arguments as Map<String, dynamic>;
            return MaterialPageRoute(
              builder: (_) => GameScreen(
                difficulty: args['difficulty'] as Difficulty,
                playerIsWhite: args['playerIsWhite'] as bool,
                timerSeconds: args['timerSeconds'] as int? ?? 0,
                fen: args['fen'] as String?,
              ),
            );
          default:
            return MaterialPageRoute(builder: (_) => const HomeScreen());
        }
      },
    );
  }
}
