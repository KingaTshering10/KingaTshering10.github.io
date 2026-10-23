"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, Empty, Loading } from "@/components/ui";
import { formatMoney, useI18n } from "@/i18n";
import { api, type Me } from "@/lib/api";

function Stat({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-xl border border-earth-100 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-earth-700">{label}</p>
      <p className="mt-1 text-xl font-bold text-field-800">{value ?? "—"}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { t } = useI18n();
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/users/me") });

  const role = me?.role;
  const analyticsPath =
    role === "farmer"
      ? "/analytics/farmer"
      : role === "buyer"
        ? "/analytics/buyer"
        : role === "transporter"
          ? "/analytics/transporter"
          : role
            ? "/analytics/platform"
            : null;

  const { data: analytics, isLoading } = useQuery({
    queryKey: ["analytics", analyticsPath],
    queryFn: () =>
      api<{ measured: Record<string, unknown>; estimated?: Record<string, unknown> }>(
        analyticsPath as string,
      ),
    enabled: analyticsPath !== null,
  });

  const { data: notifications } = useQuery({
    queryKey: ["recent-notifications"],
    queryFn: () =>
      api<{ items: { id: string; subject: string; created_at: string }[] }>(
        "/notifications?page_size=5",
      ),
  });

  if (!me || isLoading) return <Loading label={t.common.loading} />;

  const measured = analytics?.measured ?? {};
  const money = (key: string) => (measured[key] != null ? formatMoney(String(measured[key])) : "—");

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">{t.nav.dashboard}</h1>

      <div className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-4">
        {me.role === "farmer" ? (
          <>
            <Stat
              label={t.harvest.forecastQuantity}
              value={`${measured.listed_quantity ?? "0"} kg`}
            />
            <Stat
              label={t.harvest.confirmedQuantity}
              value={`${measured.confirmed_quantity ?? "0"} kg`}
            />
            <Stat label={t.dashboard.amountDue} value={money("amount_due")} />
            <Stat label={t.dashboard.amountPaid} value={money("amount_paid")} />
          </>
        ) : me.role === "buyer" ? (
          <>
            <Stat label={t.dashboard.activeOrders} value={String(measured.orders_created ?? 0)} />
            <Stat
              label="Fulfilment"
              value={
                measured.fulfilment_rate_percent ? `${measured.fulfilment_rate_percent}%` : "—"
              }
            />
            <Stat label={t.payment.outstanding} value={money("payment_obligations_outstanding")} />
            <Stat label="Completed" value={String(measured.completed_orders ?? 0)} />
          </>
        ) : me.role === "transporter" ? (
          <>
            <Stat label="Completed trips" value={String(measured.completed_trips ?? 0)} />
            <Stat label="Active trips" value={String(measured.active_trips ?? 0)} />
            <Stat label="Fleet capacity" value={`${measured.fleet_capacity_kg ?? 0} kg`} />
            <Stat label={t.payment.outstanding} value={money("pending_payment")} />
          </>
        ) : (
          <>
            <Stat label="Produce listed" value={`${measured.total_produce_listed_kg ?? 0} kg`} />
            <Stat label="Produce sold" value={`${measured.total_produce_sold_kg ?? 0} kg`} />
            <Stat label="Gross value" value={money("gross_transaction_value")} />
            <Stat label="Disputes" value={String(measured.dispute_count ?? 0)} />
          </>
        )}
      </div>

      {analytics?.estimated ? (
        <Card title={t.dashboard.estimated} className="mb-8">
          <p className="mb-2 text-xs text-earth-700">{t.dashboard.estimatedNote}</p>
          <dl className="grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-earth-700">Transport savings (estimated)</dt>
              <dd className="font-semibold">
                {formatMoney(String(analytics.estimated.transport_savings_nu ?? "0"))}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-earth-700">Produce-loss reduction (estimated)</dt>
              <dd className="font-semibold">
                {String(analytics.estimated.produce_loss_reduction_kg ?? "0")} kg
              </dd>
            </div>
          </dl>
        </Card>
      ) : null}

      <Card title={t.nav.notifications}>
        {notifications?.items.length ? (
          <ul className="divide-y divide-earth-100">
            {notifications.items.map((n) => (
              <li key={n.id} className="py-2 text-sm">
                <span className="font-medium">{n.subject}</span>
                <span className="ml-2 text-xs text-earth-700">
                  {new Date(n.created_at).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty label={t.common.empty} />
        )}
      </Card>
    </div>
  );
}
