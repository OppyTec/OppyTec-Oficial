import { useCallback, useEffect, useState } from "react";
import {
  OFFICIAL_THEMES,
  type OppyTecTheme,
} from "@/shared/components/ui/designTokens";
import { trackUmamiEvent } from "@/shared/telemetry/umami";

export const THEME_STORAGE_KEY = "oppytec_theme";

export function applyDocumentTheme(theme: OppyTecTheme): void {
  if (typeof document === "undefined") {
    return;
  }
  const root = document.documentElement;
  root.classList.remove(...OFFICIAL_THEMES);
  root.classList.add(theme);
  root.setAttribute("data-theme", theme);
}

export function useTheme(initialTheme: OppyTecTheme = "ocean-blue") {
  const [theme, setThemeState] = useState<OppyTecTheme>(() => {
    if (
      typeof window !== "undefined" &&
      typeof window.localStorage?.getItem === "function"
    ) {
      const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === "light" || saved === "dark" || saved === "ocean-blue") {
        return saved;
      }
    }
    return initialTheme;
  });

  useEffect(() => {
    applyDocumentTheme(theme);
    if (typeof window !== "undefined") {
      if (typeof window.localStorage?.setItem === "function") {
        window.localStorage.setItem(THEME_STORAGE_KEY, theme);
      }
      trackUmamiEvent("theme_changed", window.location.pathname, { theme });
    }
  }, [theme]);

  const setTheme = useCallback((next: OppyTecTheme): void => {
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback((): void => {
    setThemeState((prev) => {
      if (prev === "light") return "dark";
      if (prev === "dark") return "ocean-blue";
      return "light";
    });
  }, []);

  return {
    theme,
    setTheme,
    toggleTheme,
    themes: OFFICIAL_THEMES,
  };
}
