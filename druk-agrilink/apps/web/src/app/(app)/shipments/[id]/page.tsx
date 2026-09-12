"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Button, Card, ErrorState, Field, inputClass, Loading, StatusBadge } from "@/components/ui";
import { formatMoney, useI18n } from "@/i18n";
import { api, ApiRequestError, type Me } from "@/lib/api";
import type { Shipment, Stop } from "@/lib/types";

function CollectionForm({ stop, onDone }: { stop: Stop; onDone: () => void }) {
  const { t } = useI18n();
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({
    presented: stop.planned_quantity ?? "",
    accepted: stop.planned_quantity ?? "",
    rejected: "0",
    unitPrice: "",
    transportDeduction: "0",
    otherDeduction: "0",
    rejectionReason: "",
    listingId: "",
  });

  const { data: proposals } = useQuery({
    queryKey: ["proposals"],
    queryFn: () =>
      api<{ allocations: { harvest_listing_id: string }[] }[]>("/match-proposals?status=approved"),
  });
  const listingOptions =
    proposals?.flatMap((p) => p.allocations.map((a) => a.harvest_listing_id)) ?? [];

  const record = useMutation({
    mutationFn: () =>
      api("/collections", {
        method: "POST",
        body: {
          shipment_stop_id: stop.id,
          harvest_listing_id: values.listingId,
          presented_quantity: values.presented,
          accepted_quantity: values.accepted,
          rejected_quantity: values.rejected,
          unit_price: values.unitPrice,
          transport_deduction: values.transportDeduction,
          other_deduction: values.otherDeduction,
          rejection_reason: values.rejectionReason || null,
        },
      }),
    onSuccess: onDone,
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : "Error"),
  });

  const set =
    (key: keyof typeof values) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setValues((prev) => ({ ...prev, [key]: event.target.value }));

  return (
    <form
      className="mt-3 rounded-lg border border-earth-100 p-3"
      onSubmit={(event) => {
        event.preventDefault();
        record.mutate();
      }}
    >
      {error ? <ErrorState message={error} /> : null}
      <Field label="Harvest listing" htmlFor={`listing-${stop.id}`}>
        <select
          id={`listing-${stop.id}`}
          required
          className={inputClass}
          value={values.listingId}
          onChange={set("listingId")}
        >
          <option value="">—</option>
          {listingOptions.map((id) => (
            <option key={id} value={id}>
              {id.slice(0, 8)}…
            </option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-3 gap-2">
        <Field label={t.collection.presented} htmlFor={`presented-${stop.id}`}>
          <input
            id={`presented-${stop.id}`}
            type="number"
            step="0.01"
            min="0"
            required
            className={inputClass}
            value={values.presented}
            onChange={set("presented")}
          />
        </Field>
        <Field label={t.collection.accepted} htmlFor={`accepted-${stop.id}`}>
          <input
            id={`accepted-${stop.id}`}
            type="number"
            step="0.01"
            min="0"
            required
            className={inputClass}
            value={values.accepted}
            onChange={set("accepted")}
          />
        </Field>
        <Field label={t.collection.rejected} htmlFor={`rejected-${stop.id}`}>
          <input
            id={`rejected-${stop.id}`}
            type="number"
            step="0.01"
            min="0"
            required
            className={inputClass}
            value={values.rejected}
            onChange={set("rejected")}
          />
        </Field>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Field label={t.collection.unitPrice} htmlFor={`price-${stop.id}`}>
          <input
            id={`price-${stop.id}`}
            type="number"
            step="0.01"
            min="0"
            required
            className={inputClass}
            value={values.unitPrice}
            onChange={set("unitPrice")}
          />
        </Field>
        <Field label={t.collection.transportDeduction} htmlFor={`td-${stop.id}`}>
          <input
            id={`td-${stop.id}`}
            type="number"
            step="0.01"
            min="0"
            className={inputClass}
            value={values.transportDeduction}
            onChange={set("transportDeduction")}
          />
        </Field>
        <Field label={t.collection.otherDeduction} htmlFor={`od-${stop.id}`}>
          <input
            id={`od-${stop.id}`}
            type="number"
            step="0.01"
            min="0"
            className={inputClass}
            value={values.otherDeduction}
            onChange={set("otherDeduction")}
          />
        </Field>
      </div>
      <Field label={t.collection.rejectionReason} htmlFor={`rr-${stop.id}`}>
        <input
          id={`rr-${stop.id}`}
          className={inputClass}
          value={values.rejectionReason}
          onChange={set("rejectionReason")}
        />
      </Field>
      <Button type="submit" disabled={record.isPending}>
        {t.collection.recordCollection}
      </Button>
    </form>
  );
}

export default function ShipmentDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [openStop, setOpenStop] = useState<string | null>(null);

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/users/me") });
  const { data: shipment, isLoading } = useQuery({
    queryKey: ["shipment", params.id],
    queryFn: () => api<Shipment>(`/shipments/${params.id}`),
  });

  const setStatus = useMutation({
    mutationFn: (status: string) =>
      api(`/shipments/${params.id}/status`, { method: "POST", body: { status } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shipment", params.id] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });
  const act = useMutation({
    mutationFn: (action: string) => api(`/shipments/${params.id}/${action}`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shipment", params.id] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  if (isLoading || !shipment) return <Loading label={t.common.loading} />;

  const isTransporter = me?.role === "transporter";
  const isCoordinator = me?.role === "coordinator" || me?.role === "admin";

  return (
    <div className="max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {shipment.vehicle?.registration_number ?? "Shipment"}
        </h1>
        <StatusBadge status={shipment.status} />
      </div>
      {error ? (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      ) : null}

      <Card className="mb-4">
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-earth-700">{t.shipment.distance}</dt>
            <dd className="font-medium">
              {shipment.planned_distance_km
                ? `${shipment.planned_distance_km} km (${t.common.approximate})`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-earth-700">{t.proposal.transportCost}</dt>
            <dd className="font-medium">
              {shipment.estimated_transport_cost
                ? formatMoney(shipment.estimated_transport_cost)
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-earth-700">Driver</dt>
            <dd className="font-medium">
              {shipment.driver_name ?? "—"} {shipment.driver_phone ?? ""}
            </dd>
          </div>
          <div>
            <dt className="text-earth-700">Pickup</dt>
            <dd className="font-medium">
              {shipment.planned_pickup_at
                ? new Date(shipment.planned_pickup_at).toLocaleString()
                : "—"}
            </dd>
          </div>
        </dl>
        {shipment.incident_notes ? (
          <p className="mt-3 rounded-lg bg-maize-100 p-2 text-sm">{shipment.incident_notes}</p>
        ) : null}
      </Card>

      <Card title={t.shipment.stops} className="mb-4">
        <ol className="grid gap-2">
          {shipment.stops.map((stop) => (
            <li key={stop.id} className="rounded-lg border border-earth-100 p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {stop.sequence_number}. {stop.stop_type === "pickup" ? "Pickup" : "Delivery"} —{" "}
                  {stop.farmer_display_name ?? stop.location_name ?? "—"}
                </span>
                <StatusBadge status={stop.status} />
              </div>
              <p className="text-earth-700">
                Planned: {stop.planned_quantity ?? "—"} · Collected:{" "}
                {stop.collected_quantity ?? "—"}
              </p>
              {isCoordinator &&
              stop.stop_type === "pickup" &&
              stop.status === "planned" &&
              shipment.status === "collection_in_progress" ? (
                <>
                  <Button
                    variant="secondary"
                    className="mt-2"
                    onClick={() => setOpenStop(openStop === stop.id ? null : stop.id)}
                  >
                    {t.collection.recordCollection}
                  </Button>
                  {openStop === stop.id ? (
                    <CollectionForm
                      stop={stop}
                      onDone={() => {
                        setOpenStop(null);
                        void queryClient.invalidateQueries({ queryKey: ["shipment", params.id] });
                      }}
                    />
                  ) : null}
                </>
              ) : null}
            </li>
          ))}
        </ol>
      </Card>

      <div className="flex flex-wrap gap-2">
        {isCoordinator && shipment.status === "planning" ? (
          <Button onClick={() => act.mutate("offer")}>Offer to transporter</Button>
        ) : null}
        {isTransporter && shipment.status === "offered" ? (
          <>
            <Button onClick={() => act.mutate("accept")}>{t.shipment.acceptTrip}</Button>
            <Button variant="secondary" onClick={() => act.mutate("decline")}>
              {t.shipment.declineTrip}
            </Button>
          </>
        ) : null}
        {isCoordinator && shipment.status === "assigned" ? (
          <Button onClick={() => act.mutate("confirm")}>{t.common.confirm}</Button>
        ) : null}
        {isTransporter && shipment.status === "confirmed" ? (
          <Button onClick={() => setStatus.mutate("collection_in_progress")}>
            {t.shipment.startCollection}
          </Button>
        ) : null}
        {isTransporter && shipment.status === "collection_in_progress" ? (
          <Button onClick={() => setStatus.mutate("in_transit")}>{t.shipment.markInTransit}</Button>
        ) : null}
        {isTransporter && shipment.status === "in_transit" ? (
          <Button onClick={() => setStatus.mutate("arrived")}>{t.shipment.markArrived}</Button>
        ) : null}
        {isTransporter && ["collection_in_progress", "in_transit"].includes(shipment.status) ? (
          <Button variant="secondary" onClick={() => setStatus.mutate("delayed")}>
            {t.shipment.reportDelay}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
