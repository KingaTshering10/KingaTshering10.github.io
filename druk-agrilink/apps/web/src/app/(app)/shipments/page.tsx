"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Empty, Loading, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import type { Shipment } from "@/lib/types";

export default function ShipmentsPage() {
  const { t } = useI18n();
  const { data, isLoading } = useQuery({
    queryKey: ["shipments"],
    queryFn: () => api<Shipment[]>("/shipments"),
  });

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.shipments}</h1>
      {isLoading ? <Loading label={t.common.loading} /> : null}
      {data && data.length === 0 ? <Empty label={t.common.empty} /> : null}
      <ul className="grid gap-3">
        {data?.map((shipment) => (
          <li key={shipment.id}>
            <Link
              href={`/shipments/${shipment.id}`}
              className="block rounded-xl border border-earth-100 bg-white p-4 shadow-sm hover:border-field-500"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold">
                  {shipment.vehicle?.registration_number ?? "—"} ·{" "}
                  {shipment.planned_distance_km
                    ? `${shipment.planned_distance_km} km (${t.common.approximate})`
                    : ""}
                </span>
                <StatusBadge status={shipment.status} />
              </div>
              <p className="mt-1 text-sm text-earth-700">
                {shipment.stops.filter((stop) => stop.stop_type === "pickup").length} pickups ·{" "}
                {shipment.planned_pickup_at
                  ? new Date(shipment.planned_pickup_at).toLocaleDateString()
                  : "—"}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
