import 'package:flutter/material.dart';

const sage = Color(0xFF668D7F);
const deepSage = Color(0xFF315C50);
const cream = Color(0xFFF7F7F2);
const graphite = Color(0xFF26332F);
// #68776F fica em 4,38:1 no creme. #5E6C64 passa de 4,5:1.
const inkMuted = Color(0xFF5E6C64);
const cardWhite = Color(0xFFFFFFFF);
const line = Color(0xFFE6EBE6);
const mist = Color(0xFFE6EFEA);
const errorInk = Color(0xFF8C3A32);
const errorMist = Color(0xFFF6E8E6);
const disabledFill = Color(0xFFD7E0DB);

abstract final class DiarySpace {
  static const double s4 = 4;
  static const double s8 = 8;
  static const double s12 = 12;
  static const double s16 = 16;
  static const double s24 = 24;
  static const double s32 = 32;
}

abstract final class DiaryRadius {
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 20;
  static const double xl = 24;
}

abstract final class DiaryElevation {
  static const double card = 1;
  static const Color shadow = Color(0x14000000);
}

ThemeData diaryTheme() {
  final scheme = ColorScheme(
    brightness: Brightness.light,
    primary: sage,
    onPrimary: cardWhite,
    primaryContainer: mist,
    onPrimaryContainer: deepSage,
    secondary: deepSage,
    onSecondary: cardWhite,
    secondaryContainer: mist,
    onSecondaryContainer: deepSage,
    error: errorInk,
    onError: cardWhite,
    errorContainer: errorMist,
    onErrorContainer: errorInk,
    surface: cardWhite,
    onSurface: graphite,
    onSurfaceVariant: inkMuted,
    outline: line,
    outlineVariant: line,
    shadow: DiaryElevation.shadow,
  );
  final radiusMd = BorderRadius.circular(DiaryRadius.md);
  final radiusLg = BorderRadius.circular(DiaryRadius.lg);
  final field = OutlineInputBorder(
    borderRadius: radiusMd,
    borderSide: const BorderSide(color: line),
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: cream,
    visualDensity: VisualDensity.standard,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    splashFactory: InkRipple.splashFactory,
    focusColor: deepSage.withValues(alpha: 0.16),
    hoverColor: deepSage.withValues(alpha: 0.06),
    appBarTheme: const AppBarTheme(
      backgroundColor: cream,
      foregroundColor: graphite,
      surfaceTintColor: cream,
      elevation: 0,
    ),
    textTheme: const TextTheme(
      headlineMedium: TextStyle(
        fontSize: 32,
        height: 1.25,
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
      bodySmall: TextStyle(fontSize: 13, height: 1.4, color: inkMuted),
      labelLarge: TextStyle(fontSize: 16, height: 1.25, fontWeight: FontWeight.w600, color: graphite),
    ),
    cardTheme: const CardThemeData(
      color: cardWhite,
      elevation: DiaryElevation.card,
      shadowColor: DiaryElevation.shadow,
      surfaceTintColor: cardWhite,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(DiaryRadius.xl)),
        side: BorderSide(color: line),
      ),
    ),
    dividerTheme: const DividerThemeData(color: line, thickness: 1, space: 1),
    progressIndicatorTheme: const ProgressIndicatorThemeData(color: deepSage),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: cardWhite,
      indicatorColor: mist,
      indicatorShape: RoundedRectangleBorder(borderRadius: radiusLg),
      height: 72,
      iconTheme: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return IconThemeData(color: selected ? deepSage : graphite);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return TextStyle(
          fontSize: 12,
          height: 1.2,
          fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
          color: selected ? deepSage : graphite,
        );
      }),
    ),
    navigationRailTheme: NavigationRailThemeData(
      backgroundColor: cardWhite,
      indicatorColor: mist,
      indicatorShape: RoundedRectangleBorder(borderRadius: radiusLg),
      selectedIconTheme: const IconThemeData(color: deepSage),
      unselectedIconTheme: const IconThemeData(color: graphite),
      selectedLabelTextStyle: const TextStyle(color: deepSage, fontWeight: FontWeight.w600, fontSize: 14),
      unselectedLabelTextStyle: const TextStyle(color: graphite, fontSize: 14),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: cardWhite,
      selectedColor: mist,
      side: const BorderSide(color: line),
      labelStyle: const TextStyle(color: graphite, fontSize: 14, height: 1.3),
      padding: const EdgeInsets.symmetric(horizontal: DiarySpace.s8, vertical: DiarySpace.s8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
    ),
    snackBarTheme: const SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: graphite,
      contentTextStyle: TextStyle(color: cardWhite, fontSize: 14, height: 1.4),
    ),
    filledButtonTheme: FilledButtonThemeData(style: diaryFilledStyle()),
    outlinedButtonTheme: OutlinedButtonThemeData(style: diaryOutlinedStyle()),
    textButtonTheme: TextButtonThemeData(style: diaryTextStyle()),
    iconButtonTheme: IconButtonThemeData(style: diaryIconStyle()),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: cardWhite,
      hintStyle: const TextStyle(color: inkMuted),
      border: field,
      enabledBorder: field,
      disabledBorder: field,
      focusedBorder: OutlineInputBorder(
        borderRadius: radiusMd,
        borderSide: const BorderSide(color: deepSage, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: radiusMd,
        borderSide: const BorderSide(color: errorInk),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: radiusMd,
        borderSide: const BorderSide(color: errorInk, width: 2),
      ),
    ),
  );
}

