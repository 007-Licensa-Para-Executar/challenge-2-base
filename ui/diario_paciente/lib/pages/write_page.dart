import 'package:flutter/material.dart';

import '../services/diary_repository.dart';
import '../theme/diary_theme.dart';

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
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Continuar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sair'),
          ),
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
        const SnackBar(
          content: Text(
            'Anotado nesta demonstração. Nada foi gravado em banco.',
          ),
        ),
      );
    } on DiaryFailure catch (error) {
      if (!mounted) return;
      final message = error.code == 'text_too_long'
          ? 'O relato passa de 20 mil caracteres.'
          : 'Escreva alguma coisa antes de salvar.';
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    final length = _controller.text.length;
    final inset = MediaQuery.viewInsetsOf(context).bottom;
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
              DiarySpace.s24,
              DiarySpace.s32,
              DiarySpace.s24,
              DiarySpace.s12,
            ),
            children: [
              Text('Escreva sobre seu dia', style: theme.headlineMedium),
              const SizedBox(height: DiarySpace.s8),
              Text(
                'Não precisa encontrar as palavras perfeitas.',
                style: theme.bodyMedium,
              ),
              const SizedBox(height: DiarySpace.s24),
              TextField(
                controller: _controller,
                minLines: 12,
                maxLines: null,
                // shortcut: 20 mil é o teto do repositório de demonstração, não um limite de palavras.
                maxLength: 20000,
                keyboardType: TextInputType.multiline,
                textCapitalization: TextCapitalization.sentences,
                onChanged: (_) => setState(() {}),
                style: theme.bodyLarge?.copyWith(height: 1.6),
                decoration: const InputDecoration(
                  hintText: 'O que aconteceu hoje?',
                  alignLabelWithHint: true,
                  contentPadding: EdgeInsets.all(DiarySpace.s16),
                ),
                buildCounter:
                    (
                      context, {
                      required currentLength,
                      required isFocused,
                      maxLength,
                    }) {
                      return Padding(
                        padding: const EdgeInsets.only(top: DiarySpace.s8),
                        child: Align(
                          alignment: Alignment.centerRight,
                          child: Text(
                            '$currentLength / $maxLength',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                      );
                    },
              ),
            ],
          ),
        ),
        Padding(
          padding: EdgeInsets.fromLTRB(
            DiarySpace.s24,
            DiarySpace.s8,
            DiarySpace.s24,
            DiarySpace.s16 + inset,
          ),
          child: FilledButton(
            onPressed: widget.repository.saving || length == 0 ? null : _save,
            child: Text(
              widget.repository.saving ? 'Salvando…' : 'Salvar relato',
            ),
          ),
        ),
      ],
    );
  }
}
