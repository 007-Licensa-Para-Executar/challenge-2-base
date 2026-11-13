import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../theme/diary_theme.dart';
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
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onOpen,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Icon(
                    entry.kind == DiaryKind.written
                        ? Icons.edit_outlined
                        : Icons.graphic_eq,
                    size: 18,
                    color: sage,
                  ),
                  Text(entry.kindLabel, style: Theme.of(context).textTheme.bodyMedium),
                  StatusChip(status: entry.status),
                ],
              ),
              const SizedBox(height: 8),
              Text(date, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 8),
              Text(shown, maxLines: 3, overflow: TextOverflow.ellipsis),
            ],
          ),
        ),
      ),
    );
  }
}
