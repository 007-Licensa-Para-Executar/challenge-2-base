import '../models/diary_entry.dart';
import 'diary_repository.dart';

/// Registros fictícios, só na memória. Não abre o SQLite do projeto.
class FakeDiaryRepository extends DiaryRepository {
  FakeDiaryRepository({List<DiaryEntry>? seed, this.delay = Duration.zero})
      : _entries = List.of(seed ?? demoEntries());

  final Duration delay;
  final List<DiaryEntry> _entries;
  bool _loading = false;
  DiaryFailure? _failure;
  bool _saving = false;
  int _sequence = 10;

  @override
  List<DiaryEntry> get entries => List.unmodifiable(_entries);

  @override
  bool get loading => _loading;

  @override
  DiaryFailure? get failure => _failure;

  @override
  bool get saving => _saving;

  @override
  Future<void> refresh() async {
    _loading = true;
    _failure = null;
    notifyListeners();
    await Future<void>.delayed(delay);
    _loading = false;
    notifyListeners();
  }

  @override
  Future<void> saveText(String text, {String mood = ''}) async {
    final cleaned = text.trim();
    if (cleaned.isEmpty) throw const DiaryFailure('empty_text');
    if (cleaned.length > 20000) throw const DiaryFailure('text_too_long');
    await _save(
      DiaryEntry(
        id: 'local-${_sequence++}',
        createdAt: DateTime.now(),
        kind: DiaryKind.written,
        status: DiaryStatus.ready,
        text: cleaned,
        manualMood: mood,
      ),
    );
  }

  @override
  Future<void> saveAudio(AudioDraft draft) async {
    _validateAudio(draft);
    await _save(
      DiaryEntry(
        id: 'local-${_sequence++}',
        createdAt: DateTime.now(),
        kind: DiaryKind.audio,
        status: DiaryStatus.queued,
        fileName: draft.name,
        duration: draft.duration,
        audio: draft,
      ),
    );
  }

  Future<void> _save(DiaryEntry entry) async {
    _saving = true;
    notifyListeners();
    await Future<void>.delayed(delay);
    _entries.insert(0, entry);
    _saving = false;
    notifyListeners();
  }

  static void validateAudio(AudioDraft draft) => _validateAudio(draft);

  static void _validateAudio(AudioDraft draft) {
    if (draft.bytes.isEmpty) throw const DiaryFailure('empty_audio');
    if (draft.bytes.length > 25 * 1024 * 1024) {
      throw const DiaryFailure('audio_too_large');
    }
    final dot = draft.name.lastIndexOf('.');
    final extension = dot < 0 ? '' : draft.name.substring(dot + 1).toLowerCase();
    if (extension != 'wav' &&
        extension != 'mp3' &&
        extension != 'm4a' &&
        extension != 'webm') {
      throw const DiaryFailure('invalid_audio');
    }
  }

  static List<DiaryEntry> demoEntries() {
    return [
      DiaryEntry(
        id: 'sint-escrito',
        createdAt: DateTime.utc(2026, 11, 12, 18, 10),
        kind: DiaryKind.written,
        status: DiaryStatus.ready,
        manualMood: 'Calma',
        text:
            'Relato fictício. O fim da tarde foi silencioso e não houve pressa para decidir nada.',
      ),
      DiaryEntry(
        id: 'sint-fila',
        createdAt: DateTime.utc(2026, 11, 13, 9, 2),
        kind: DiaryKind.audio,
        status: DiaryStatus.queued,
        fileName: 'nota-ficticia.wav',
        duration: const Duration(seconds: 18),
      ),
      DiaryEntry(
        id: 'sint-andamento',
        createdAt: DateTime.utc(2026, 11, 13, 9, 16),
        kind: DiaryKind.audio,
        status: DiaryStatus.processing,
        fileName: 'manha-ficticia.m4a',
        duration: const Duration(seconds: 42),
      ),
      DiaryEntry(
        id: 'sint-pronto',
        createdAt: DateTime.utc(2026, 11, 11, 21, 40),
        kind: DiaryKind.audio,
        status: DiaryStatus.ready,
        fileName: 'tarde-ficticia.mp3',
        duration: const Duration(minutes: 1, seconds: 5),
        transcript:
            'Transcrição fictícia: o dia começou devagar e a frase sobre o remédio ficou completa.',
      ),
      DiaryEntry(
        id: 'sint-falha',
        createdAt: DateTime.utc(2026, 11, 10, 8, 5),
        kind: DiaryKind.audio,
        status: DiaryStatus.failed,
        fileName: 'corte-ficticio.wav',
        duration: const Duration(seconds: 4),
        errorCode: 'transcriber_failed',
      ),
    ];
  }
}
