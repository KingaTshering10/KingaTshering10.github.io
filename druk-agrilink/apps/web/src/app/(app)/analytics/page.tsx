"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, Loading } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

export default function AnalyticsPage() {
  const { t } = useI18n();
  const { data, isLoading } = useQuery({
    queryKey: ["platform-analytics"],
    queryFn: () =>
      api<{ measured: Record<string, unknown>; estimated: Record<string, unknown> }>(
        "/analytics/platform",
      ),
  });

  if (isLoading || !data) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.analytics}</h1>
      <Card title={t.dashboard.measured} className="mb-6">
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          {Object.entries(data.measured).map(([key, value]) => (
            <div key={key} className="rounded-lg border border-earth-100 p-2">
              <dt className="text-xs text-earth-700">{key.replaceAll("_", " ")}</dt>
              <dd className="font-semibold">
                {typeof value === "object" ? JSON.stringify(value) : String(value ?? "—")}
              </dd>
            </div>
          ))}
        </dl>
      </Card>
      <Card title={t.dashboard.estimated}>
        <p className="mb-3 rounded-lg bg-maize-100 p-2 text-xs">{t.dashboard.estimatedNote}</p>
        <dl className="grid gap-2 text-sm">
          {Object.entries(data.estimated).map(([key, value]) => (
            <div key={key} className="rounded-lg border border-earth-100 p-2">
              <dt className="text-xs text-earth-700">{key.replaceAll("_", " ")}</dt>
              <dd className={key.endsWith("_method") ? "text-xs" : "font-semibold"}>
                {String(value)}
              </dd>
            </div>
          ))}
        </dl>
      </Card>
    </div>
  );
}
