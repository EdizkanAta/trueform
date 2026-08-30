import React, { createContext, useContext } from "react";

import { darkColors, lightColors, Palette, spacing, radius, font } from "./tokens";

type Theme = {
  colors: Palette;
  scheme: "light" | "dark";
  spacing: typeof spacing;
  radius: typeof radius;
  font: typeof font;
};

const ThemeContext = createContext<Theme>({
  colors: darkColors, scheme: "dark", spacing, radius, font,
});

// Dark is the mandatory launch default. Light mode is a secondary opt-in that
// will be surfaced in Settings (not driven by the OS setting at launch).
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const scheme: "dark" | "light" = "dark";
  const colors = scheme === "light" ? lightColors : darkColors;
  return (
    <ThemeContext.Provider value={{ colors, scheme, spacing, radius, font }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
