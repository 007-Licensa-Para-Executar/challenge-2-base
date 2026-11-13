import 'dart:async';
import 'dart:typed_data';

import '../models/diary_entry.dart';
import 'audio_source.dart';

/// Fora do navegador não há microfone. O botão de gravar fica oculto.
AudioCapture buildAudioCapture() => UnavailableAudioCapture();

class UnavailableAudioCapture implements AudioCapture {
  final _elapsed = const Stream<Duration>.empty();

  @override
  bool get canRecord => false;

  @override
  bool get isRecording => false;

  @override
  Stream<Duration> get elapsed => _elapsed;

  @override
  Future<AudioDraft?> pickFile() async => null;

  @override
  Future<CaptureStart> startRecording() async => const CaptureStart(started: false);

  @override
  Future<AudioDraft?> stopRecording() async => null;

  @override
  Future<void> play(Uint8List bytes, String name) async {}
}
