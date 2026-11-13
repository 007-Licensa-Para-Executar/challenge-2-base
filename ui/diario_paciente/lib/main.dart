import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'services/audio_source.dart';
import 'services/audio_source_factory.dart';
import 'services/diary_repository.dart';
import 'services/fake_diary_repository.dart';
import 'theme/diary_theme.dart';
import 'widgets/diary_shell.dart';

void main() {
  runApp(DiaryApp(
    repository: FakeDiaryRepository(),
    capture: createAudioCapture(),
  ));
}

class DiaryApp extends StatelessWidget {
  const DiaryApp({super.key, required this.repository, required this.capture});

  final DiaryRepository repository;
  final AudioCapture capture;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Diário',
      debugShowCheckedModeBanner: false,
      theme: diaryTheme(),
      locale: const Locale('pt', 'BR'),
      supportedLocales: const [Locale('pt', 'BR')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: ListenableBuilder(
        listenable: repository,
        builder: (context, _) => DiaryShell(repository: repository, capture: capture),
      ),
    );
  }
}
