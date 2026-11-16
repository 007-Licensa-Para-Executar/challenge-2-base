import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/diary_repository.dart';
import '../theme/diary_theme.dart';
import '../widgets/action_card.dart';
import '../widgets/diary_components.dart';
import '../widgets/entry_card.dart';
import '../widgets/mood_selector.dart';
import '../widgets/quiet_notice.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.repository,
    required this.onWrite,
    required this.onAudio,
    required this.onHistory,
    required this.onOpen,
  });

  final DiaryRepository repository;
  final VoidCallback onWrite;
  final VoidCallback onAudio;
  final VoidCallback onHistory;
  final ValueChanged<DiaryEntry> onOpen;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String? _mood;

  @override
  Widget build(BuildContext context) {
    final recent =
        (widget.repository.entries.toList()..sort(compareEntriesNewestFirst))
            .take(3)
            .toList();
    final theme = Theme.of(context).textTheme;
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        DiarySpace.s24,
        DiarySpace.s32,
        DiarySpace.s24,
        DiarySpace.s24,
      ),
      children: [
        Text(_greeting(), style: theme.bodyMedium?.copyWith(color: deepSage)),
        const SizedBox(height: DiarySpace.s8),
        Text('Como você está hoje?', style: theme.headlineMedium),
        const SizedBox(height: DiarySpace.s8),
        Text('Uma palavra basta, se você quiser.', style: theme.bodyMedium),
        const SizedBox(height: DiarySpace.s16),
        MoodSelector(
          value: _mood,
          onChanged: (value) => setState(() => _mood = value),
        ),
        const SizedBox(height: DiarySpace.s8),
        Text(
          'Só nesta tela. Não é salvo e não é um diagnóstico.',
          style: theme.bodySmall,
        ),
        const SizedBox(height: DiarySpace.s24),
        LayoutBuilder(
          builder: (context, constraints) {
            final write = ActionCard(
              icon: Icons.edit_outlined,
              title: 'Escrever relato',
              subtitle: 'Anote com as suas palavras.',
              onTap: widget.onWrite,
            );
            final audio = ActionCard(
              icon: Icons.mic_none,
              title: 'Gravar ou enviar áudio',
              subtitle: 'O áudio original permanece.',
              onTap: widget.onAudio,
            );
            if (constraints.maxWidth < 560) {
              return Column(
                children: [
                  write,
                  const SizedBox(height: DiarySpace.s12),
                  audio,
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: write),
                const SizedBox(width: DiarySpace.s12),
                Expanded(child: audio),
              ],
            );
          },
        ),
        const SizedBox(height: DiarySpace.s24),
        if (widget.repository.loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: DiarySpace.s24),
            child: Center(child: CircularProgressIndicator()),
          )
        else ...[
          LayoutBuilder(
            builder: (context, constraints) {
              final header = DiarySectionHeader(
                title: 'Recentes',
                subtitle: recent.isEmpty
                    ? null
                    : 'Exemplos desta demonstração.',
              );
              final action = TextButton(
                style: TextButton.styleFrom(alignment: Alignment.centerLeft),
                onPressed: widget.onHistory,
                child: const Text('Ver histórico'),
              );
              if (constraints.maxWidth < 480) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    header,
                    SizedBox(width: double.infinity, child: action),
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: header),
                  action,
                ],
              );
            },
          ),
          const SizedBox(height: DiarySpace.s12),
          if (widget.repository.failure != null)
            const QuietNotice(
              icon: Icons.cloud_off_outlined,
              text: 'Não foi possível carregar os registros.',
            )
          else if (recent.isEmpty)
            const QuietNotice(
              text: 'Nenhum registro ainda. Você pode começar por um relato.',
            )
          else
            for (final entry in recent) ...[
              EntryCard(entry: entry, onOpen: () => widget.onOpen(entry)),
              const SizedBox(height: DiarySpace.s12),
            ],
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
