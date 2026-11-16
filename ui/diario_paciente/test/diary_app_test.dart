import 'dart:async';

import 'package:diario_paciente/main.dart';
import 'package:diario_paciente/models/diary_entry.dart';
import 'package:diario_paciente/pages/detail_page.dart';
import 'package:diario_paciente/theme/diary_theme.dart';
import 'package:diario_paciente/services/audio_source.dart';
import 'package:diario_paciente/services/diary_repository.dart';
import 'package:diario_paciente/services/fake_diary_repository.dart';
import 'package:diario_paciente/services/http_diary_repository.dart';
import 'package:diario_paciente/widgets/mood_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('salva o relato uma vez e avisa se a tela for deixada', (
    tester,
  ) async {
    final repository = FakeDiaryRepository(
      seed: [],
      delay: const Duration(seconds: 1),
    );
    await _pump(tester, repository, const Size(390, 844));
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('Meu Diário'), findsNothing);
    expect(find.text('Como você está hoje?'), findsOneWidget);
    await tester.tap(find.text('Escrever'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'Relato fictício único.');

    await tester.pump();

    final button = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Salvar relato'),
    );
    expect(button.onPressed, isNotNull);

    await tester.tap(find.widgetWithText(FilledButton, 'Salvar relato'));

    await tester.pump();

    expect(repository.saving, isTrue);
    await tester.tap(find.text('Salvando…'));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(
      repository.entries.where(
        (entry) => entry.text == 'Relato fictício único.',
      ),
      hasLength(1),
    );

    await tester.enterText(find.byType(TextField), 'Ainda não salvei.');
    await tester.tap(find.text('Início'));
    await tester.pumpAndSettle();
    expect(find.text('Sair sem salvar?'), findsOneWidget);
    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();
    expect(find.text('Ainda não salvei.'), findsOneWidget);
  });

  testWidgets('mostra os quatro estados de áudio e filtra o histórico', (
    tester,
  ) async {
    final repository = FakeDiaryRepository();
    await _pump(tester, repository, const Size(390, 844));
    await tester.tap(find.text('Histórico'));
    await tester.pumpAndSettle();
    expect(find.text('Aguardando'), findsWidgets);
    expect(find.text('Processando'), findsWidgets);
    expect(find.text('Concluído'), findsWidgets);
    expect(find.text('Erro'), findsWidgets);

    await tester.tap(find.widgetWithText(FilterChip, 'Escritos'));
    await tester.pumpAndSettle();
    expect(find.textContaining('nota-ficticia'), findsNothing);
    expect(find.textContaining('fim da tarde'), findsOneWidget);
    expect(find.textContaining('novembro'), findsWidgets);
    expect(find.textContaining('November'), findsNothing);

    await tester.tap(find.widgetWithText(FilterChip, 'Aguardando'));
    await tester.pumpAndSettle();
    expect(find.text('Nenhum registro com esse filtro.'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilterChip, 'Todos'));
    await tester.pumpAndSettle();
    expect(find.textContaining('nota-ficticia'), findsWidgets);
  });

  testWidgets('o histórico abre o detalhe e separa áudio de transcrição', (
    tester,
  ) async {
    await _pump(tester, FakeDiaryRepository(), const Size(1280, 1600));
    await tester.tap(
      find.descendant(
        of: find.byType(NavigationRail),
        matching: find.text('Histórico'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Seus registros'), findsOneWidget);
    final newest = tester.getTopLeft(
      find.textContaining('13 de novembro').first,
    );
    final older = tester.getTopLeft(
      find.textContaining('12 de novembro').first,
    );
    expect(newest.dy, lessThan(older.dy));

    var focused = false;
    for (var step = 0; step < 40 && !focused; step++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      focused = _focusNearText(tester, 'fim da tarde');
    }
    expect(focused, isTrue);
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pumpAndSettle();
    expect(find.text('Texto original'), findsOneWidget);
    expect(find.textContaining('não houve pressa'), findsWidgets);
    await tester.tap(find.text('Voltar ao histórico'));
    await tester.pumpAndSettle();
    expect(find.text('Seus registros'), findsOneWidget);

    await tester.tap(find.text('corte-ficticio.wav'));
    await tester.pumpAndSettle();
    expect(find.textContaining('não foi concluída'), findsOneWidget);
    expect(find.textContaining('transcriber_failed'), findsNothing);
    expect(find.text('Transcrição bruta'), findsNothing);
    await tester.tap(find.text('Voltar ao histórico'));
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('o dia começou devagar'));
    await tester.pumpAndSettle();
    expect(find.text('Transcrição bruta'), findsOneWidget);
    expect(find.textContaining('pode conter erros'), findsOneWidget);
    await tester.tap(find.text('Voltar ao histórico'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('nota-ficticia.wav'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Ainda não há transcrição'), findsOneWidget);
    expect(find.text('Ouvir áudio original'), findsNothing);
  });

  test('a mesma data desempata pelo id', () {
    DiaryEntry entry(String id, DateTime at) => DiaryEntry(
      id: id,
      createdAt: at,
      kind: DiaryKind.written,
      status: DiaryStatus.ready,
    );
    final sorted = [
      entry('b', DateTime.utc(2026, 1, 1)),
      entry('c', DateTime.utc(2026, 1, 2)),
      entry('a', DateTime.utc(2026, 1, 1)),
    ]..sort(compareEntriesNewestFirst);
    expect(sorted.map((item) => item.id), ['c', 'a', 'b']);
  });

  testWidgets('a home mostra os três mais recentes na ordem do histórico', (
    tester,
  ) async {
    await _pump(tester, FakeDiaryRepository(), const Size(1280, 1800));
    expect(find.text('manha-ficticia.m4a'), findsOneWidget);
    expect(find.text('nota-ficticia.wav'), findsOneWidget);
    expect(find.textContaining('fim da tarde'), findsOneWidget);
    expect(find.text('corte-ficticio.wav'), findsNothing);
    expect(find.textContaining('o dia começou devagar'), findsNothing);
    final newest = tester.getTopLeft(find.text('manha-ficticia.m4a'));
    final middle = tester.getTopLeft(find.text('nota-ficticia.wav'));
    final oldest = tester.getTopLeft(find.textContaining('fim da tarde'));
    expect(newest.dy, lessThan(middle.dy));
    expect(middle.dy, lessThan(oldest.dy));

    await tester.tap(find.text('Ver histórico'));
    await tester.pumpAndSettle();
    final historyNewest = tester.getTopLeft(find.text('manha-ficticia.m4a'));
    final historyMiddle = tester.getTopLeft(find.text('nota-ficticia.wav'));
    expect(historyNewest.dy, lessThan(historyMiddle.dy));
  });

  testWidgets('as telas cabem em 320 px com a fonte ampliada', (tester) async {
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    for (final scale in [1.0, 1.5, 2.0]) {
      tester.platformDispatcher.textScaleFactorTestValue = scale;
      tester.view.physicalSize = const Size(320, 720);
      await tester.pumpWidget(
        KeyedSubtree(
          key: UniqueKey(),
          child: DiaryApp(
            repository: FakeDiaryRepository(),
            capture: const ScriptedCapture(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(NavigationBar), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.scrollUntilVisible(find.text('Ver histórico'), 200);
      expect(tester.takeException(), isNull);
      for (final label in ['Escrever', 'Áudio', 'Histórico', 'Início']) {
        await tester.tap(find.text(label));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        if (label == 'Histórico' || label == 'Áudio') {
          await tester.drag(find.byType(ListView).last, const Offset(0, -800));
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);
        }
      }
    }
  });

  testWidgets('o detalhe longo cabe com a fonte dobrada', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 844);
    tester.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await tester.pumpWidget(
      MaterialApp(
        theme: diaryTheme(),
        locale: const Locale('pt', 'BR'),
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        home: DetailPage(
          capture: const ScriptedCapture(),
          entry: DiaryEntry(
            id: 'longo',
            createdAt: DateTime.utc(2026, 11, 1, 12),
            kind: DiaryKind.written,
            status: DiaryStatus.ready,
            text: 'frase longa ' * 80,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('frase longa'), findsOneWidget);
    expect(find.text('Voltar ao histórico'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('lista vazia e falha de carga', (tester) async {
    await _pump(tester, FakeDiaryRepository(seed: []), const Size(1280, 800));
    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
    expect(find.text('Meu Diário'), findsOneWidget);
    expect(find.text('Como você está hoje?'), findsOneWidget);
    expect(find.textContaining('Nenhum registro ainda'), findsOneWidget);

    await _pump(tester, _BrokenRepository(), const Size(1440, 900));
    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.text('Meu Diário'), findsOneWidget);
    expect(find.textContaining('Não foi possível carregar'), findsOneWidget);
  });

  testWidgets('rejeita áudio inválido e envia um wav', (tester) async {
    final repository = FakeDiaryRepository(seed: []);
    final capture = ScriptedCapture();
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(768, 1024);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);
    await tester.pumpWidget(DiaryApp(repository: repository, capture: capture));
    await tester.pumpAndSettle();
    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.text('Meu Diário'), findsOneWidget);
    await tester.tap(find.text('Áudio'));
    await tester.pumpAndSettle();
    expect(find.text('Gravar pelo microfone'), findsNothing);
    expect(find.text('Ver transcrições'), findsNothing);

    ScriptedCapture.next = AudioDraft(
      name: 'nota.txt',
      bytes: Uint8List.fromList([1, 2, 3]),
    );
    await tester.tap(find.text('Selecionar áudio'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enviar áudio'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Esse arquivo não serve'), findsOneWidget);
    expect(repository.entries, isEmpty);

    ScriptedCapture.next = AudioDraft(
      name: 'fala.wav',
      bytes: Uint8List.fromList(const [1, 2, 3, 4]),
    );
    await tester.tap(find.text('Selecionar áudio'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enviar áudio'));
    await tester.pumpAndSettle();
    expect(repository.entries.single.status, DiaryStatus.queued);
    expect(repository.entries.single.kind, DiaryKind.audio);
  });

  testWidgets('a prévia transcreve sem enviar o áudio', (tester) async {
    final repository = FakeDiaryRepository(seed: []);
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(768, 1024);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);
    await tester.pumpWidget(
      DiaryApp(
        repository: repository,
        capture: const ScriptedCapture(),
        transcribe: (draft) async => 'fala ouvida na prévia',
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Áudio'));
    await tester.pumpAndSettle();
    ScriptedCapture.next = AudioDraft(
      name: 'fala.wav',
      bytes: Uint8List.fromList(const [1, 2, 3, 4]),
    );
    await tester.tap(find.text('Selecionar áudio'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Transcrever antes de enviar'));
    await tester.pumpAndSettle();
    expect(find.text('fala ouvida na prévia'), findsOneWidget);
    expect(find.textContaining('ainda não enviada'), findsOneWidget);
    expect(repository.entries, isEmpty);
  });

  testWidgets('o botão revela só a transcrição que o registro já tem', (
    tester,
  ) async {
    await _pump(tester, FakeDiaryRepository(), const Size(1280, 900));
    await tester.tap(
      find.descendant(
        of: find.byType(NavigationRail),
        matching: find.text('Áudio'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('o dia começou devagar'), findsNothing);
    await tester.scrollUntilVisible(find.text('Ver transcrições'), 400);
    await tester.tap(find.text('Ver transcrições'));
    await tester.pumpAndSettle();
    expect(find.textContaining('o dia começou devagar'), findsOneWidget);
    expect(find.text('nota-ficticia.wav'), findsNothing);
    await tester.tap(find.text('Ocultar transcrições'));
    await tester.pumpAndSettle();
    expect(find.textContaining('o dia começou devagar'), findsNothing);
  });

  testWidgets('o check-in é local e os cards abrem as telas', (tester) async {
    final repository = FakeDiaryRepository();
    final before = repository.entries.map((entry) => entry.id).toList();
    await _pump(tester, repository, const Size(390, 844));
    final semantics = tester.ensureSemantics();

    expect(
      tester.getSemantics(find.widgetWithText(MoodOptionButton, 'Bem')),
      isSemantics(
        isButton: true,
        isFocusable: true,
        hasTapAction: true,
        label: 'Bem',
      ),
    );
    await tester.tap(find.text('Bem'));
    await tester.pump();
    expect(
      tester
          .widget<MoodOptionButton>(
            find.widgetWithText(MoodOptionButton, 'Bem'),
          )
          .selected,
      isTrue,
    );
    expect(
      tester.getSemantics(find.widgetWithText(MoodOptionButton, 'Bem')),
      isSemantics(
        isButton: true,
        isFocusable: true,
        hasTapAction: true,
        isSelected: true,
        label: 'Bem',
      ),
    );
    await tester.tap(find.text('Triste'));
    await tester.pump();
    expect(
      tester
          .widget<MoodOptionButton>(
            find.widgetWithText(MoodOptionButton, 'Bem'),
          )
          .selected,
      isFalse,
    );
    expect(
      tester
          .widget<MoodOptionButton>(
            find.widgetWithText(MoodOptionButton, 'Triste'),
          )
          .selected,
      isTrue,
    );
    await tester.tap(find.text('Triste'));
    await tester.pump();
    expect(
      tester
          .widget<MoodOptionButton>(
            find.widgetWithText(MoodOptionButton, 'Triste'),
          )
          .selected,
      isFalse,
    );
    expect(repository.entries.map((entry) => entry.id), before);
    expect(
      repository.entries.every((entry) => entry.manualMood.isEmpty),
      isTrue,
    );
    expect(find.textContaining('Humor informado'), findsNothing);

    await tester.scrollUntilVisible(find.text('Escrever relato'), 400);
    await tester.tap(find.text('Escrever relato'));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(FilledButton, 'Salvar relato'), findsOneWidget);
    await tester.tap(find.text('Início'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Gravar ou enviar áudio'), 400);
    await tester.tap(find.text('Gravar ou enviar áudio'));
    await tester.pumpAndSettle();
    expect(find.text('Selecionar áudio'), findsOneWidget);
    expect(find.text('Gravar pelo microfone'), findsNothing);
    semantics.dispose();
  });

  testWidgets('o teclado seleciona o humor e a home mostra só três recentes', (
    tester,
  ) async {
    await _pump(tester, FakeDiaryRepository(), const Size(1280, 900));
    expect(find.textContaining('o dia começou devagar'), findsNothing);
    expect(find.text('Exemplos desta demonstração.'), findsOneWidget);

    var focused = false;
    for (var step = 0; step < 24 && !focused; step++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      focused = _focusOnLabel(tester, 'Ansioso');
    }
    expect(focused, isTrue);
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pump();
    expect(
      tester
          .widget<MoodOptionButton>(
            find.widgetWithText(MoodOptionButton, 'Ansioso'),
          )
          .selected,
      isTrue,
    );
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pump();
    expect(
      tester
          .widget<MoodOptionButton>(
            find.widgetWithText(MoodOptionButton, 'Ansioso'),
          )
          .selected,
      isFalse,
    );

    await tester.tap(find.text('Ver histórico'));
    await tester.pumpAndSettle();
    expect(find.text('Seus registros'), findsOneWidget);
  });

  testWidgets('o teclado chega ao editor e o contador acompanha o texto', (
    tester,
  ) async {
    await _pump(tester, FakeDiaryRepository(seed: []), const Size(1280, 900));
    await tester.tap(
      find.descendant(
        of: find.byType(NavigationRail),
        matching: find.text('Escrever'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Escreva sobre seu dia'), findsOneWidget);
    expect(find.byType(MoodSelector), findsNothing);
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Salvar relato'),
          )
          .onPressed,
      isNull,
    );

    var focused = false;
    for (var step = 0; step < 24 && !focused; step++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      focused = _editorFocused(tester);
    }
    expect(focused, isTrue);
    await tester.enterText(find.byType(TextField), 'a' * 2000);
    await tester.pump();
    expect(find.text('2000 / 20000'), findsOneWidget);
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Salvar relato'),
          )
          .onPressed,
      isNotNull,
    );
  });

  testWidgets('escrita e áudio cabem com a fonte dobrada', (tester) async {
    tester.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    for (final width in [390.0, 768.0, 1280.0, 1440.0]) {
      await _pump(tester, FakeDiaryRepository(seed: []), Size(width, 900));
      await tester.tap(find.text('Escrever'));
      await tester.pumpAndSettle();
      expect(find.text('Escreva sobre seu dia'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('Áudio'));
      await tester.pumpAndSettle();
      expect(find.text('Conte com sua voz'), findsOneWidget);
      expect(find.text('Gravar pelo microfone'), findsNothing);
      expect(tester.takeException(), isNull);
    }
  });

  testWidgets('cabe em 390, 768, 1280 e 1440', (tester) async {
    for (final width in [390.0, 768.0, 1280.0, 1440.0]) {
      await _pump(tester, FakeDiaryRepository(), Size(width, 900));
      expect(find.text('Como você está hoje?'), findsOneWidget);
      expect(find.text('Bem'), findsOneWidget);
      expect(tester.takeException(), isNull);
      if (width < 768) {
        expect(find.byType(NavigationBar), findsOneWidget);
        expect(find.text('Meu Diário'), findsNothing);
      } else {
        expect(find.byType(NavigationRail), findsOneWidget);
        expect(find.text('Meu Diário'), findsOneWidget);
      }
      await tester.tap(find.text('Histórico'));
      await tester.pumpAndSettle();
      expect(find.textContaining('novembro'), findsWidgets);
      expect(tester.takeException(), isNull);
    }
  });

  test(
    'o cliente HTTP ainda não está ligado e não recebe paciente do navegador',
    () {
      expect(HttpDiaryRepository.textoPath, '/api/texto');
      expect(HttpDiaryRepository.historicoPath, '/api/historico');
      expect(() => HttpDiaryRepository().refresh(), throwsA(isA<StateError>()));
    },
  );
}

bool _focusNearText(WidgetTester tester, String fragment) {
  final node = tester.binding.focusManager.primaryFocus;
  final context = node?.context;
  if (context == null || node?.hasFocus != true) return false;
  var found = false;
  void walk(Element element) {
    final widget = element.widget;
    if (widget is Text && (widget.data?.contains(fragment) ?? false)) {
      found = true;
    }
    element.visitChildren(walk);
  }

  context.visitAncestorElements((ancestor) {
    if (ancestor.widget is InkWell) {
      ancestor.visitChildren(walk);
      return false;
    }
    return true;
  });
  return found;
}

bool _editorFocused(WidgetTester tester) {
  final node = tester.binding.focusManager.primaryFocus;
  final context = node?.context;
  if (context == null || node?.hasFocus != true) return false;
  if (context.widget is EditableText) return true;
  var found = false;
  context.visitAncestorElements((ancestor) {
    if (ancestor.widget is EditableText || ancestor.widget is TextField) {
      found = true;
    }
    return !found;
  });
  return found;
}

bool _focusOnLabel(WidgetTester tester, String label) {
  final node = tester.binding.focusManager.primaryFocus;
  final context = node?.context;
  if (context == null || node?.hasFocus != true) return false;
  var found = false;
  context.visitAncestorElements((ancestor) {
    if (ancestor.widget is! OutlinedButton) return true;
    void walk(Element element) {
      final widget = element.widget;
      if (widget is Text && widget.data == label) found = true;
      element.visitChildren(walk);
    }

    ancestor.visitChildren(walk);
    return false;
  });
  return found;
}

Future<void> _pump(
  WidgetTester tester,
  DiaryRepository repository,
  Size size,
) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = size;
  addTearDown(tester.view.resetDevicePixelRatio);
  addTearDown(tester.view.resetPhysicalSize);
  await tester.pumpWidget(
    KeyedSubtree(
      key: UniqueKey(),
      child: DiaryApp(repository: repository, capture: const ScriptedCapture()),
    ),
  );
  await tester.pumpAndSettle();
}

class _BrokenRepository extends DiaryRepository {
  @override
  List<DiaryEntry> get entries => const [];

  @override
  bool get loading => false;

  @override
  DiaryFailure? get failure => const DiaryFailure('load_failed');

  @override
  bool get saving => false;

  @override
  Future<void> refresh() async {}

  @override
  Future<void> saveText(String text, {String mood = ''}) async {}

  @override
  Future<void> saveAudio(AudioDraft draft) async {}
}

class ScriptedCapture implements AudioCapture {
  const ScriptedCapture();

  static AudioDraft? next;

  @override
  bool get canRecord => false;

  @override
  bool get isRecording => false;

  @override
  Stream<Duration> get elapsed => const Stream.empty();

  @override
  Future<AudioDraft?> pickFile() async => next;

  @override
  Future<CaptureStart> startRecording() async =>
      const CaptureStart(started: false);

  @override
  Future<AudioDraft?> stopRecording() async => null;

  @override
  Future<void> play(Uint8List bytes, String name) async {}
}
