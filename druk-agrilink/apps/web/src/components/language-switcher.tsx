"use client";

import { useI18n, type Locale } from "@/i18n";

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  return (
    <label className="flex items-center gap-1 text-sm">
      <span className="sr-only">Language / སྐད་ཡིག།</span>
      <select
        aria-label="Language"
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
        className="min-h-11 rounded-lg border border-earth-100 bg-white px-2 text-sm"
      >
        <option value="en">English</option>
        <option value="dz">རྫོང་ཁ (Dzongkha)</option>
      </select>
    </label>
  );
}
