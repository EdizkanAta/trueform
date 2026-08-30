import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

import { storage } from "@/src/utils/storage";
import { darkColors, lightColors, Palette, spacing, radius, font } from "./tokens";

type Scheme = "light" | "dark";

type Theme = {
  colors: Palette;
  scheme: Scheme;
  setScheme: (s: Scheme) => void;
  spacing: typeof spacing;
  radius: typeof radius;
  font: typeof font;
};

const THEME_KEY = "tf_theme";

const ThemeContext = createContext<Theme>({
  colors: darkColors, scheme: "dark", setScheme: () => {}, spacing, radius, font,
});

// Dark is the mandatory launch default. Light mode is a secondary opt-in
// surfaced in Settings and persisted on-device (AsyncStorage). First launch =
// dark (the stored fallback), independent of the OS color scheme.
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [scheme, setSchemeState] = useState<Scheme>("dark");

  useEffect(() => {
    (async () => {
      const saved = await storage.getItem<string>(THEME_KEY, "dark");
      if (saved === "light" || saved === "dark") setSchemeState(saved);
    })();
  }, []);

  const setScheme = useCallback((s: Scheme) => {
    setSchemeState(s);
    storage.setItem(THEME_KEY, s);
  }, []);

  const colors = scheme === "light" ? lightColors : darkColors;

  return (
    <ThemeContext.Provider value={{ colors, scheme, setScheme, spacing, radius, font }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
