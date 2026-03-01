import 'package:flutter_test/flutter_test.dart';
import 'package:mindgambit/app.dart';

void main() {
  testWidgets('MindGambit app launches', (WidgetTester tester) async {
    await tester.pumpWidget(const MindGambitApp());
    expect(find.text('MindGambit'), findsOneWidget);
  });
}
