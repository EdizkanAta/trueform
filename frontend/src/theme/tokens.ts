// TrueForm design tokens — clinical, dark-first "lab instrument" aesthetic.
// Single source of truth; components never hardcode colors.

export const darkColors = {
  bg: "#0E0F12",
  surface: "#17181C",
  surfaceElevated: "#1C1E23",
  border: "#26272C",
  borderStrong: "#3B4048",
  textPrimary: "#F2F3F5",
  textSecondary: "#9BA0A8",
  textTertiary: "#6B7078",
  // accent gradient (data)
  accentTeal: "#2DD4BF",
  accentBlue: "#3B82F6",
  accentViolet: "#8B5CF6",
  onAccent: "#0E0F12",
  success: "#34D399",
  warning: "#FBBF24",
  alert: "#F87171",
  scrim: "rgba(14,15,18,0.72)",
};

export const lightColors = {
  bg: "#F9FAFB",
  surface: "#FFFFFF",
  surfaceElevated: "#FFFFFF",
  border: "#E5E7EB",
  borderStrong: "#D1D5DB",
  textPrimary: "#111827",
  textSecondary: "#6B7280",
  textTertiary: "#9CA3AF",
  accentTeal: "#0D9488",
  accentBlue: "#2563EB",
  accentViolet: "#7C3AED",
  onAccent: "#FFFFFF",
  success: "#059669",
  warning: "#D97706",
  alert: "#DC2626",
  scrim: "rgba(17,24,39,0.55)",
};

export type Palette = typeof darkColors;

export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48, xxxl: 64 };
export const radius = { sm: 8, md: 16, lg: 24, pill: 999 };

export const font = {
  // System font (SF Pro / Roboto). Thin numerals for the instrument readout.
  numeral: "200" as const,
  numeralMedium: "300" as const,
  label: "600" as const,
  body: "400" as const,
  size: { xs: 11, sm: 12, base: 14, md: 16, lg: 20, xl: 24, "2xl": 32, "3xl": 44, "4xl": 60 },
  letterSpacingLabel: 1.5,
};

export const ACCENT_GRADIENT = [darkColors.accentTeal, darkColors.accentBlue, darkColors.accentViolet];
