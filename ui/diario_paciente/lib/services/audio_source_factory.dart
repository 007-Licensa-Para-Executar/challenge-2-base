import 'audio_source.dart';
import 'audio_source_stub.dart'
    if (dart.library.html) 'audio_source_web.dart';

AudioCapture createAudioCapture() => buildAudioCapture();
