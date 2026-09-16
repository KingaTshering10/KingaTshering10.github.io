"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { en, type Dictionary } from "./en";
import { dzDictionary } from "./dz";

export type Locale = "en" | "dz";

const dictionaries: Record<Locale, Dictionary> = { en, dz: dzDictionary };

interface I18nContextValue {
  locale: Locale;
  t: Dictionary;
  setLocale: (locale: Locale) => void;
}

const I18nContext = createContext<I18nContextValue>({
  locale: "en",
  t: en,
  setLocale: () => undefined,
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const saved = window.localStorage.getItem("druk.locale");
    if (saved === "dz" || saved === "en") setLocaleState(saved);
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem("druk.locale", next);
    document.documentElement.lang = next;
  }, []);

  return (
    <I18nContext.Provider value={{ locale, t: dictionaries[locale], setLocale }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}

/** Locale-aware money formatting: Nu. 1,234.56 (BTN). */
export function formatMoney(value: string | number): string {
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return `Nu. ${value}`;
  return `Nu. ${num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatQuantity(value: string | number, unit: string): string {
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return `${value} ${unit}`;
  return `${num.toLocaleString("en-IN")} ${unit}`;
}
