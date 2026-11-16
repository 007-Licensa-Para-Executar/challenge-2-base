import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../theme/diary_theme.dart';

class DiaryStatusChip extends StatelessWidget {
  const DiaryStatusChip({super.key, required this.status});

  final DiaryStatus status;

  @override
  Widget build(BuildContext context) {
    final (label, color, icon, background) = switch (status) {
      DiaryStatus.queued => ('Aguardando', graphite, Icons.schedule, mist),
      DiaryStatus.processing => (
        'Processando',
        deepSage,
        Icons.autorenew,
        mist,
      ),
      DiaryStatus.ready => ('Concluído', deepSage, Icons.check, mist),
      DiaryStatus.failed => (
        'Erro',
        Theme.of(context).colorScheme.error,
        Icons.error_outline,
        errorMist,
      ),
    };
    return Semantics(
      label: 'Status $label',
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DiarySpace.s12,
          vertical: DiarySpace.s4,
        ),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Wrap(
          spacing: DiarySpace.s4,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Icon(icon, size: 16, color: color),
            Text(
              label,
              style: TextStyle(color: color, fontSize: 14, height: 1.3),
            ),
          ],
        ),
      ),
    );
  }
}

typedef StatusChip = DiaryStatusChip;
