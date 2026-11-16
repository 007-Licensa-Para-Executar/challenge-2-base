import 'package:flutter/material.dart';

import '../theme/diary_theme.dart';

class DiaryCard extends StatelessWidget {
  const DiaryCard({
    super.key,
    required this.child,
    this.onTap,
    this.padding = const EdgeInsets.all(DiarySpace.s16),
  });

  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final content = Padding(padding: padding, child: child);
    return Card(
      clipBehavior: Clip.antiAlias,
      child: onTap == null
          ? content
          : InkWell(
              onTap: onTap,
              hoverColor: deepSage.withValues(alpha: 0.06),
              focusColor: deepSage.withValues(alpha: 0.16),
              splashColor: deepSage.withValues(alpha: 0.12),
              child: content,
            ),
    );
  }
}

class DiaryPrimaryButton extends StatelessWidget {
  const DiaryPrimaryButton({
    super.key,
    required this.onPressed,
    required this.label,
    this.icon,
  });

  final VoidCallback? onPressed;
  final String label;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    if (icon == null) {
      return FilledButton(onPressed: onPressed, child: Text(label));
    }
    return FilledButton.icon(onPressed: onPressed, icon: Icon(icon), label: Text(label));
  }
}

class DiarySecondaryButton extends StatelessWidget {
  const DiarySecondaryButton({
    super.key,
    required this.onPressed,
    required this.label,
    this.icon,
  });

  final VoidCallback? onPressed;
  final String label;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    if (icon == null) {
      return OutlinedButton(onPressed: onPressed, child: Text(label));
    }
    return OutlinedButton.icon(onPressed: onPressed, icon: Icon(icon), label: Text(label));
  }
}

class DiarySectionHeader extends StatelessWidget {
  const DiarySectionHeader({super.key, required this.title, this.subtitle});

  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: theme.titleLarge),
        if (subtitle != null) ...[
          const SizedBox(height: DiarySpace.s8),
          Text(subtitle!, style: theme.bodyMedium),
        ],
      ],
    );
  }
}

class DiaryNavigationItem {
  const DiaryNavigationItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });

  final IconData icon;
  final IconData selectedIcon;
  final String label;
}

const diaryDestinations = <DiaryNavigationItem>[
  DiaryNavigationItem(icon: Icons.home_outlined, selectedIcon: Icons.home, label: 'Início'),
  DiaryNavigationItem(icon: Icons.edit_outlined, selectedIcon: Icons.edit, label: 'Escrever'),
  DiaryNavigationItem(icon: Icons.mic_none, selectedIcon: Icons.mic, label: 'Áudio'),
  DiaryNavigationItem(icon: Icons.history, selectedIcon: Icons.history, label: 'Histórico'),
];
