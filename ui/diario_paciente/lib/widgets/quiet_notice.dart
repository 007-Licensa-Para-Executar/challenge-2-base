import 'package:flutter/material.dart';

import '../theme/diary_theme.dart';
import 'diary_components.dart';

class DiaryEmptyState extends StatelessWidget {
  const DiaryEmptyState({super.key, required this.text, this.icon = Icons.spa_outlined});

  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return DiaryCard(
      padding: const EdgeInsets.symmetric(horizontal: DiarySpace.s24, vertical: DiarySpace.s32),
      child: Column(
        children: [
          Icon(icon, color: deepSage, size: 28),
          const SizedBox(height: DiarySpace.s12),
          Text(text, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
        ],
      ),
    );
  }
}

typedef QuietNotice = DiaryEmptyState;
