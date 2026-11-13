import 'dart:async';

import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/audio_source.dart';
import '../services/diary_repository.dart';

class AudioPage extends StatefulWidget {
  const AudioPage({super.key, required this.repository, required this.capture});

  final DiaryRepository repository;
  final AudioCapture capture;

  @override
  State<AudioPage> createState() => AudioPageState();
}

class AudioPageState extends State<AudioPage> {
  AudioDraft? _draft;
  String _message = '';
  Duration _elapsed = Duration.zero;
  StreamSubscription<Duration>? _ticks;
  bool _recording = false;

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
    });
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
        _message = 'Áudio enviado. O estado inicial é aguardando.';
      });
    } on DiaryFailure catch (error) {
      if (!mounted) return;
      setState(() => _message = _audioMessage(error.code));
    }
  }

  @override
  Widget build(BuildContext context) {
    final draft = _draft;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
      children: [
        Text('Áudio', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        const Text(
          'O arquivo original permanece. A transcrição automática pode conter erros e não substitui o áudio.',
        ),
        const SizedBox(height: 20),
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
          Text(_details(draft)),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => widget.capture.play(draft.bytes, draft.name),
            icon: const Icon(Icons.play_arrow),
            label: const Text('Ouvir antes de enviar'),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: widget.repository.saving ? null : _send,
            child: Text(widget.repository.saving ? 'Enviando…' : 'Enviar áudio'),
          ),
        ],
        if (_message.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(_message),
        ],
      ],
    );
  }

  String _details(AudioDraft draft) {
    final size = (draft.sizeBytes / 1024).toStringAsFixed(0);
    final duration = draft.duration == null ? '' : ' · ${_clock(draft.duration!)}';
    return '$size KB$duration';
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
