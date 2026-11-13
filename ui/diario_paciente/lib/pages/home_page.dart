import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/diary_repository.dart';
import '../theme/diary_theme.dart';
import '../widgets/entry_card.dart';

class HomePage extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final recent = repository.entries.take(3).toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
      children: [
        Text(_greeting(), style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text(
          'Como você está se sentindo hoje?',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Text(
          'Estes registros são fictícios nesta demonstração. Nada aqui é um diagnóstico.',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 24),
        _ActionCard(
          icon: Icons.edit_outlined,
          title: 'Escrever relato',
          subtitle: 'Um texto só seu, guardado como foi escrito.',
          onTap: onWrite,
        ),
        const SizedBox(height: 12),
        _ActionCard(
          icon: Icons.mic_none,
          title: 'Gravar ou enviar áudio',
          subtitle: 'WAV, MP3 ou M4A. A transcrição não substitui o arquivo.',
          onTap: onAudio,
        ),
        const SizedBox(height: 28),
        Text('Recentes', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        if (repository.loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (repository.failure != null)
          const _Notice(text: 'Não foi possível carregar os registros.')
        else if (recent.isEmpty)
          const _Notice(text: 'Nenhum registro ainda. Você pode começar por um relato.')
        else
          for (final entry in recent) ...[
            EntryCard(entry: entry, onOpen: () => onOpen(entry)),
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

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            children: [
              Icon(icon, color: sage),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(subtitle),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(text, style: Theme.of(context).textTheme.bodyLarge);
  }
}
