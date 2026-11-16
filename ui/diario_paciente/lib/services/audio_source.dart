import 'dart:async';
import 'dart:typed_data';

import '../models/diary_entry.dart';

class CaptureStart {
  const CaptureStart({required this.started, this.permissionDenied = false});

  final bool started;
  final bool permissionDenied;
}

abstract class AudioCapture {
  bool get canRecord;
  bool get isRecording;
  Stream<Duration> get elapsed;

  Future<AudioDraft?> pickFile();
  Future<CaptureStart> startRecording();
  Future<AudioDraft?> stopRecording();
  Future<void> play(Uint8List bytes, String name);
}

String audioExtension(String name) {
  final dot = name.lastIndexOf('.');
  if (dot < 0 || dot == name.length - 1) return '';
  return name.substring(dot + 1).toLowerCase();
}

bool supportedAudioName(String name) {
  final extension = audioExtension(name);
  return extension == 'wav' || extension == 'mp3' || extension == 'm4a';
}
