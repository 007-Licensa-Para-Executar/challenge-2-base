import 'package:flutter/material.dart';

const sage = Color(0xFF668D7F);
const cream = Color(0xFFF7F7F2);
const graphite = Color(0xFF26332F);
const cardWhite = Color(0xFFFFFFFF);
const mist = Color(0xFFE6EFEA);

ThemeData diaryTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: sage,
    brightness: Brightness.light,
  ).copyWith(
    primary: sage,
    onPrimary: cardWhite,
    surface: cardWhite,
    onSurface: graphite,
    error: const Color(0xFF8C3A32),
    onError: cardWhite,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: cream,
    appBarTheme: const AppBarTheme(
      backgroundColor: cream,
      foregroundColor: graphite,
      surfaceTintColor: cream,
      elevation: 0,
    ),
    textTheme: const TextTheme(
      headlineMedium: TextStyle(
        fontSize: 32,
        height: 1.2,
        fontWeight: FontWeight.w600,
        color: graphite,
      ),
      titleLarge: TextStyle(
        fontSize: 22,
        height: 1.3,
        fontWeight: FontWeight.w600,
        color: graphite,
      ),
      titleMedium: TextStyle(
        fontSize: 18,
        height: 1.35,
        fontWeight: FontWeight.w600,
        color: graphite,
      ),
      bodyLarge: TextStyle(fontSize: 16, height: 1.5, color: graphite),
      bodyMedium: TextStyle(fontSize: 14, height: 1.45, color: graphite),
      labelLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
    ),
    cardTheme: const CardThemeData(
      color: cardWhite,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(20)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(48, 48),
        backgroundColor: sage,
        foregroundColor: cardWhite,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(14)),
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: cardWhite,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFFD5DED9)),
      ),
    ),
  );
}
