import 'package:flutter/material.dart';

const sage = Color(0xFF668D7F);
const deepSage = Color(0xFF315C50);
const cream = Color(0xFFF7F7F2);
const graphite = Color(0xFF26332F);
const inkMuted = Color(0xFF68776F);
const cardWhite = Color(0xFFFFFFFF);
const line = Color(0xFFE6EBE6);
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
      bodyMedium: TextStyle(fontSize: 14, height: 1.45, color: inkMuted),
      labelLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
    ),
    materialTapTargetSize: MaterialTapTargetSize.padded,
    splashFactory: InkRipple.splashFactory,
    focusColor: sage.withValues(alpha: 0.22),
    hoverColor: sage.withValues(alpha: 0.06),
    cardTheme: const CardThemeData(
      color: cardWhite,
      elevation: 0.4,
      shadowColor: Color(0x14000000),
      surfaceTintColor: cardWhite,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(22)),
        side: BorderSide(color: line),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: cardWhite,
      indicatorColor: mist,
      height: 72,
      iconTheme: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return IconThemeData(color: selected ? deepSage : graphite);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return TextStyle(
          fontSize: 12,
          fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
          color: selected ? deepSage : graphite,
        );
      }),
    ),
    navigationRailTheme: const NavigationRailThemeData(
      backgroundColor: cardWhite,
      indicatorColor: mist,
      selectedIconTheme: IconThemeData(color: deepSage),
      unselectedIconTheme: IconThemeData(color: graphite),
      selectedLabelTextStyle: TextStyle(color: deepSage, fontWeight: FontWeight.w600, fontSize: 14),
      unselectedLabelTextStyle: TextStyle(color: graphite, fontSize: 14),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: cardWhite,
      selectedColor: mist,
      side: const BorderSide(color: Color(0xFFD5DED9)),
      labelStyle: const TextStyle(color: graphite, fontSize: 14),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
    ),
    snackBarTheme: const SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: graphite,
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        foregroundColor: sage,
        side: const BorderSide(color: sage),
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(14)),
        ),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
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
        borderRadius: BorderRadius.circular(20),
        borderSide: const BorderSide(color: line),
      ),
    ),
  );
}
