import 'package:diario_paciente/main.dart';
import 'package:diario_paciente/models/diary_entry.dart';
import 'package:diario_paciente/services/fake_diary_repository.dart';
import 'package:diario_paciente/theme/diary_theme.dart';
import 'package:diario_paciente/widgets/diary_components.dart';
import 'package:diario_paciente/widgets/quiet_notice.dart';
import 'package:diario_paciente/widgets/status_chip.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'diary_app_test.dart' show ScriptedCapture;

void main() {
  testWidgets('componentes do diário respeitam toque, estado e texto grande', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: diaryTheme(),
        home: Scaffold(
          body: Column(
            children: [
              const DiarySectionHeader(title: 'Recentes', subtitle: 'Só o que já está nesta tela.'),
              const DiaryPrimaryButton(onPressed: _noop, label: 'Salvar relato'),
              const DiarySecondaryButton(onPressed: null, label: 'Ouvir antes de enviar'),
              const DiaryStatusChip(status: DiaryStatus.failed),
              const DiaryEmptyState(text: 'Nenhum registro ainda.'),
            ],
          ),
        ),
      ),
    );

    final primary = tester.getSize(find.widgetWithText(FilledButton, 'Salvar relato'));
    expect(primary.height, greaterThanOrEqualTo(48));
    final secondary = tester.getSize(find.widgetWithText(OutlinedButton, 'Ouvir antes de enviar'));
    expect(secondary.height, greaterThanOrEqualTo(48));
    expect(tester.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Ouvir antes de enviar')).onPressed, isNull);
    expect(find.byIcon(Icons.error_outline), findsOneWidget);
    expect(find.text('Erro'), findsOneWidget);
    expect(find.text('Nenhum registro ainda.'), findsOneWidget);

    final focused = diaryOutlinedStyle().side!.resolve({WidgetState.focused})!;
    expect(focused.width, 2);
    expect(focused.color, deepSage);
    expect(diaryFilledStyle().backgroundColor!.resolve({}), deepSage);
    expect(diaryFilledStyle().backgroundColor!.resolve({WidgetState.disabled}), isNot(deepSage));
  });

  testWidgets('a home continua legível com a fonte dobrada', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    for (final size in [const Size(390, 844), const Size(1280, 800)]) {
      tester.view.physicalSize = size;
      await tester.pumpWidget(
        DiaryApp(repository: FakeDiaryRepository(seed: []), capture: const ScriptedCapture()),
      );
      await tester.pumpAndSettle();
      expect(find.text('Como você está hoje?'), findsOneWidget);
      expect(tester.takeException(), isNull);
    }
  });
}

void _noop() {}
