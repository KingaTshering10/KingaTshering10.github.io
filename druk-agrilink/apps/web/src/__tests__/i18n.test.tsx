import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { en } from "@/i18n/en";
import { dzDictionary } from "@/i18n/dz";
import { formatMoney, formatQuantity, I18nProvider, useI18n } from "@/i18n";

describe("i18n dictionaries", () => {
  it("dz falls back to English for unverified keys instead of inventing text", () => {
    expect(dzDictionary.landing.heroTitle).toBe(en.landing.heroTitle);
    expect(dzDictionary.common.save).toBe(en.common.save);
  });

  it("dz keeps verified translations", () => {
    expect(dzDictionary.appName).not.toBe(en.appName);
    expect(dzDictionary.auth.language).toBe("སྐད་ཡིག།");
  });

  it("no placeholder markers leak into rendered strings", () => {
    const collect = (obj: object): string[] =>
      Object.values(obj).flatMap((value) =>
        typeof value === "string" ? [value] : collect(value as object),
      );
    for (const value of collect(dzDictionary)) {
      expect(value).not.toContain("[DZ REVIEW]");
    }
  });
});

describe("financial display", () => {
  it("formats ngultrum with the Nu. prefix and two decimals", () => {
    expect(formatMoney("7789")).toBe("Nu. 7,789.00");
    expect(formatMoney("10500.5")).toBe("Nu. 10,500.50");
  });

  it("formats quantities with units", () => {
    expect(formatQuantity("230.00", "kg")).toBe("230 kg");
  });
});

function Probe() {
  const { t, locale, setLocale } = useI18n();
  return (
    <div>
      <span data-testid="locale">{locale}</span>
      <span data-testid="appname">{t.appName}</span>
      <button onClick={() => setLocale("dz")}>switch</button>
    </div>
  );
}

describe("language switching", () => {
  it("switches dictionaries at runtime", () => {
    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    );
    expect(screen.getByTestId("appname").textContent).toBe(en.appName);
    fireEvent.click(screen.getByText("switch"));
    expect(screen.getByTestId("locale").textContent).toBe("dz");
    expect(screen.getByTestId("appname").textContent).toBe(dzDictionary.appName);
  });
});
