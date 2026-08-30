/**
 * TrueForm design tokens — the SINGLE source of truth.
 *
 * Every hex/rgba literal in the app lives here exactly once. Framework-agnostic
 * so it feeds the StyleSheet `ThemeProvider` (via tokens.ts) — no value is ever
 * copied elsewhere. Dark is the mandatory launch default; `light` is derived
 * from the same palette and is a secondary opt-in (Settings), wired later.
 */

// ---- Base color constants (each literal declared once) ---------------------
const nearBlack = "#0E0F12";
const surfaceDark = "#17181C";
const surfaceDarkElevated = "#1C1E23";
const hairlineDark = "#26272C";
const hairlineDarkStrong = "#3B4048";
const inkHigh = "#F2F3F5";
const inkMid = "#9BA0A8";
const inkLow = "#6B7078";

const teal = "#2DD4BF";
const blue = "#3B82F6";
const violet = "#8B5CF6";

const success = "#34D399";
const warning = "#FBBF24";
const alert = "#F87171";

const scrimDark = "rgba(14,15,18,0.72)";
const overlay = "rgba(0,0,0,0.45)";
const white = "#FFFFFF";

// light-mode neutrals (derived surfaces/text)
const bgLight = "#F9FAFB";
const surfaceLight = "#FFFFFF";
const hairlineLight = "#E5E7EB";
const hairlineLightStrong = "#D1D5DB";
const inkHighLight = "#111827";
const inkMidLight = "#6B7280";
const inkLowLight = "#9CA3AF";
const scrimLight = "rgba(17,24,39,0.55)";

// ---- Dark palette (default) ------------------------------------------------
export const palette = {
  // surfaces
  bg: nearBlack, // near-black app background (not pure black)
  surface: surfaceDark, // cards / sheets
  surfaceElevated: surfaceDarkElevated, // raised fills (skeletons, insets)
  hairline: hairlineDark, // 1px borders / dividers
  hairlineStrong: hairlineDarkStrong, // stronger control borders

  // text
  textPrimary: inkHigh,
  textSecondary: inkMid,
  textTertiary: inkLow,

  // single restrained accent gradient — DATA + charts only, one CTA max/screen
  accentFrom: teal,
  accentMid: blue,
  accentTo: violet,
  accentGradient: [teal, blue, violet] as const, // teal → blue → violet
  onAccent: nearBlack, // text/icon on an accent fill

  // semantic — used sparingly, never to shame
  success,
  warning,
  alert,

  // image treatments
  scrim: scrimDark, // gradient scrim on full-bleed photo cards
  overlay, // pill/label chips over imagery
  onImage: white, // text/icon over imagery
} as const;

// ---- Light palette (derived; secondary opt-in) -----------------------------
const lightColors = {
  ...palette,
  bg: bgLight,
  surface: surfaceLight,
  surfaceElevated: surfaceLight,
  hairline: hairlineLight,
  hairlineStrong: hairlineLightStrong,
  textPrimary: inkHighLight,
  textSecondary: inkMidLight,
  textTertiary: inkLowLight,
  onAccent: white,
  scrim: scrimLight,
} as const;

// ---- Radius (spec: 16 default) --------------------------------------------
export const radius = { sm: 8, md: 16, lg: 24, pill: 999 } as const;

// ---- Spacing (8-pt grid) ---------------------------------------------------
export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48, xxxl: 64 } as const;

// ---- Typography (instrument-readout: thin numerals, uppercase labels) ------
export const typography = {
  numeral: "200" as const,
  numeralMedium: "300" as const,
  label: "600" as const,
  body: "400" as const,
  letterSpacingLabel: 1.5,
  size: { xs: 11, sm: 12, base: 14, md: 16, lg: 20, xl: 24, "2xl": 32, "3xl": 44, "4xl": 60 },
} as const;

// ---- Composed themes (dark default, light derived) -------------------------
export const darkTheme = { name: "dark" as const, colors: palette, radius, spacing, typography };
export const lightTheme = { name: "light" as const, colors: lightColors, radius, spacing, typography };

export type AppTheme = typeof darkTheme;

// Default export = the mandatory launch theme (dark).
export default darkTheme;
