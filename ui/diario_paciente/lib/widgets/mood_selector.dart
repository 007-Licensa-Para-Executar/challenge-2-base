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
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final choice in moodChoices)
            ChoiceChip(
              label: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ExcludeSemantics(child: Text(choice.emoji, style: const TextStyle(fontSize: 18))),
                  const SizedBox(width: 6),
                  Text(choice.label),
                ],
              ),
              selected: value == choice.label,
              showCheckmark: false,
              selectedColor: mist,
              side: BorderSide(color: value == choice.label ? deepSage : line),
              onSelected: (selected) => onChanged(selected ? choice.label : null),
            ),
        ],
      ),
    );
  }
}
