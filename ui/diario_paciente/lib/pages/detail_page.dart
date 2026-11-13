import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/audio_source.dart';
import '../widgets/status_chip.dart';

class DetailPage extends StatelessWidget {
  const DetailPage({super.key, required this.entry, required this.capture});

  final DiaryEntry entry;
  final AudioCapture capture;

  @override
  Widget build(BuildContext context) {
    final date = MaterialLocalizations.of(context).formatFullDate(entry.createdAt.toLocal());
    final time = MaterialLocalizations.of(context).formatTimeOfDay(
      TimeOfDay.fromDateTime(entry.createdAt.toLocal()),
    );
    return Scaffold(
      appBar: AppBar(title: const Text('Registro')),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text('$date · $time', style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(entry.kindLabel, style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(width: 12),
                  StatusChip(status: entry.status),
                ],
              ),
              if (entry.manualMood.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text('Humor informado: ${entry.manualMood}'),
              ],
              if (entry.text.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text('Texto original', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(entry.text),
              ],
              if (entry.kind == DiaryKind.audio) ...[
                const SizedBox(height: 20),
                Text(entry.fileName.isEmpty ? 'Áudio original' : entry.fileName),
                const SizedBox(height: 8),
                const Text(
                  'A transcrição automática pode conter erros. Ela não substitui o arquivo original.',
                ),
                if (entry.audio != null) ...[
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () => capture.play(entry.audio!.bytes, entry.audio!.name),
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Ouvir áudio original'),
                  ),
                ],
              ],
              if (entry.transcript.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text('Transcrição bruta', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(entry.transcript),
              ],
              if (entry.errorCode.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text('A transcrição não foi concluída (${entry.errorCode}).'),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
