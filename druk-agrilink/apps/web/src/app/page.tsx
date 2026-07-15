"use client";

import Link from "next/link";
import { useI18n } from "@/i18n";
import { LanguageSwitcher } from "@/components/language-switcher";

export default function LandingPage() {
  const { t } = useI18n();
  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/icon.svg" alt="" className="h-9 w-9" />
          <span className="text-lg font-bold text-field-800">{t.appName}</span>
        </div>
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          <Link
            href="/login"
            className="rounded-lg border border-field-600 px-4 py-2 text-sm font-semibold text-field-700 hover:bg-field-50"
          >
            {t.landing.signIn}
          </Link>
        </div>
      </header>

      <section className="mb-12 text-center">
        <h1 className="mb-4 text-3xl font-bold leading-tight text-field-800 sm:text-4xl">
          {t.landing.heroTitle}
        </h1>
        <p className="mx-auto mb-6 max-w-2xl text-earth-700">{t.landing.heroBody}</p>
        <Link
          href="/register"
          className="inline-block rounded-lg bg-field-600 px-6 py-3 font-semibold text-white hover:bg-field-700"
        >
          {t.landing.getStarted}
        </Link>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {[
          [t.landing.forFarmers, t.landing.forFarmersBody],
          [t.landing.forBuyers, t.landing.forBuyersBody],
          [t.landing.forTransporters, t.landing.forTransportersBody],
        ].map(([title, body]) => (
          <div key={title} className="rounded-xl border border-earth-100 bg-white p-5 shadow-sm">
            <h2 className="mb-2 font-semibold text-field-800">{title}</h2>
            <p className="text-sm text-earth-700">{body}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
