import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../theme/diary_theme.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status});

  final DiaryStatus status;

  @override
  Widget build(BuildContext context) {
    final label = switch (status) {
      DiaryStatus.queued => 'Aguardando',
      DiaryStatus.processing => 'Processando',
      DiaryStatus.ready => 'Concluído',
      DiaryStatus.failed => 'Erro',
    };
    final color = switch (status) {
      DiaryStatus.failed => Theme.of(context).colorScheme.error,
      DiaryStatus.processing => sage,
      _ => graphite,
    };
    return Semantics(
      label: 'Status $label',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: status == DiaryStatus.failed ? const Color(0xFFF6E8E6) : mist,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label, style: TextStyle(color: color, fontSize: 13)),
      ),
    );
  }
}
