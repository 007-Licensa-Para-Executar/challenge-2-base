import 'package:flutter/foundation.dart';

import '../models/diary_entry.dart';

class DiaryFailure implements Exception {
  const DiaryFailure(this.code);
  final String code;
}

/// Leitura e gravação do diário. A identidade não vem da interface.
abstract class DiaryRepository extends ChangeNotifier {
  List<DiaryEntry> get entries;
  bool get loading;
  DiaryFailure? get failure;
  bool get saving;

  Future<void> refresh();
  Future<void> saveText(String text, {String mood = ''});
  Future<void> saveAudio(AudioDraft draft);
}
