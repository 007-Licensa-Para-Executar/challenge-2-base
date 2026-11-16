import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../services/diary_repository.dart';
import '../theme/diary_theme.dart';
import '../widgets/entry_card.dart';
import '../widgets/quiet_notice.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({
    super.key,
    required this.repository,
    required this.onOpen,
  });

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
    final theme = Theme.of(context).textTheme;
    final visible = widget.repository.entries.where((entry) {
      if (_kind != null && entry.kind != _kind) return false;
      if (_status != null && entry.status != _status) return false;
      return true;
    }).toList()..sort(compareEntriesNewestFirst);
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        DiarySpace.s24,
        DiarySpace.s32,
        DiarySpace.s24,
        DiarySpace.s24,
      ),
      children: [
        Text('Seus registros', style: theme.headlineMedium),
        const SizedBox(height: DiarySpace.s8),
        Text(
          'Do mais recente ao mais antigo. São exemplos desta demonstração.',
          style: theme.bodyMedium,
        ),
        const SizedBox(height: DiarySpace.s16),
        Wrap(
          spacing: DiarySpace.s8,
          runSpacing: DiarySpace.s8,
          children: [
            FilterChip(
              label: const Text('Todos'),
              selected: _kind == null,
              onSelected: (_) => setState(() => _kind = null),
            ),
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
        const SizedBox(height: DiarySpace.s16),
        if (widget.repository.loading)
          const Center(child: CircularProgressIndicator())
        else if (widget.repository.failure != null)
          const QuietNotice(
            icon: Icons.cloud_off_outlined,
            text: 'Não foi possível carregar o histórico.',
          )
        else if (widget.repository.entries.isEmpty)
          const QuietNotice(
            text: 'Nenhum registro ainda. Você pode começar por um relato.',
          )
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
      final day = MaterialLocalizations.of(context)
          .formatFullDate(entry.createdAt.toLocal());
      if (day != lastDay) {
        widgets.add(
          Padding(
            padding: EdgeInsets.only(
              top: lastDay == null ? DiarySpace.s4 : DiarySpace.s12,
              bottom: DiarySpace.s8,
            ),
            child: Text(day, style: Theme.of(context).textTheme.titleMedium),
          ),
        );
        lastDay = day;
      }
      widgets.add(EntryCard(entry: entry, onOpen: () => widget.onOpen(entry)));
      widgets.add(const SizedBox(height: DiarySpace.s12));
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
