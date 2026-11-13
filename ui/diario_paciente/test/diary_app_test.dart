import 'dart:async';
import 'dart:typed_data';

import 'package:diario_paciente/main.dart';
import 'package:diario_paciente/models/diary_entry.dart';
import 'package:diario_paciente/services/audio_source.dart';
import 'package:diario_paciente/services/diary_repository.dart';
import 'package:diario_paciente/services/fake_diary_repository.dart';
import 'package:diario_paciente/services/http_diary_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('salva o relato uma vez e avisa se a tela for deixada', (tester) async {
    final repository = FakeDiaryRepository(seed: [], delay: const Duration(seconds: 1));
    await _pump(tester, repository, const Size(390, 844));
    await tester.tap(find.text('Escrever'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Relato fictício único.');
    await tester.pump();
    final button = tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Salvar relato'));
    expect(button.onPressed, isNotNull);
    await tester.tap(find.widgetWithText(FilledButton, 'Salvar relato'));
    await tester.pump();
    expect(repository.saving, isTrue);
    await tester.tap(find.text('Salvando…'));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(repository.entries.where((entry) => entry.text == 'Relato fictício único.'), hasLength(1));

    await tester.enterText(find.byType(TextField), 'Ainda não salvei.');
    await tester.tap(find.text('Início'));
    await tester.pumpAndSettle();
    expect(find.text('Sair sem salvar?'), findsOneWidget);
    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();
    expect(find.text('Ainda não salvei.'), findsOneWidget);
  });

  testWidgets('mostra os quatro estados de áudio e filtra o histórico', (tester) async {
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
  });

  testWidgets('lista vazia e falha de carga', (tester) async {
    await _pump(tester, FakeDiaryRepository(seed: []), const Size(1280, 800));
    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
    expect(find.textContaining('Nenhum registro ainda'), findsOneWidget);

    await _pump(tester, _BrokenRepository(), const Size(1440, 900));
    expect(find.textContaining('Não foi possível carregar'), findsOneWidget);
  });

  testWidgets('rejeita áudio inválido e envia um wav', (tester) async {
    final repository = FakeDiaryRepository(seed: []);
    final capture = ScriptedCapture();
    await tester.pumpWidget(DiaryApp(repository: repository, capture: capture));
    await tester.pumpAndSettle();
    await tester.binding.setSurfaceSize(const Size(768, 1024));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Áudio'));
    await tester.pumpAndSettle();
    expect(find.text('Gravar pelo microfone'), findsNothing);

    ScriptedCapture.next = AudioDraft(name: 'nota.txt', bytes: Uint8List.fromList([1, 2, 3]));
    await tester.tap(find.text('Selecionar WAV, MP3 ou M4A'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enviar áudio'));
    await tester.pumpAndSettle();
    expect(find.textContaining('WAV, MP3 ou M4A'), findsWidgets);
    expect(repository.entries, isEmpty);

    ScriptedCapture.next = AudioDraft(name: 'fala.wav', bytes: Uint8List.fromList(const [1, 2, 3, 4]));
    await tester.tap(find.text('Selecionar WAV, MP3 ou M4A'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enviar áudio'));
    await tester.pumpAndSettle();
    expect(repository.entries.single.status, DiaryStatus.queued);
    expect(repository.entries.single.kind, DiaryKind.audio);
  });

  test('o cliente HTTP ainda não está ligado e não recebe paciente do navegador', () {
    expect(HttpDiaryRepository.textoPath, '/api/texto');
    expect(HttpDiaryRepository.historicoPath, '/api/historico');
    expect(
      () => HttpDiaryRepository().refresh(),
      throwsA(isA<StateError>()),
    );
  });
}

Future<void> _pump(WidgetTester tester, DiaryRepository repository, Size size) async {
  await tester.binding.setSurfaceSize(size);
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(
    DiaryApp(repository: repository, capture: const ScriptedCapture()),
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
  Future<CaptureStart> startRecording() async => const CaptureStart(started: false);

  @override
  Future<AudioDraft?> stopRecording() async => null;

  @override
  Future<void> play(Uint8List bytes, String name) async {}
}
