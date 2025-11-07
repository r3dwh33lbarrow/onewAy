import { useEffect, useMemo, useState } from "react";

import { ThemeContext } from "./themeContext";

const preferDarkQuery = "(prefers-color-scheme: dark)";

function getInitialPreference() {
  const savedPreference =
    localStorage.getItem("themePreference") || localStorage.getItem("theme");

  if (savedPreference === "dark") {
    return { initialDark: true, initialSystem: false };
  }

  if (savedPreference === "light") {
    return { initialDark: false, initialSystem: false };
  }

  const prefersDark = window.matchMedia(preferDarkQuery).matches;
  return { initialDark: prefersDark, initialSystem: true };
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { initialDark, initialSystem } = useMemo(
    () => getInitialPreference(),
    [],
  );
  const [useSystemTheme, setUseSystemTheme] = useState<boolean>(initialSystem);
  const [isDarkState, setIsDarkState] = useState<boolean>(initialDark);

  useEffect(() => {
    const mediaQuery = window.matchMedia(preferDarkQuery);

    const handleChange = (event: MediaQueryListEvent) => {
      if (useSystemTheme) {
        setIsDarkState(event.matches);
      }
    };

    if (useSystemTheme) {
      setIsDarkState(mediaQuery.matches);
    }

    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    } else {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, [useSystemTheme]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDarkState);
  }, [isDarkState]);

  useEffect(() => {
    if (useSystemTheme) {
      localStorage.setItem("themePreference", "system");
    } else {
      localStorage.setItem("themePreference", isDarkState ? "dark" : "light");
    }
  }, [useSystemTheme, isDarkState]);

  const setIsDark = (value: boolean) => {
    setUseSystemTheme(false);
    setIsDarkState(value);
  };

  return (
    <ThemeContext.Provider
      value={{
        isDark: isDarkState,
        setIsDark,
        useSystemTheme,
        setUseSystemTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}
