"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Button, Empty, Loading, StatusBadge } from "@/components/ui";
import { formatQuantity, useI18n } from "@/i18n";
import { api } from "@/lib/api";

export interface Listing {
  id: string;
  product_id: string;
  forecast_quantity: string;
  confirmed_quantity: string | null;
  available_quantity: string;
  unit: string;
  harvest_start_date: string;
  harvest_end_date: string;
  minimum_unit_price: string;
  status: string;
  row_version: number;
}

export default function HarvestsPage() {
  const { t } = useI18n();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["harvests"],
    queryFn: () => api<Listing[]>("/harvest-listings"),
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t.nav.myHarvests}</h1>
        <Link href="/harvests/new">
          <Button>{t.harvest.newListing}</Button>
        </Link>
      </div>
      {isLoading ? <Loading label={t.common.loading} /> : null}
      {isError ? <Empty label={t.common.error} /> : null}
      {data && data.length === 0 ? <Empty label={t.common.empty} /> : null}
      {data && data.length > 0 ? (
        <ul className="grid gap-3">
          {data.map((listing) => (
            <li key={listing.id}>
              <Link
                href={`/harvests/${listing.id}`}
                className="block rounded-xl border border-earth-100 bg-white p-4 shadow-sm hover:border-field-500"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold">
                    {formatQuantity(listing.forecast_quantity, listing.unit)}
                  </span>
                  <StatusBadge status={listing.status} />
                </div>
                <p className="mt-1 text-sm text-earth-700">
                  {listing.harvest_start_date} → {listing.harvest_end_date} · min Nu.{" "}
                  {listing.minimum_unit_price}/{listing.unit}
                </p>
                {listing.confirmed_quantity ? (
                  <p className="mt-1 text-sm text-earth-700">
                    {t.harvest.confirmedQuantity}:{" "}
                    {formatQuantity(listing.confirmed_quantity, listing.unit)} ·{" "}
                    {t.harvest.availableQuantity}:{" "}
                    {formatQuantity(listing.available_quantity, listing.unit)}
                  </p>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
