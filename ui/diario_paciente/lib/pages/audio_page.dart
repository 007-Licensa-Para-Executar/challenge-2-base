import 'dart:async';

import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/audio_source.dart';
import '../services/diary_repository.dart';

class AudioPage extends StatefulWidget {
  const AudioPage({
    super.key,
    required this.repository,
    required this.capture,
    this.transcribe,
  });

  final DiaryRepository repository;
  final AudioCapture capture;
  final Future<String> Function(AudioDraft draft)? transcribe;

  @override
  State<AudioPage> createState() => AudioPageState();
}

class AudioPageState extends State<AudioPage> {
  AudioDraft? _draft;
  String _message = '';
  Duration _elapsed = Duration.zero;
  StreamSubscription<Duration>? _ticks;
  bool _recording = false;
  bool _transcriptsOpen = false;
  bool _transcribing = false;
  String _preview = '';

  bool get busy => _recording || widget.repository.saving;

  @override
  void dispose() {
    _ticks?.cancel();
    super.dispose();
  }

  Future<bool> confirmLeave() async {
    if (!_recording && _draft == null) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Descartar este áudio?'),
        content: const Text('A gravação ou o arquivo ainda não foram enviados.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Ficar')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Sair')),
        ],
      ),
    );
    if (leave == true && _recording) {
      await widget.capture.stopRecording();
      _recording = false;
    }
    return leave ?? false;
  }

  Future<void> _pick() async {
    final draft = await widget.capture.pickFile();
    if (!mounted || draft == null) return;
    setState(() {
      _draft = draft;
      _message = '';
      _preview = '';
    });
  }

  Future<void> _listen() async {
    final draft = _draft;
    if (draft == null) return;
    setState(() => _message = 'Reproduzindo ${draft.name}.');
    try {
      await widget.capture.play(draft.bytes, draft.name);
    } catch (_) {
      if (!mounted) return;
      setState(() => _message = 'Não foi possível reproduzir este áudio.');
    }
  }

  Future<void> _transcribe() async {
    final draft = _draft;
    final transcribe = widget.transcribe;
    if (draft == null || transcribe == null || _transcribing) return;
    setState(() {
      _transcribing = true;
      _preview = '';
      _message = '';
    });
    try {
      final text = await transcribe(draft);
      if (!mounted) return;
      setState(() {
        _transcribing = false;
        _preview = text;
      });
    } catch (error) {
      if (!mounted) return;
      final detail = error is StateError ? error.message.trim() : '';
      setState(() {
        _transcribing = false;
        _message = detail.isEmpty
            ? 'O transcritor local em 127.0.0.1:8765 não respondeu. O áudio não foi enviado.'
            : '$detail O áudio não foi enviado.';
      });
    }
  }

  Future<void> _toggleRecord() async {
    if (_recording) {
      final draft = await widget.capture.stopRecording();
      _ticks?.cancel();
      if (!mounted) return;
      setState(() {
        _recording = false;
        _draft = draft ?? _draft;
      });
      return;
    }
    final start = await widget.capture.startRecording();
    if (!mounted) return;
    if (start.permissionDenied) {
      setState(() => _message = 'O navegador não autorizou o microfone.');
      return;
    }
    if (!start.started) return;
    _ticks = widget.capture.elapsed.listen((value) {
      if (mounted) setState(() => _elapsed = value);
    });
    setState(() {
      _recording = true;
      _elapsed = Duration.zero;
      _message = '';
      _draft = null;
      _preview = '';
    });
  }

  Future<void> _send() async {
    final draft = _draft;
    if (draft == null || widget.repository.saving) return;
    try {
      await widget.repository.saveAudio(draft);
      if (!mounted) return;
      setState(() {
        _draft = null;
        _message = 'Áudio aceito nesta demonstração. O estado inicial é aguardando.';
      });
    } on DiaryFailure catch (error) {
      if (!mounted) return;
      setState(() => _message = _audioMessage(error.code));
    }
  }

  @override
  Widget build(BuildContext context) {
    final draft = _draft;
    final transcribed = widget.repository.entries
        .where((entry) => entry.kind == DiaryKind.audio && entry.transcript.isNotEmpty)
        .toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 32, 24, 28),
      children: [
        Text('Áudio', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        const Text(
          'O arquivo original permanece. Depois do envio ele pode ficar aguardando, em processamento, concluído ou com erro. Nesta demonstração o Whisper não é executado. A transcrição que aparece no histórico é fictícia e não substitui o áudio.',
        ),
        const SizedBox(height: 20),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                FilledButton.icon(
                  onPressed: busy ? null : _pick,
                  icon: const Icon(Icons.upload_file),
                  label: const Text('Selecionar WAV, MP3 ou M4A'),
                ),
                if (widget.capture.canRecord) ...[
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: widget.repository.saving ? null : _toggleRecord,
                    icon: Icon(_recording ? Icons.stop : Icons.mic_none),
                    label: Text(_recording ? 'Parar ${_clock(_elapsed)}' : 'Gravar pelo microfone'),
                  ),
                ],
                if (_recording)
                  const Padding(
                    padding: EdgeInsets.only(top: 12),
                    child: Text('Gravando. O cronômetro acompanha o tempo real.'),
                  ),
                if (draft != null) ...[
                  const SizedBox(height: 20),
                  Text(draft.name, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(_details(draft)),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: _listen,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Ouvir antes de enviar'),
                  ),
                  if (widget.transcribe != null) ...[
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: _transcribing ? null : _transcribe,
                      icon: const Icon(Icons.notes_outlined),
                      label: Text(_transcribing ? 'Transcrevendo…' : 'Transcrever antes de enviar'),
                    ),
                  ],
                  if (_preview.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Text('Prévia deste áudio, ainda não enviada.', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Text(_preview),
                  ],
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: widget.repository.saving ? null : _send,
                    child: Text(widget.repository.saving ? 'Enviando…' : 'Enviar áudio'),
                  ),
                ],
              ],
            ),
          ),
        ),
        if (_message.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(_message),
        ],
        if (transcribed.isNotEmpty) ...[
          const SizedBox(height: 20),
          OutlinedButton.icon(
            onPressed: () => setState(() => _transcriptsOpen = !_transcriptsOpen),
            icon: Icon(_transcriptsOpen ? Icons.expand_less : Icons.notes_outlined),
            label: Text(_transcriptsOpen ? 'Ocultar transcrições' : 'Ver transcrições'),
          ),
          if (_transcriptsOpen)
            for (final entry in transcribed) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(entry.fileName, style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Text(entry.transcript),
                      const SizedBox(height: 8),
                      const Text('Texto fictício já presente no registro. Enviar um áudio nesta tela não cria transcrição.'),
                    ],
                  ),
                ),
              ),
            ],
        ],
      ],
    );
  }

  String _details(AudioDraft draft) {
    final dot = draft.name.lastIndexOf('.');
    final type = dot < 0 ? 'Arquivo' : draft.name.substring(dot + 1).toUpperCase();
    final size = (draft.sizeBytes / 1024).toStringAsFixed(0);
    final duration = draft.duration == null ? '' : ' · ${_clock(draft.duration!)}';
    return '$type · $size KB$duration';
  }

  String _clock(Duration value) {
    final minutes = value.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = value.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  String _audioMessage(String code) {
    return switch (code) {
      'empty_audio' => 'O arquivo está vazio.',
      'audio_too_large' => 'O arquivo passa de 25 MB.',
      _ => 'Use um arquivo WAV, MP3 ou M4A.',
    };
  }
}
