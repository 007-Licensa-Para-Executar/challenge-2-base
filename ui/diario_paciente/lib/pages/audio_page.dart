import 'dart:async';

import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/audio_source.dart';
import '../services/diary_repository.dart';
import '../theme/diary_theme.dart';
import '../widgets/diary_components.dart';
import '../widgets/status_chip.dart';

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
  bool _messageIsError = false;
  bool _accepted = false;
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
        content: const Text(
          'A gravação ou o arquivo ainda não foram enviados.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Ficar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sair'),
          ),
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
      _messageIsError = false;
      _accepted = false;
      _preview = '';
    });
  }

  Future<void> _listen() async {
    final draft = _draft;
    if (draft == null) return;
    setState(() {
      _message = 'Reproduzindo ${draft.name}.';
      _messageIsError = false;
    });
    try {
      await widget.capture.play(draft.bytes, draft.name);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _message = 'Não foi possível reproduzir este áudio.';
        _messageIsError = true;
      });
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
      _messageIsError = false;
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
        _messageIsError = true;
        _message = detail.isEmpty
            ? 'O transcritor local na porta 8765 não respondeu. O áudio não foi enviado.'
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
      setState(() {
        _message = 'O navegador não autorizou o microfone.';
        _messageIsError = true;
      });
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
      _messageIsError = false;
      _accepted = false;
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
        _preview = '';
        _accepted = true;
        _messageIsError = false;
        _message = 'Áudio aceito nesta demonstração. Ele fica aguardando.';
      });
    } on DiaryFailure catch (error) {
      if (!mounted) return;
      setState(() {
        _accepted = false;
        _messageIsError = true;
        _message = _audioMessage(error.code);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    final draft = _draft;
    final transcribed = widget.repository.entries
        .where(
          (entry) =>
              entry.kind == DiaryKind.audio && entry.transcript.isNotEmpty,
        )
        .toList();
    final select = draft == null
        ? FilledButton.icon(
            onPressed: busy ? null : _pick,
            icon: const Icon(Icons.upload_file),
            label: const Text('Selecionar áudio'),
          )
        : OutlinedButton.icon(
            onPressed: busy ? null : _pick,
            icon: const Icon(Icons.upload_file),
            label: const Text('Selecionar áudio'),
          );
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        DiarySpace.s24,
        DiarySpace.s32,
        DiarySpace.s24,
        DiarySpace.s24,
      ),
      children: [
        Text('Conte com sua voz', style: theme.headlineMedium),
        const SizedBox(height: DiarySpace.s8),
        Text(
          'Você pode enviar um áudio no seu ritmo.',
          style: theme.bodyMedium,
        ),
        const SizedBox(height: DiarySpace.s8),
        Text(
          'O arquivo original permanece. A transcrição, quando existe, não o substitui.',
          style: theme.bodyMedium,
        ),
        const SizedBox(height: DiarySpace.s24),
        DiaryCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('WAV, MP3 ou M4A', style: theme.titleMedium),
              const SizedBox(height: DiarySpace.s4),
              Text(
                'Escolha um arquivo neste aparelho.',
                style: theme.bodyMedium,
              ),
              const SizedBox(height: DiarySpace.s16),
              select,
              if (widget.capture.canRecord) ...[
                const SizedBox(height: DiarySpace.s12),
                OutlinedButton.icon(
                  onPressed: widget.repository.saving ? null : _toggleRecord,
                  icon: Icon(_recording ? Icons.stop : Icons.mic_none),
                  label: Text(
                    _recording
                        ? 'Parar ${_clock(_elapsed)}'
                        : 'Gravar pelo microfone',
                  ),
                ),
              ],
              if (_recording) ...[
                const SizedBox(height: DiarySpace.s12),
                Text(
                  'Gravando. O cronômetro acompanha o tempo real.',
                  style: theme.bodyMedium,
                ),
              ],
              if (draft != null) ...[
                const SizedBox(height: DiarySpace.s16),
                Text(draft.name, style: theme.titleMedium),
                const SizedBox(height: DiarySpace.s4),
                Text(_details(draft), style: theme.bodyMedium),
                const SizedBox(height: DiarySpace.s12),
                OutlinedButton.icon(
                  onPressed: _listen,
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Ouvir antes de enviar'),
                ),
                if (widget.transcribe != null) ...[
                  const SizedBox(height: DiarySpace.s12),
                  OutlinedButton.icon(
                    onPressed: _transcribing ? null : _transcribe,
                    icon: const Icon(Icons.notes_outlined),
                    label: Text(
                      _transcribing
                          ? 'Transcrevendo…'
                          : 'Transcrever antes de enviar',
                    ),
                  ),
                ],
                if (_preview.isNotEmpty) ...[
                  const SizedBox(height: DiarySpace.s16),
                  Text(
                    'Prévia deste áudio, ainda não enviada.',
                    style: theme.titleMedium,
                  ),
                  const SizedBox(height: DiarySpace.s8),
                  Text(_preview, style: theme.bodyLarge?.copyWith(height: 1.5)),
                ],
                const SizedBox(height: DiarySpace.s12),
                FilledButton(
                  onPressed: widget.repository.saving ? null : _send,
                  child: Text(
                    widget.repository.saving ? 'Enviando…' : 'Enviar áudio',
                  ),
                ),
              ],
            ],
          ),
        ),
        if (_message.isNotEmpty) ...[
          const SizedBox(height: DiarySpace.s16),
          if (_accepted) ...[
            const DiaryStatusChip(status: DiaryStatus.queued),
            const SizedBox(height: DiarySpace.s8),
          ],
          Text(
            _message,
            style: _messageIsError
                ? theme.bodyLarge?.copyWith(
                    color: Theme.of(context).colorScheme.error,
                  )
                : theme.bodyLarge,
          ),
        ],
        if (transcribed.isNotEmpty) ...[
          const SizedBox(height: DiarySpace.s24),
          OutlinedButton.icon(
            onPressed: () =>
                setState(() => _transcriptsOpen = !_transcriptsOpen),
            icon: Icon(
              _transcriptsOpen ? Icons.expand_less : Icons.notes_outlined,
            ),
            label: Text(
              _transcriptsOpen ? 'Ocultar transcrições' : 'Ver transcrições',
            ),
          ),
          if (_transcriptsOpen)
            for (final entry in transcribed) ...[
              const SizedBox(height: DiarySpace.s12),
              DiaryCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(entry.fileName, style: theme.titleMedium),
                    const SizedBox(height: DiarySpace.s8),
                    DiaryStatusChip(status: entry.status),
                    const SizedBox(height: DiarySpace.s8),
                    Text(
                      entry.transcript,
                      style: theme.bodyLarge?.copyWith(height: 1.5),
                    ),
                    const SizedBox(height: DiarySpace.s8),
                    Text(
                      'Texto de exemplo já presente no registro. Enviar um áudio nesta tela não cria transcrição.',
                      style: theme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
        ],
      ],
    );
  }

  String _details(AudioDraft draft) {
    final dot = draft.name.lastIndexOf('.');
    final type = dot < 0
        ? 'Arquivo'
        : draft.name.substring(dot + 1).toUpperCase();
    final size = (draft.sizeBytes / 1024).toStringAsFixed(0);
    final duration = draft.duration == null
        ? ''
        : ' · ${_clock(draft.duration!)}';
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
      _ => 'Esse arquivo não serve. Use WAV, MP3 ou M4A.',
    };
  }
}
