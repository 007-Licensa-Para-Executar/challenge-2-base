import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../theme/diary_theme.dart';
import 'diary_components.dart';
import 'status_chip.dart';

class EntryCard extends StatelessWidget {
  const EntryCard({super.key, required this.entry, required this.onOpen});

  final DiaryEntry entry;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final date = MaterialLocalizations.of(context).formatFullDate(entry.createdAt.toLocal());
    final preview = entry.preview;
    final shown = preview.length > 140 ? '${preview.substring(0, 140)}…' : preview;
    final accent = entry.kind == DiaryKind.written ? deepSage : sage;
    return DiaryCard(
      onTap: onOpen,
      padding: EdgeInsets.zero,
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ColoredBox(color: accent, child: const SizedBox(width: DiarySpace.s4)),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(DiarySpace.s16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: DiarySpace.s8,
                      runSpacing: DiarySpace.s8,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Icon(
                          entry.kind == DiaryKind.written ? Icons.edit_outlined : Icons.graphic_eq,
                          size: 18,
                          color: deepSage,
                        ),
                        Text(entry.kindLabel, style: Theme.of(context).textTheme.bodyMedium),
                        DiaryStatusChip(status: entry.status),
                      ],
                    ),
                    const SizedBox(height: DiarySpace.s8),
                    Text(date, style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: DiarySpace.s8),
                    Text(shown, maxLines: 3, overflow: TextOverflow.ellipsis),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
