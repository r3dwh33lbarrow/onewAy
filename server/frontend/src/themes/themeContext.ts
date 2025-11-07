import { createContext, useContext } from "react";

export interface ThemeContextValue {
  isDark: boolean;
  setIsDark: (value: boolean) => void;
  useSystemTheme: boolean;
  setUseSystemTheme: (value: boolean) => void;
}

export const ThemeContext = createContext<ThemeContextValue>({
  isDark: false,
  setIsDark: () => {},
  useSystemTheme: true,
  setUseSystemTheme: () => {},
});

export const useTheme = (): ThemeContextValue => useContext(ThemeContext);
