import 'package:flutter/material.dart';

import '../theme/diary_theme.dart';

class QuietNotice extends StatelessWidget {
  const QuietNotice({super.key, required this.text, this.icon = Icons.spa_outlined});

  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 28),
        child: Column(
          children: [
            Icon(icon, color: sage, size: 28),
            const SizedBox(height: 12),
            Text(text, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
          ],
        ),
      ),
    );
  }
}
