import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/diary_repository.dart';
import '../theme/diary_theme.dart';
import '../widgets/action_card.dart';
import '../widgets/entry_card.dart';
import '../widgets/mood_selector.dart';
import '../widgets/quiet_notice.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.repository,
    required this.onWrite,
    required this.onAudio,
    required this.onOpen,
  });

  final DiaryRepository repository;
  final VoidCallback onWrite;
  final VoidCallback onAudio;
  final ValueChanged<DiaryEntry> onOpen;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String? _mood;

  @override
  Widget build(BuildContext context) {
    final recent = widget.repository.entries.take(3).toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 32, 24, 28),
      children: [
        Text(_greeting(), style: Theme.of(context).textTheme.titleMedium?.copyWith(color: deepSage)),
        const SizedBox(height: 8),
        Text('Como você está se sentindo hoje?', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        const Text('Um instante para perceber o dia, se você quiser.'),
        const SizedBox(height: 20),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Check-in', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                const Text('Opcional. Toque de novo para desmarcar.'),
                const SizedBox(height: 14),
                MoodSelector(
                  value: _mood,
                  onChanged: (value) => setState(() => _mood = value),
                ),
                const SizedBox(height: 14),
                const Text(
                  'Esta escolha fica só nesta tela. Ela não é salva, não é enviada e não é um diagnóstico.',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final write = ActionCard(
              icon: Icons.edit_outlined,
              title: 'Escrever relato',
              subtitle: 'Um texto só seu, do jeito que você escreveu.',
              onTap: widget.onWrite,
            );
            final audio = ActionCard(
              icon: Icons.mic_none,
              title: 'Gravar ou enviar áudio',
              subtitle: 'WAV, MP3 ou M4A. A transcrição não substitui o arquivo.',
              onTap: widget.onAudio,
            );
            if (constraints.maxWidth < 560) {
              return Column(children: [write, const SizedBox(height: 12), audio]);
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: write),
                const SizedBox(width: 12),
                Expanded(child: audio),
              ],
            );
          },
        ),
        const SizedBox(height: 28),
        Text('Recentes', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        if (widget.repository.loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (widget.repository.failure != null)
          const QuietNotice(
            icon: Icons.cloud_off_outlined,
            text: 'Não foi possível carregar os registros.',
          )
        else if (recent.isEmpty)
          const QuietNotice(text: 'Nenhum registro ainda. Você pode começar por um relato.')
        else
          for (final entry in recent) ...[
            EntryCard(entry: entry, onOpen: () => widget.onOpen(entry)),
            const SizedBox(height: 12),
          ],
      ],
    );
  }

  String _greeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Bom dia';
    if (hour < 18) return 'Boa tarde';
    return 'Boa noite';
  }
}
