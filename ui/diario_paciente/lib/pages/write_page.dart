import 'package:flutter/material.dart';

import '../services/diary_repository.dart';

class WritePage extends StatefulWidget {
  const WritePage({super.key, required this.repository});

  final DiaryRepository repository;

  @override
  State<WritePage> createState() => WritePageState();
}

class WritePageState extends State<WritePage> {
  final _controller = TextEditingController();
  String _mood = '';
  static const _moods = ['Calma', 'Alegria', 'Preocupação', 'Tristeza'];

  bool get dirty => _controller.text.trim().isNotEmpty;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<bool> confirmLeave() async {
    if (!dirty) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sair sem salvar?'),
        content: const Text('O texto desta tela ainda não foi gravado.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Continuar')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Sair')),
        ],
      ),
    );
    return leave ?? false;
  }

  Future<void> _save() async {
    if (widget.repository.saving) return;
    try {
      await widget.repository.saveText(_controller.text, mood: _mood);
      if (!mounted) return;
      _controller.clear();
      setState(() => _mood = '');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Relato gravado.')),
      );
    } on DiaryFailure catch (error) {
      if (!mounted) return;
      final message = error.code == 'text_too_long'
          ? 'O relato passa de 20 mil caracteres.'
          : 'Escreva alguma coisa antes de salvar.';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final length = _controller.text.length;
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 28, 20, 12),
            children: [
              Text('Escrever relato', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 8),
              const Text('O texto fica como você escreveu. Nada é reescrito automaticamente.'),
              const SizedBox(height: 20),
              TextField(
          controller: _controller,
          minLines: 8,
          maxLines: 16,
          maxLength: 20000,
          onChanged: (_) => setState(() {}),
          decoration: const InputDecoration(
            hintText: 'Escreva com calma.',
            alignLabelWithHint: true,
          ),
          buildCounter: (context, {required currentLength, required isFocused, maxLength}) {
            return Text(
              '$currentLength / $maxLength',
              style: Theme.of(context).textTheme.bodyMedium,
            );
          },
        ),
        const SizedBox(height: 8),
        Text('Humor informado por você, se quiser.', style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final mood in _moods)
              ChoiceChip(
                label: Text(mood),
                selected: _mood == mood,
                onSelected: (selected) => setState(() => _mood = selected ? mood : ''),
              ),
          ],
        ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
          child: FilledButton(
            onPressed: widget.repository.saving || length == 0 ? null : _save,
            child: Text(widget.repository.saving ? 'Salvando…' : 'Salvar relato'),
          ),
        ),
      ],
    );
  }
}
