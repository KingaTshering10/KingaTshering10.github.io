"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button, Card, Empty, Loading, StatusBadge } from "@/components/ui";
import { formatMoney, useI18n } from "@/i18n";
import { api } from "@/lib/api";
import type { Shipment } from "@/lib/types";

export default function TripsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["shipments"],
    queryFn: () => api<Shipment[]>("/shipments"),
  });

  const act = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api(`/shipments/${id}/${action}`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shipments"] }),
  });

  if (isLoading) return <Loading label={t.common.loading} />;
  const offered = data?.filter((shipment) => shipment.status === "offered") ?? [];
  const mine = data?.filter((shipment) => shipment.status !== "offered") ?? [];

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.availableTrips}</h1>
      {offered.length === 0 ? <Empty label={t.common.empty} /> : null}
      {offered.map((shipment) => (
        <Card key={shipment.id} className="mb-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-semibold">
              {shipment.planned_distance_km
                ? `${shipment.planned_distance_km} km (${t.common.approximate})`
                : "Trip"}
              {shipment.estimated_transport_cost
                ? ` · ${formatMoney(shipment.estimated_transport_cost)}`
                : ""}
            </span>
            <StatusBadge status={shipment.status} />
          </div>
          <p className="mb-3 text-sm text-earth-700">
            {shipment.stops.filter((stop) => stop.stop_type === "pickup").length} pickup stops ·{" "}
            {shipment.planned_pickup_at
              ? new Date(shipment.planned_pickup_at).toLocaleString()
              : "—"}
          </p>
          <div className="flex gap-2">
            <Button onClick={() => act.mutate({ id: shipment.id, action: "accept" })}>
              {t.shipment.acceptTrip}
            </Button>
            <Button
              variant="secondary"
              onClick={() => act.mutate({ id: shipment.id, action: "decline" })}
            >
              {t.shipment.declineTrip}
            </Button>
          </div>
        </Card>
      ))}

      <h2 className="mb-4 mt-8 text-xl font-bold">{t.nav.assignedTrips}</h2>
      {mine.length === 0 ? <Empty label={t.common.empty} /> : null}
      <ul className="grid gap-3">
        {mine.map((shipment) => (
          <li key={shipment.id}>
            <Link
              href={`/shipments/${shipment.id}`}
              className="block rounded-xl border border-earth-100 bg-white p-4 shadow-sm hover:border-field-500"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold">
                  {shipment.vehicle?.registration_number ?? "—"}
                </span>
                <StatusBadge status={shipment.status} />
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
