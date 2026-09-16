"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Button, Card, ErrorState, Field, inputClass, Loading, StatusBadge } from "@/components/ui";
import { formatQuantity, useI18n } from "@/i18n";
import { api, ApiRequestError } from "@/lib/api";
import type { Listing } from "../page";

interface Revision {
  id: string;
  field: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

interface ConflictInfo {
  serverState: Record<string, unknown>;
  localValue: string;
}

export default function HarvestDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [confirmQty, setConfirmQty] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictInfo | null>(null);

  const { data: listing, isLoading } = useQuery({
    queryKey: ["harvest", params.id],
    queryFn: () => api<Listing>(`/harvest-listings/${params.id}`),
  });
  const { data: revisions } = useQuery({
    queryKey: ["harvest-revisions", params.id],
    queryFn: () => api<Revision[]>(`/harvest-listings/${params.id}/revisions`),
  });

  const confirmMutation = useMutation({
    mutationFn: (body: { confirmed_quantity: string; expected_row_version?: number }) =>
      api(`/harvest-listings/${params.id}/confirm`, { method: "POST", body }),
    onSuccess: () => {
      setError(null);
      setConflict(null);
      void queryClient.invalidateQueries({ queryKey: ["harvest", params.id] });
      void queryClient.invalidateQueries({ queryKey: ["harvest-revisions", params.id] });
    },
    onError: (err) => {
      if (err instanceof ApiRequestError && err.error.code === "CONFLICT_STALE_VERSION") {
        setConflict({
          serverState: (err.error.server_state as Record<string, unknown>) ?? {},
          localValue: confirmQty,
        });
      } else {
        setError(err instanceof ApiRequestError ? err.message : t.common.error);
      }
    },
  });

  const publishMutation = useMutation({
    mutationFn: () => api(`/harvest-listings/${params.id}/publish`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["harvest", params.id] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  if (isLoading || !listing) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {formatQuantity(listing.forecast_quantity, listing.unit)}
        </h1>
        <StatusBadge status={listing.status} />
      </div>
      {error ? (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      ) : null}

      {conflict ? (
        <Card title={t.harvest.conflictTitle} className="mb-6 border-maize-500">
          <p className="mb-3 text-sm text-earth-700">{t.harvest.conflictBody}</p>
          <div className="mb-3 grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-earth-100 p-3">
              <h3 className="mb-1 text-sm font-semibold">{t.harvest.yourVersion}</h3>
              <p className="text-sm">
                {t.harvest.confirmedQuantity}: {conflict.localValue} {listing.unit}
              </p>
            </div>
            <div className="rounded-lg border border-earth-100 p-3">
              <h3 className="mb-1 text-sm font-semibold">{t.harvest.serverVersion}</h3>
              {Object.entries(conflict.serverState).map(([key, value]) => (
                <p key={key} className="text-sm">
                  {key}: {String(value ?? "—")}
                </p>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => confirmMutation.mutate({ confirmed_quantity: conflict.localValue })}
            >
              {t.harvest.keepMine}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setConflict(null);
                void queryClient.invalidateQueries({ queryKey: ["harvest", params.id] });
              }}
            >
              {t.harvest.keepServer}
            </Button>
          </div>
        </Card>
      ) : null}

      <Card className="mb-6">
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-earth-700">{t.harvest.window}</dt>
            <dd className="font-medium">
              {listing.harvest_start_date} → {listing.harvest_end_date}
            </dd>
          </div>
          <div>
            <dt className="text-earth-700">{t.harvest.minPrice}</dt>
            <dd className="font-medium">
              Nu. {listing.minimum_unit_price}/{listing.unit}
            </dd>
          </div>
          <div>
            <dt className="text-earth-700">{t.harvest.confirmedQuantity}</dt>
            <dd className="font-medium">
              {listing.confirmed_quantity
                ? formatQuantity(listing.confirmed_quantity, listing.unit)
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-earth-700">{t.harvest.availableQuantity}</dt>
            <dd className="font-medium">
              {formatQuantity(listing.available_quantity, listing.unit)}
            </dd>
          </div>
        </dl>
      </Card>

      {listing.status === "draft" ? (
        <Card className="mb-6">
          <Button onClick={() => publishMutation.mutate()} disabled={publishMutation.isPending}>
            {t.harvest.publish}
          </Button>
        </Card>
      ) : null}

      {listing.status === "forecast" ? (
        <Card title={t.harvest.confirmQuantity} className="mb-6">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              confirmMutation.mutate({
                confirmed_quantity: confirmQty,
                expected_row_version: listing.row_version,
              });
            }}
          >
            <Field label={t.harvest.confirmedQuantity} htmlFor="confirm_qty">
              <input
                id="confirm_qty"
                type="number"
                step="0.01"
                min="0"
                required
                inputMode="decimal"
                className={inputClass}
                value={confirmQty}
                onChange={(event) => setConfirmQty(event.target.value)}
              />
            </Field>
            <Button type="submit" disabled={confirmMutation.isPending}>
              {t.common.confirm}
            </Button>
          </form>
        </Card>
      ) : null}

      <Card title={t.harvest.revisionHistory}>
        {revisions && revisions.length > 0 ? (
          <ul className="divide-y divide-earth-100 text-sm">
            {revisions.map((revision) => (
              <li key={revision.id} className="py-2">
                <span className="font-medium">{revision.field}</span>: {revision.old_value ?? "—"} →{" "}
                {revision.new_value ?? "—"}
                <span className="ml-2 text-xs text-earth-700">
                  {new Date(revision.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-earth-700">{t.common.empty}</p>
        )}
      </Card>
    </div>
  );
}
