// TubeCutter Mobile — szkielet Flutter (Android).
// Motyw: #15121E tło, #8B5CF6 fiolet, #2DD4BF mięta, tekst #E5E4F0.
// 4 zakładki w dolnym pasku; ekran CD z CustomPainter (łuk zajętego miejsca).

import 'dart:math' as math;
import 'package:flutter/material.dart';

const kBg = Color(0xFF15121E);
const kSurface = Color(0xFF1E1A2B);
const kAccent = Color(0xFF8B5CF6);
const kMint = Color(0xFF2DD4BF);
const kText = Color(0xFFE5E4F0);
const kTextDim = Color(0xFF9B97AD);

void main() => runApp(const TubeCutterApp());

class TubeCutterApp extends StatelessWidget {
  const TubeCutterApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TubeCutter',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: kBg,
        colorScheme: const ColorScheme.dark(
          primary: kAccent, secondary: kMint, surface: kSurface,
        ),
        textTheme: ThemeData.dark().textTheme.apply(
              fontFamily: 'Inter', bodyColor: kText, displayColor: kText),
      ),
      home: const HomeShell(),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      const DownloadTab(),
      const LibraryTab(),
      const CdTab(),
      const SettingsTab(),
    ];
    return Scaffold(
      body: pages[_tab],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        backgroundColor: kSurface,
        indicatorColor: kAccent,
        destinations: const [
          NavigationDestination(icon: Icon(Icons.download), label: 'Pobieranie'),
          NavigationDestination(icon: Icon(Icons.library_music), label: 'Biblioteka'),
          NavigationDestination(icon: Icon(Icons.album), label: 'Płyta CD'),
          NavigationDestination(icon: Icon(Icons.settings), label: 'Ustawienia'),
        ],
      ),
    );
  }
}

class DownloadTab extends StatelessWidget {
  const DownloadTab({super.key});
  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(children: [
          TextField(
            decoration: InputDecoration(
              hintText: 'Wklej link do filmu YouTube…',
              filled: true, fillColor: kSurface,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: 160, height: 52,
            child: FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: kAccent,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14))),
              onPressed: () {/* potwierdzenie prawne → kolejka */},
              child: const Text('POBIERZ',
                  style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ]),
      ),
    );
  }
}

class LibraryTab extends StatelessWidget {
  const LibraryTab({super.key});
  @override
  Widget build(BuildContext context) {
    // Siatka 2×N (mobile): GridView.count(crossAxisCount: 2, ...)
    return const SafeArea(
      child: Center(child: Text('Biblioteka — siatka 2×N okładek',
          style: TextStyle(color: kTextDim))));
  }
}

/// Ekran CD na mobile: ten sam łuk + „EKSPORTUJ NA KOMPUTER".
class CdTab extends StatelessWidget {
  const CdTab({super.key});
  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(children: [
          const SizedBox(height: 24),
          const CustomPaint(
            size: Size(220, 220),
            painter: CdPainter(fraction: 0.42, isAudioCd: true),
          ),
          const SizedBox(height: 16),
          const Text('33:36 / 80:00', style: TextStyle(color: kTextDim)),
          const Spacer(),
          SizedBox(
            width: double.infinity, height: 52,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: kAccent,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16))),
              icon: const Icon(Icons.share),
              label: const Text('EKSPORTUJ NA KOMPUTER',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              onPressed: () {/* serwer Wi‑Fi + QR / share sheet / USB */},
            ),
          ),
        ]),
      ),
    );
  }
}

class CdPainter extends CustomPainter {
  final double fraction; // 0..1
  final bool isAudioCd;
  const CdPainter({required this.fraction, this.isAudioCd = true});

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = size.shortestSide / 2;
    canvas.drawCircle(center, radius, Paint()..color = kSurface);
    canvas.drawCircle(center, radius * 0.22, Paint()..color = kBg);
    final arc = Paint()
      ..color = isAudioCd ? kAccent : kMint
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(Rect.fromCircle(center: center, radius: radius - 14),
        -math.pi / 2, 2 * math.pi * fraction, false, arc);
  }

  @override
  bool shouldRepaint(CdPainter old) =>
      old.fraction != fraction || old.isAudioCd != isAudioCd;
}

class SettingsTab extends StatelessWidget {
  const SettingsTab({super.key});
  @override
  Widget build(BuildContext context) {
    return const SafeArea(
      child: Center(child: Text('Ustawienia', style: TextStyle(color: kTextDim))));
  }
}
