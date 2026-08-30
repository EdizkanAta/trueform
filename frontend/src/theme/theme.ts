/**
 * TrueForm design tokens — single source of truth.
 *
 * Framework-agnostic plain object so it can feed EITHER a NativeWind
 * `tailwind.config.js` (theme.extend.colors) OR the StyleSheet `ThemeProvider`.
 * Screens must consume these tokens only — never hardcode hex values.
 *
 * Dark is the mandatory launch default. `light` is derived from the same
 * palette and is a secondary opt-in (Settings), wired in a later step.
 */

// ---- Color palette ---------------------------------------------------------
export const palette = {
  // surfaces
  bg: "#0E0F12", // near-black app background (not pure black)
  surface: "#17181C", // cards / sheets
  hairline: "#26272C", // 1px borders / dividers

  // text
  textPrimary: "#F2F3F5",
  textSecondary: "#9BA0A8",

  // single restrained accent gradient — DATA + charts only, one CTA max/screen
  accentGradient: ["#2DD4BF", "#3B82F6", "#8B5CF6"] as const, // teal → blue → violet
  accentFrom: "#2DD4BF",
  accentMid: "#3B82F6",
  accentTo: "#8B5CF6",
  onAccent: "#0E0F12", // text/icon on top of an accent fill

  // semantic — used sparingly, never to shame
  success: "#34D399",
  warning: "#FBBF24",
  alert: "#F87171",
} as const;

// ---- Radius (spec: 16) -----------------------------------------------------
export const radius = {
  sm: 8,
  md: 16, // default card/control radius
  lg: 24,
  pill: 999,
} as const;

// ---- Spacing (8-pt grid) ---------------------------------------------------
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
} as const;

// ---- Typography (instrument-readout: thin numerals, uppercase labels) ------
export const typography = {
  numeral: "200", // large stat numbers
  numeralMedium: "300",
  label: "600", // small uppercase letter-spaced labels
  body: "400",
  letterSpacingLabel: 1.5,
  size: {
    xs: 11,
    sm: 12,
    base: 14,
    md: 16,
    lg: 20,
    xl: 24,
    "2xl": 32,
    "3xl": 44,
    "4xl": 60,
  },
} as const;

// ---- Composed theme objects (dark default, light derived) ------------------
export const darkTheme = {
  name: "dark" as const,
  colors: palette,
  radius,
  spacing,
  typography,
};

export const lightTheme = {
  name: "light" as const,
  colors: {
    ...palette,
    bg: "#F9FAFB",
    surface: "#FFFFFF",
    hairline: "#E5E7EB",
    textPrimary: "#111827",
    textSecondary: "#6B7280",
    onAccent: "#FFFFFF",
    // keep the same accent gradient + semantic colors across modes
  },
  radius,
  spacing,
  typography,
};

export type AppTheme = typeof darkTheme;

// Default export = the mandatory launch theme (dark).
export default darkTheme;
