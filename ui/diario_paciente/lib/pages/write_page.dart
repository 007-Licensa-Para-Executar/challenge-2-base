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
      await widget.repository.saveText(_controller.text);
      if (!mounted) return;
      _controller.clear();
      setState(() {});
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Anotado nesta demonstração. Nada foi gravado em banco.')),
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
            padding: const EdgeInsets.fromLTRB(24, 32, 24, 12),
            children: [
              Text('Escrever relato', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 8),
              const Text('O texto fica como você escreveu. Nada é reescrito automaticamente.'),
              const SizedBox(height: 4),
              const Text('Nesta demonstração o relato não vai para um banco.'),
              const SizedBox(height: 20),
              TextField(
                controller: _controller,
                minLines: 12,
                maxLines: 18,
                maxLength: 20000,
                onChanged: (_) => setState(() {}),
                style: Theme.of(context).textTheme.bodyLarge,
                decoration: const InputDecoration(
                  hintText: 'O que você quer anotar hoje?',
                  alignLabelWithHint: true,
                  contentPadding: EdgeInsets.all(20),
                ),
                buildCounter: (context, {required currentLength, required isFocused, maxLength}) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      '$currentLength / $maxLength',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  );
                },
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 16),
          child: FilledButton(
            onPressed: widget.repository.saving || length == 0 ? null : _save,
            child: Text(widget.repository.saving ? 'Salvando…' : 'Salvar relato'),
          ),
        ),
      ],
    );
  }
}
