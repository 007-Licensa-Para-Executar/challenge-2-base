import 'package:flutter/material.dart';

import '../theme/diary_theme.dart';
import 'diary_components.dart';

class ActionCard extends StatelessWidget {
  const ActionCard({
    super.key,
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
    return DiaryCard(
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 96),
        child: Row(
          children: [
            DecoratedBox(
              decoration: const BoxDecoration(color: mist, shape: BoxShape.circle),
              child: Padding(
                padding: const EdgeInsets.all(DiarySpace.s12),
                child: Icon(icon, color: deepSage),
              ),
            ),
            const SizedBox(width: DiarySpace.s16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: DiarySpace.s4),
                  Text(subtitle),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
