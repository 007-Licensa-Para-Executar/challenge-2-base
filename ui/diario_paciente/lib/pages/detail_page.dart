import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/audio_source.dart';
import '../theme/diary_theme.dart';
import '../widgets/diary_components.dart';
import '../widgets/status_chip.dart';

class DetailPage extends StatelessWidget {
  const DetailPage({super.key, required this.entry, required this.capture});

  final DiaryEntry entry;
  final AudioCapture capture;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    final date = MaterialLocalizations.of(context)
        .formatFullDate(entry.createdAt.toLocal());
    final time = MaterialLocalizations.of(context)
        .formatTimeOfDay(TimeOfDay.fromDateTime(entry.createdAt.toLocal()));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Registro'),
        leading: IconButton(
          tooltip: 'Voltar ao histórico',
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back),
        ),
      ),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
              DiarySpace.s24,
              DiarySpace.s16,
              DiarySpace.s24,
              DiarySpace.s32,
            ),
            children: [
              TextButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.arrow_back),
                label: const Text('Voltar ao histórico'),
              ),
              const SizedBox(height: DiarySpace.s8),
              Text('$date · $time', style: theme.bodyMedium),
              const SizedBox(height: DiarySpace.s8),
              Wrap(
                spacing: DiarySpace.s8,
                runSpacing: DiarySpace.s8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(entry.kindLabel, style: theme.titleLarge),
                  DiaryStatusChip(status: entry.status),
                ],
              ),
              if (entry.kind == DiaryKind.written && entry.text.isNotEmpty) ...[
                const SizedBox(height: DiarySpace.s16),
                DiaryCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Texto original', style: theme.titleMedium),
                      const SizedBox(height: DiarySpace.s8),
                      Text(
                        entry.text,
                        style: theme.bodyLarge?.copyWith(height: 1.6),
                      ),
                    ],
                  ),
                ),
              ],
              if (entry.kind == DiaryKind.audio) ...[
                const SizedBox(height: DiarySpace.s16),
                Text(
                  entry.fileName.isEmpty ? 'Áudio original' : entry.fileName,
                  style: theme.titleMedium,
                ),
                if (entry.duration != null) ...[
                  const SizedBox(height: DiarySpace.s4),
                  Text(_clock(entry.duration!), style: theme.bodyMedium),
                ],
                const SizedBox(height: DiarySpace.s8),
                Text(
                  _audioNote(entry),
                  style: theme.bodyLarge?.copyWith(height: 1.5),
                ),
                if (entry.audio != null) ...[
                  const SizedBox(height: DiarySpace.s12),
                  OutlinedButton.icon(
                    onPressed: () =>
                        capture.play(entry.audio!.bytes, entry.audio!.name),
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Ouvir áudio original'),
                  ),
                ],
                if (entry.transcript.isNotEmpty) ...[
                  const SizedBox(height: DiarySpace.s16),
                  DiaryCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Transcrição bruta', style: theme.titleMedium),
                        const SizedBox(height: DiarySpace.s8),
                        Text(
                          entry.transcript,
                          style: theme.bodyLarge?.copyWith(height: 1.6),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }

  String _audioNote(DiaryEntry entry) {
    if (entry.status == DiaryStatus.failed) {
      return 'A transcrição não foi concluída. O arquivo original continua valendo.';
    }
    if (entry.transcript.isEmpty) {
      return 'Ainda não há transcrição. O áudio original é o registro.';
    }
    return 'A transcrição automática pode conter erros. Ela não substitui o arquivo.';
  }

  String _clock(Duration value) {
    final minutes = value.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = value.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }
}
