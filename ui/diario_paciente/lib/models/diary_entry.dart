import 'dart:typed_data';

enum DiaryKind { written, audio }

enum DiaryStatus { queued, processing, ready, failed }

class AudioDraft {
  const AudioDraft({
    required this.name,
    required this.bytes,
    this.duration,
  });

  final String name;
  final Uint8List bytes;
  final Duration? duration;

  int get sizeBytes => bytes.length;
}

class DiaryEntry {
  const DiaryEntry({
    required this.id,
    required this.createdAt,
    required this.kind,
    required this.status,
    this.text = '',
    this.transcript = '',
    this.errorCode = '',
    this.manualMood = '',
    this.fileName = '',
    this.duration,
    this.audio,
  });

  final String id;
  final DateTime createdAt;
  final DiaryKind kind;
  final DiaryStatus status;
  final String text;
  final String transcript;
  final String errorCode;
  final String manualMood;
  final String fileName;
  final Duration? duration;
  final AudioDraft? audio;

  String get statusLabel => switch (status) {
        DiaryStatus.queued => 'Aguardando',
        DiaryStatus.processing => 'Processando',
        DiaryStatus.ready => 'Concluído',
        DiaryStatus.failed => 'Erro',
      };

  String get kindLabel => kind == DiaryKind.written ? 'Escrito' : 'Áudio';

  String get preview {
    if (kind == DiaryKind.written && text.isNotEmpty) return text;
    if (transcript.isNotEmpty) return transcript;
    if (fileName.isNotEmpty) return fileName;
    return 'Registro sem texto';
  }
}
