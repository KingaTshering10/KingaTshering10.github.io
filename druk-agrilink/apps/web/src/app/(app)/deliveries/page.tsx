"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Button,
  Card,
  Empty,
  ErrorState,
  Field,
  inputClass,
  Loading,
  StatusBadge,
} from "@/components/ui";
import { useI18n } from "@/i18n";
import { api, ApiRequestError } from "@/lib/api";
import type { Shipment } from "@/lib/types";

interface DeliveryRecord {
  id: string;
  shipment_id: string;
  delivered_quantity: string;
  accepted_quantity: string;
  rejected_quantity: string;
  discrepancy_flag: boolean;
  discrepancy_note: string | null;
  buyer_confirmation: boolean;
}

function ConfirmForm({ shipment, onDone }: { shipment: Shipment; onDone: () => void }) {
  const { t } = useI18n();
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({
    delivered: "",
    accepted: "",
    rejected: "0",
    condition: "good",
    reason: "",
  });

  const record = useMutation({
    mutationFn: () =>
      api("/deliveries", {
        method: "POST",
        body: {
          shipment_id: shipment.id,
          delivered_quantity: values.delivered,
          accepted_quantity: values.accepted,
          rejected_quantity: values.rejected,
          arrival_condition: values.condition,
          rejection_reason: values.reason || null,
        },
      }),
    onSuccess: onDone,
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  return (
    <form
      className="mt-3 rounded-lg border border-earth-100 p-3"
      onSubmit={(event) => {
        event.preventDefault();
        record.mutate();
      }}
    >
      {error ? <ErrorState message={error} /> : null}
      <div className="grid grid-cols-3 gap-2">
        <Field label={t.delivery.delivered} htmlFor={`delivered-${shipment.id}`}>
          <input
            id={`delivered-${shipment.id}`}
            type="number"
            step="0.01"
            min="0"
            required
            className={inputClass}
            value={values.delivered}
            onChange={(e) => setValues({ ...values, delivered: e.target.value })}
          />
        </Field>
        <Field label={t.delivery.acceptedQty} htmlFor={`accepted-${shipment.id}`}>
          <input
            id={`accepted-${shipment.id}`}
            type="number"
            step="0.01"
            min="0"
            required
            className={inputClass}
            value={values.accepted}
            onChange={(e) => setValues({ ...values, accepted: e.target.value })}
          />
        </Field>
        <Field label={t.delivery.rejectedQty} htmlFor={`rejected-${shipment.id}`}>
          <input
            id={`rejected-${shipment.id}`}
            type="number"
            step="0.01"
            min="0"
            required
            className={inputClass}
            value={values.rejected}
            onChange={(e) => setValues({ ...values, rejected: e.target.value })}
          />
        </Field>
      </div>
      <Field label={t.delivery.condition} htmlFor={`condition-${shipment.id}`}>
        <input
          id={`condition-${shipment.id}`}
          className={inputClass}
          value={values.condition}
          onChange={(e) => setValues({ ...values, condition: e.target.value })}
        />
      </Field>
      <Field label={t.collection.rejectionReason} htmlFor={`reason-${shipment.id}`}>
        <input
          id={`reason-${shipment.id}`}
          className={inputClass}
          value={values.reason}
          onChange={(e) => setValues({ ...values, reason: e.target.value })}
        />
      </Field>
      <Button type="submit" disabled={record.isPending}>
        {t.delivery.confirmDelivery}
      </Button>
    </form>
  );
}

export default function DeliveriesPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [openId, setOpenId] = useState<string | null>(null);

  const { data: shipments, isLoading } = useQuery({
    queryKey: ["shipments"],
    queryFn: () => api<Shipment[]>("/shipments"),
  });
  const { data: deliveries } = useQuery({
    queryKey: ["deliveries"],
    queryFn: () => api<DeliveryRecord[]>("/deliveries"),
  });

  if (isLoading) return <Loading label={t.common.loading} />;
  const arrived = shipments?.filter((shipment) => shipment.status === "arrived") ?? [];

  return (
    <div className="max-w-xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.deliveries}</h1>

      {arrived.map((shipment) => (
        <Card key={shipment.id} className="mb-4">
          <div className="flex items-center justify-between">
            <span className="font-semibold">
              {shipment.vehicle?.registration_number ?? "Shipment"} · arrived
            </span>
            <Button
              variant="secondary"
              onClick={() => setOpenId(openId === shipment.id ? null : shipment.id)}
            >
              {t.delivery.confirmDelivery}
            </Button>
          </div>
          {openId === shipment.id ? (
            <ConfirmForm
              shipment={shipment}
              onDone={() => {
                setOpenId(null);
                void queryClient.invalidateQueries({ queryKey: ["shipments"] });
                void queryClient.invalidateQueries({ queryKey: ["deliveries"] });
              }}
            />
          ) : null}
        </Card>
      ))}

      {(!deliveries || deliveries.length === 0) && arrived.length === 0 ? (
        <Empty label={t.common.empty} />
      ) : null}
      {deliveries?.map((delivery) => (
        <Card key={delivery.id} className="mb-3">
          <div className="flex items-center justify-between text-sm">
            <div>
              <p className="font-medium">
                {t.delivery.delivered}: {delivery.delivered_quantity} · {t.delivery.acceptedQty}:{" "}
                {delivery.accepted_quantity} · {t.delivery.rejectedQty}:{" "}
                {delivery.rejected_quantity}
              </p>
              {delivery.discrepancy_flag ? (
                <p className="mt-1 rounded bg-maize-100 p-1 text-xs">
                  ⚠ {t.delivery.discrepancy}: {delivery.discrepancy_note}
                </p>
              ) : null}
            </div>
            <StatusBadge status={delivery.buyer_confirmation ? "confirmed" : "pending"} />
          </div>
        </Card>
      ))}
    </div>
  );
}
