import 'package:flutter/material.dart';

import '../theme/diary_theme.dart';

class MoodChoice {
  const MoodChoice(this.emoji, this.label);

  final String emoji;
  final String label;
}

const moodChoices = <MoodChoice>[
  MoodChoice('😊', 'Bem'),
  MoodChoice('😌', 'Tranquilo'),
  MoodChoice('😐', 'Neutro'),
  MoodChoice('😔', 'Triste'),
  MoodChoice('😟', 'Ansioso'),
  MoodChoice('😤', 'Frustrado'),
];

/// Seleção única e opcional. O valor fica no estado da tela.
class MoodSelector extends StatelessWidget {
  const MoodSelector({super.key, required this.value, required this.onChanged});

  final String? value;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: 'Check-in de humor, opcional',
      child: LayoutBuilder(
        builder: (context, constraints) {
          final scale = MediaQuery.textScalerOf(context).scale(16) / 16;
          final columns = constraints.maxWidth >= 560 && scale < 1.6 ? 3 : 2;
          return Column(
            children: [
              for (
                var index = 0;
                index < moodChoices.length;
                index += columns
              ) ...[
                if (index > 0) const SizedBox(height: DiarySpace.s8),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (var column = 0; column < columns; column++) ...[
                      if (column > 0) const SizedBox(width: DiarySpace.s8),
                      Expanded(child: _tile(index + column)),
                    ],
                  ],
                ),
              ],
            ],
          );
        },
      ),
    );
  }

  Widget _tile(int index) {
    final choice = moodChoices[index];
    return MoodOptionButton(
      choice: choice,
      selected: value == choice.label,
      onPressed: () => onChanged(value == choice.label ? null : choice.label),
    );
  }
}

class MoodOptionButton extends StatelessWidget {
  const MoodOptionButton({
    super.key,
    required this.choice,
    required this.selected,
    required this.onPressed,
  });

  final MoodChoice choice;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return MergeSemantics(
      child: Semantics(
        selected: selected,
        child: OutlinedButton(
          onPressed: onPressed,
          style: ButtonStyle(
            minimumSize: const WidgetStatePropertyAll(Size(48, 48)),
            padding: const WidgetStatePropertyAll(
              EdgeInsets.symmetric(
                horizontal: DiarySpace.s8,
                vertical: DiarySpace.s8,
              ),
            ),
            tapTargetSize: MaterialTapTargetSize.padded,
            visualDensity: VisualDensity.standard,
            elevation: const WidgetStatePropertyAll(0),
            overlayColor: const WidgetStatePropertyAll(Colors.transparent),
            foregroundColor: const WidgetStatePropertyAll(graphite),
            backgroundColor: WidgetStateProperty.resolveWith((states) {
              if (states.contains(WidgetState.pressed)) {
                return deepSage.withValues(alpha: 0.16);
              }
              if (selected) return mist;
              if (states.contains(WidgetState.hovered)) {
                return sage.withValues(alpha: 0.12);
              }
              return cardWhite;
            }),
            side: WidgetStateProperty.resolveWith((states) {
              if (states.contains(WidgetState.focused)) {
                return const BorderSide(color: deepSage, width: 3);
              }
              if (selected) return const BorderSide(color: deepSage, width: 2);
              return const BorderSide(color: line);
            }),
            shape: const WidgetStatePropertyAll(
              RoundedRectangleBorder(
                borderRadius: BorderRadius.all(Radius.circular(DiaryRadius.md)),
              ),
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ExcludeSemantics(
                child: Text(
                  choice.emoji,
                  style: const TextStyle(fontSize: 22, height: 1.2),
                ),
              ),
              const SizedBox(height: DiarySpace.s4),
              Text(
                choice.label,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