ButtonStyle diaryFilledStyle() {
  return FilledButton.styleFrom(
    minimumSize: const Size.fromHeight(48),
    backgroundColor: deepSage,
    foregroundColor: cardWhite,
    disabledBackgroundColor: disabledFill,
    disabledForegroundColor: inkMuted,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(DiaryRadius.sm)),
    ),
  ).copyWith(
    overlayColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.pressed)) return const Color(0x24FFFFFF);
      if (states.contains(WidgetState.hovered) || states.contains(WidgetState.focused)) {
        return const Color(0x14FFFFFF);
      }
      return null;
    }),
    side: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.focused)) {
        return const BorderSide(color: cardWhite, width: 2);
      }
      return BorderSide.none;
    }),
  );
}

ButtonStyle diaryOutlinedStyle() {
  return OutlinedButton.styleFrom(
    minimumSize: const Size.fromHeight(48),
    foregroundColor: deepSage,
    disabledForegroundColor: inkMuted,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(DiaryRadius.sm)),
    ),
  ).copyWith(
    side: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.disabled)) return const BorderSide(color: disabledFill);
      final strong = states.contains(WidgetState.focused) || states.contains(WidgetState.pressed);
      return BorderSide(color: deepSage, width: strong ? 2 : 1);
    }),
    overlayColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.pressed)) return deepSage.withValues(alpha: 0.12);
      if (states.contains(WidgetState.hovered) || states.contains(WidgetState.focused)) {
        return deepSage.withValues(alpha: 0.08);
      }
      return null;
    }),
  );
}

ButtonStyle diaryTextStyle() {
  return TextButton.styleFrom(
    foregroundColor: deepSage,
    minimumSize: const Size(48, 48),
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(DiaryRadius.sm)),
    ),
  ).copyWith(
    side: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.focused)) return const BorderSide(color: deepSage, width: 2);
      return BorderSide.none;
    }),
    overlayColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.pressed)) return deepSage.withValues(alpha: 0.12);
      if (states.contains(WidgetState.hovered) || states.contains(WidgetState.focused)) {
        return deepSage.withValues(alpha: 0.08);
      }
      return null;
    }),
  );
}

ButtonStyle diaryIconStyle() {
  return IconButton.styleFrom(
    foregroundColor: graphite,
    minimumSize: const Size(48, 48),
    highlightColor: deepSage.withValues(alpha: 0.08),
    hoverColor: deepSage.withValues(alpha: 0.06),
  ).copyWith(
    side: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.focused)) return const BorderSide(color: deepSage, width: 2);
      return BorderSide.none;
    }),
  );
}
