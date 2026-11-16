import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/diary_repository.dart';
import '../widgets/entry_card.dart';
import '../widgets/quiet_notice.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key, required this.repository, required this.onOpen});

  final DiaryRepository repository;
  final ValueChanged<DiaryEntry> onOpen;

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  DiaryKind? _kind;
  DiaryStatus? _status;

  @override
  Widget build(BuildContext context) {
    final visible = widget.repository.entries.where((entry) {
      if (_kind != null && entry.kind != _kind) return false;
      if (_status != null && entry.status != _status) return false;
      return true;
    }).toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 32, 24, 28),
      children: [
        Text('Histórico', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        const Text(
          'Relatos escritos e áudios ficam separados. A transcrição exibida é fictícia e não substitui o arquivo.',
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilterChip(
              label: const Text('Escritos'),
              selected: _kind == DiaryKind.written,
              onSelected: (selected) => setState(() {
                _kind = selected ? DiaryKind.written : null;
              }),
            ),
            FilterChip(
              label: const Text('Áudios'),
              selected: _kind == DiaryKind.audio,
              onSelected: (selected) => setState(() {
                _kind = selected ? DiaryKind.audio : null;
              }),
            ),
            for (final status in DiaryStatus.values)
              FilterChip(
                label: Text(_statusName(status)),
                selected: _status == status,
                onSelected: (selected) => setState(() {
                  _status = selected ? status : null;
                }),
              ),
          ],
        ),
        const SizedBox(height: 16),
        if (widget.repository.loading)
          const Center(child: CircularProgressIndicator())
        else if (widget.repository.failure != null)
          const QuietNotice(
            icon: Icons.cloud_off_outlined,
            text: 'Não foi possível carregar o histórico.',
          )
        else if (widget.repository.entries.isEmpty)
          const QuietNotice(text: 'Nenhum registro ainda. Você pode começar por um relato.')
        else if (visible.isEmpty)
          const QuietNotice(text: 'Nenhum registro com esse filtro.')
        else
          ..._grouped(context, visible),
      ],
    );
  }

  List<Widget> _grouped(BuildContext context, List<DiaryEntry> visible) {
    final widgets = <Widget>[];
    String? lastDay;
    for (final entry in visible) {
      final day = MaterialLocalizations.of(context).formatFullDate(entry.createdAt.toLocal());
      if (day != lastDay) {
        widgets.add(
          Padding(
            padding: EdgeInsets.only(top: lastDay == null ? 4 : 12, bottom: 8),
            child: Text(day, style: Theme.of(context).textTheme.titleMedium),
          ),
        );
        lastDay = day;
      }
      widgets.add(EntryCard(entry: entry, onOpen: () => widget.onOpen(entry)));
      widgets.add(const SizedBox(height: 12));
    }
    return widgets;
  }

  String _statusName(DiaryStatus status) => switch (status) {
        DiaryStatus.queued => 'Aguardando',
        DiaryStatus.processing => 'Processando',
        DiaryStatus.ready => 'Concluído',
        DiaryStatus.failed => 'Erro',
      };
}
