// Consumes the single source of truth (theme.ts) — NO color/spacing/radius
// values are declared here. This module only MAPS theme.ts into the color-key
// shape the existing components expect (e.g. `border` ← hairline,
// `accentTeal` ← accentFrom). Adding a literal here would violate the
// single-source rule.
import { darkTheme, lightTheme, palette, radius, spacing, typography } from "./theme";

type ThemeColors = typeof palette;

const mapColors = (c: ThemeColors) => ({
  bg: c.bg,
  surface: c.surface,
  surfaceElevated: c.surfaceElevated,
  border: c.hairline,
  borderStrong: c.hairlineStrong,
  textPrimary: c.textPrimary,
  textSecondary: c.textSecondary,
  textTertiary: c.textTertiary,
  accentTeal: c.accentFrom,
  accentBlue: c.accentMid,
  accentViolet: c.accentTo,
  onAccent: c.onAccent,
  success: c.success,
  warning: c.warning,
  alert: c.alert,
  scrim: c.scrim,
});

export const darkColors = mapColors(darkTheme.colors);
export const lightColors = mapColors(lightTheme.colors);

export type Palette = typeof darkColors;

export { spacing, radius };
export const font = typography;
export const ACCENT_GRADIENT = palette.accentGradient;
