import 'package:flutter/material.dart';

import '../models/diary_entry.dart';
import '../pages/audio_page.dart';
import '../pages/detail_page.dart';
import '../pages/history_page.dart';
import '../pages/home_page.dart';
import '../pages/write_page.dart';
import '../services/audio_source.dart';
import '../services/diary_repository.dart';
import '../theme/diary_theme.dart';

class DiaryShell extends StatefulWidget {
  const DiaryShell({super.key, required this.repository, required this.capture});

  final DiaryRepository repository;
  final AudioCapture capture;

  @override
  State<DiaryShell> createState() => _DiaryShellState();
}

class _DiaryShellState extends State<DiaryShell> {
  int _index = 0;
  final _writeKey = GlobalKey<WritePageState>();
  final _audioKey = GlobalKey<AudioPageState>();

  Future<void> _select(int index) async {
    if (index == _index) return;
    if (_index == 1 && await _writeKey.currentState?.confirmLeave() == false) return;
    if (_index == 2 && await _audioKey.currentState?.confirmLeave() == false) return;
    if (!mounted) return;
    setState(() => _index = index);
  }

  void _open(DiaryEntry entry) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => DetailPage(entry: entry, capture: widget.capture),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 768;
    final pages = [
      HomePage(
        repository: widget.repository,
        onWrite: () {
          _select(1);
        },
        onAudio: () {
          _select(2);
        },
        onOpen: _open,
      ),
      WritePage(key: _writeKey, repository: widget.repository),
      AudioPage(key: _audioKey, repository: widget.repository, capture: widget.capture),
      HistoryPage(repository: widget.repository, onOpen: _open),
    ];
    final body = Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: IndexedStack(index: _index, children: pages),
      ),
    );
    if (wide) {
      return Scaffold(
        body: Row(
          children: [
            _Sidebar(
              index: _index,
              onSelect: (index) {
                _select(index);
              },
            ),
            const VerticalDivider(width: 1),
            Expanded(child: body),
          ],
        ),
      );
    }
    return Scaffold(
      body: body,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (index) {
          _select(index);
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Início'),
          NavigationDestination(icon: Icon(Icons.edit_outlined), label: 'Escrever'),
          NavigationDestination(icon: Icon(Icons.mic_none), label: 'Áudio'),
          NavigationDestination(icon: Icon(Icons.history), label: 'Histórico'),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.index, required this.onSelect});

  final int index;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    const items = [
      (Icons.home_outlined, 'Início'),
      (Icons.edit_outlined, 'Escrever'),
      (Icons.mic_none, 'Áudio'),
      (Icons.history, 'Histórico'),
    ];
    return NavigationRail(
      backgroundColor: cardWhite,
      selectedIndex: index,
      onDestinationSelected: (index) {
        onSelect(index);
      },
      labelType: NavigationRailLabelType.all,
      selectedIconTheme: const IconThemeData(color: sage),
      destinations: [
        for (final item in items)
          NavigationRailDestination(icon: Icon(item.$1), label: Text(item.$2)),
      ],
    );
  }
}
