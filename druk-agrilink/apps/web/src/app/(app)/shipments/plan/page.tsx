"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Card, ErrorState, Field, inputClass, Loading } from "@/components/ui";
import { formatQuantity, useI18n } from "@/i18n";
import { api, ApiRequestError } from "@/lib/api";
import type { Proposal } from "@/lib/types";

interface VehicleOption {
  id: string;
  registration_number: string;
  capacity_kg: string;
  has_refrigeration: boolean;
}

export default function PlanShipmentPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({
    proposalId: "",
    vehicleId: "",
    pickupAt: "",
    deliveryAt: "",
    driverName: "",
    driverPhone: "",
  });

  const { data: proposals, isLoading } = useQuery({
    queryKey: ["approved-proposals"],
    queryFn: () => api<Proposal[]>("/match-proposals?status=approved"),
  });
  // Coordinators do not own vehicles; list every verified vehicle via admin-visible endpoint
  const { data: shipmentsExisting } = useQuery({
    queryKey: ["shipments"],
    queryFn: () => api<{ id: string; match_proposal_id: string }[]>("/shipments"),
  });
  const { data: vehicles } = useQuery({
    queryKey: ["all-vehicles"],
    queryFn: () => api<VehicleOption[]>("/vehicles").catch(() => [] as VehicleOption[]),
  });

  const plan = useMutation({
    mutationFn: () =>
      api("/shipments/plan", {
        method: "POST",
        body: {
          match_proposal_id: values.proposalId,
          vehicle_id: values.vehicleId,
          planned_pickup_at: values.pickupAt,
          planned_delivery_at: values.deliveryAt,
          driver_name: values.driverName || null,
          driver_phone: values.driverPhone || null,
        },
      }),
    onSuccess: (shipment) => router.push(`/shipments/${(shipment as { id: string }).id}`),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  if (isLoading) return <Loading label={t.common.loading} />;

  const shippedProposalIds = new Set(shipmentsExisting?.map((s) => s.match_proposal_id) ?? []);
  const shippable = proposals?.filter((proposal) => !shippedProposalIds.has(proposal.id)) ?? [];

  return (
    <div className="max-w-lg">
      <h1 className="mb-6 text-2xl font-bold">{t.shipment.planShipment}</h1>
      {error ? (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      ) : null}
      <Card>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            plan.mutate();
          }}
        >
          <Field label={t.nav.matchProposals} htmlFor="proposal">
            <select
              id="proposal"
              required
              className={inputClass}
              value={values.proposalId}
              onChange={(event) => setValues({ ...values, proposalId: event.target.value })}
            >
              <option value="">—</option>
              {shippable.map((proposal) => (
                <option key={proposal.id} value={proposal.id}>
                  {proposal.product_name} —{" "}
                  {formatQuantity(proposal.proposed_quantity, proposal.unit)}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label={t.shipment.vehicle}
            htmlFor="vehicle"
            hint="Vehicle ID can also be pasted directly if it is not listed."
          >
            <input
              id="vehicle"
              required
              className={inputClass}
              list="vehicle-options"
              value={values.vehicleId}
              onChange={(event) => setValues({ ...values, vehicleId: event.target.value })}
            />
            <datalist id="vehicle-options">
              {vehicles?.map((vehicle) => (
                <option key={vehicle.id} value={vehicle.id}>
                  {vehicle.registration_number} ({vehicle.capacity_kg} kg)
                </option>
              ))}
            </datalist>
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Pickup at" htmlFor="pickupAt">
              <input
                id="pickupAt"
                type="datetime-local"
                required
                className={inputClass}
                value={values.pickupAt}
                onChange={(e) => setValues({ ...values, pickupAt: e.target.value })}
              />
            </Field>
            <Field label="Delivery at" htmlFor="deliveryAt">
              <input
                id="deliveryAt"
                type="datetime-local"
                required
                className={inputClass}
                value={values.deliveryAt}
                onChange={(e) => setValues({ ...values, deliveryAt: e.target.value })}
              />
            </Field>
            <Field label="Driver name" htmlFor="driverName">
              <input
                id="driverName"
                className={inputClass}
                value={values.driverName}
                onChange={(e) => setValues({ ...values, driverName: e.target.value })}
              />
            </Field>
            <Field label="Driver phone" htmlFor="driverPhone">
              <input
                id="driverPhone"
                type="tel"
                className={inputClass}
                value={values.driverPhone}
                onChange={(e) => setValues({ ...values, driverPhone: e.target.value })}
              />
            </Field>
          </div>
          <Button type="submit" disabled={plan.isPending}>
            {t.shipment.planShipment}
          </Button>
        </form>
      </Card>
    </div>
  );
}
