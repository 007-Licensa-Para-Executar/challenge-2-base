import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

import '../models/diary_entry.dart';
import 'audio_source.dart';

AudioCapture buildAudioCapture() => WebAudioCapture();

class WebAudioCapture implements AudioCapture {
  final _elapsed = StreamController<Duration>.broadcast();
  Timer? _timer;
  DateTime? _started;
  web.MediaRecorder? _recorder;
  web.MediaStream? _stream;
  final List<web.Blob> _chunks = [];
  bool _recording = false;

  @override
  bool get canRecord => true;

  @override
  bool get isRecording => _recording;

  @override
  Stream<Duration> get elapsed => _elapsed.stream;

  @override
  Future<AudioDraft?> pickFile() async {
    final input = web.HTMLInputElement()
      ..type = 'file'
      ..accept = '.wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4';
    final selected = Completer<web.File?>();
    input.onchange = ((web.Event _) {
      selected.complete(input.files?.item(0));
    }).toJS;
    input.click();
    final file = await selected.future;
    if (file == null) return null;
    final bytes = await _bytesOf(file);
    return AudioDraft(name: file.name, bytes: bytes, duration: await _duration(bytes, file.name));
  }

  @override
  Future<CaptureStart> startRecording() async {
    try {
      _stream = await web.window.navigator.mediaDevices
          .getUserMedia(web.MediaStreamConstraints(audio: true.toJS))
          .toDart;
    } catch (_) {
      return const CaptureStart(started: false, permissionDenied: true);
    }
    _chunks.clear();
    final recorder = web.MediaRecorder(_stream!);
    recorder.ondataavailable = ((web.BlobEvent event) {
      if (event.data.size > 0) _chunks.add(event.data);
    }).toJS;
    recorder.start();
    _recorder = recorder;
    _recording = true;
    _started = DateTime.now();
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      final start = _started;
      if (start != null) _elapsed.add(DateTime.now().difference(start));
    });
    return const CaptureStart(started: true);
  }

  @override
  Future<AudioDraft?> stopRecording() async {
    final recorder = _recorder;
    _timer?.cancel();
    _recording = false;
    if (recorder == null) return null;
    final stopped = Completer<void>();
    recorder.onstop = ((web.Event _) => stopped.complete()).toJS;
    recorder.stop();
    await stopped.future;
    _stream?.getTracks().toDart.forEach((track) => track.stop());
    final blob = web.Blob(
      _chunks.map((chunk) => chunk as JSAny).toList().toJS,
      web.BlobPropertyBag(type: 'audio/webm'),
    );
    final bytes = await _bytesOfBlob(blob);
    final elapsed = _started == null ? Duration.zero : DateTime.now().difference(_started!);
    _recorder = null;
    _stream = null;
    return AudioDraft(name: 'gravacao.webm', bytes: bytes, duration: elapsed);
  }

  @override
  Future<void> play(Uint8List bytes, String name) async {
    final blob = web.Blob(
      [bytes.toJS].toJS,
      web.BlobPropertyBag(type: _mime(name)),
    );
    final url = web.URL.createObjectURL(blob);
    final audio = web.HTMLAudioElement()..src = url;
    await audio.play().toDart;
  }

  Future<Uint8List> _bytesOf(web.File file) {
    final reader = web.FileReader();
    final done = Completer<Uint8List>();
    reader.onloadend = ((web.ProgressEvent _) {
      final buffer = reader.result as JSArrayBuffer;
      done.complete(buffer.toDart.asUint8List());
    }).toJS;
    reader.readAsArrayBuffer(file);
    return done.future;
  }

  Future<Uint8List> _bytesOfBlob(web.Blob blob) {
    final reader = web.FileReader();
    final done = Completer<Uint8List>();
    reader.onloadend = ((web.ProgressEvent _) {
      final buffer = reader.result as JSArrayBuffer;
      done.complete(buffer.toDart.asUint8List());
    }).toJS;
    reader.readAsArrayBuffer(blob);
    return done.future;
  }

  Future<Duration?> _duration(Uint8List bytes, String name) async {
    try {
      final blob = web.Blob([bytes.toJS].toJS, web.BlobPropertyBag(type: _mime(name)));
      final url = web.URL.createObjectURL(blob);
      final audio = web.HTMLAudioElement()..src = url;
      final done = Completer<Duration?>();
      audio.onloadedmetadata = ((web.Event _) {
        final seconds = audio.duration;
        done.complete(seconds.isFinite ? Duration(milliseconds: (seconds * 1000).round()) : null);
      }).toJS;
      audio.onerror = ((web.Event _) => done.complete(null)).toJS;
      return await done.future.timeout(const Duration(seconds: 2), onTimeout: () => null);
    } catch (_) {
      return null;
    }
  }

  String _mime(String name) {
    return switch (audioExtension(name)) {
      'mp3' => 'audio/mpeg',
      'm4a' => 'audio/mp4',
      'wav' => 'audio/wav',
      _ => 'audio/webm',
    };
  }
}
