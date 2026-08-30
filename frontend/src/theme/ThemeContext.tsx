import React, { createContext, useContext } from "react";
import { useColorScheme } from "react-native";

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

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const scheme = useColorScheme() ?? "dark";
  const colors = scheme === "light" ? lightColors : darkColors;
  return (
    <ThemeContext.Provider value={{ colors, scheme, spacing, radius, font }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
