import '../models/diary_entry.dart';
import 'diary_repository.dart';

/// Contrato da API local ainda não publicada.
///
/// O servidor atual em 127.0.0.1:8765 responde HTML e formulários
/// (`GET /`, `POST /texto`, `POST /audio`, `POST /worker`). Não há JSON,
/// não há CORS e o paciente é fixo no processo. Estes caminhos só devem
/// ser usados depois da revisão, com origem explícita em 127.0.0.1.
class HttpDiaryRepository extends DiaryRepository {
  HttpDiaryRepository({this.origin = 'http://127.0.0.1:8765'});

  static const historicoPath = '/api/historico';
  static const textoPath = '/api/texto';
  static const audioPath = '/api/audio';
  static const workerPath = '/api/worker';

  final String origin;

  @override
  List<DiaryEntry> get entries => const [];

  @override
  bool get loading => false;

  @override
  DiaryFailure? get failure => const DiaryFailure('api_nao_ligada');

  @override
  bool get saving => false;

  @override
  Future<void> refresh() => _closed();

  @override
  Future<void> saveText(String text, {String mood = ''}) => _closed();

  @override
  Future<void> saveAudio(AudioDraft draft) => _closed();

  Future<void> _closed() {
    throw StateError(
      'A API JSON ainda não está ligada. O paciente não vem do navegador.',
    );
  }
}
