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

interface Vehicle {
  id: string;
  registration_number: string;
  vehicle_type: string;
  capacity_kg: string;
  has_refrigeration: boolean;
  is_available: boolean;
  verification_status: string;
}

export default function VehiclesPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({
    registration: "",
    type: "light_truck",
    capacity: "",
    refrigerated: false,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["vehicles"],
    queryFn: () => api<Vehicle[]>("/vehicles"),
  });

  const create = useMutation({
    mutationFn: () =>
      api("/vehicles", {
        method: "POST",
        body: {
          registration_number: values.registration,
          vehicle_type: values.type,
          capacity_kg: values.capacity,
          has_refrigeration: values.refrigerated,
        },
      }),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });
  const toggleAvailability = useMutation({
    mutationFn: ({ id, available }: { id: string; available: boolean }) =>
      api(`/vehicles/${id}/availability`, { method: "PATCH", body: { is_available: available } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vehicles"] }),
  });

  if (isLoading) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.vehicles}</h1>
      {error ? (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      ) : null}

      <Card title="Register vehicle" className="mb-6">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            create.mutate();
          }}
        >
          <div className="grid grid-cols-2 gap-2">
            <Field label="Registration number" htmlFor="registration">
              <input
                id="registration"
                required
                minLength={3}
                className={inputClass}
                value={values.registration}
                onChange={(e) => setValues({ ...values, registration: e.target.value })}
              />
            </Field>
            <Field label="Type" htmlFor="type">
              <select
                id="type"
                className={inputClass}
                value={values.type}
                onChange={(e) => setValues({ ...values, type: e.target.value })}
              >
                {["pickup", "light_truck", "truck", "refrigerated_truck", "utility"].map((type) => (
                  <option key={type} value={type}>
                    {type.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Capacity (kg)" htmlFor="capacity">
              <input
                id="capacity"
                type="number"
                min="1"
                required
                className={inputClass}
                value={values.capacity}
                onChange={(e) => setValues({ ...values, capacity: e.target.value })}
              />
            </Field>
          </div>
          <label className="mb-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-5 w-5"
              checked={values.refrigerated}
              onChange={(e) => setValues({ ...values, refrigerated: e.target.checked })}
            />
            Refrigerated
          </label>
          <Button type="submit" disabled={create.isPending}>
            {t.common.save}
          </Button>
        </form>
      </Card>

      {!data || data.length === 0 ? <Empty label={t.common.empty} /> : null}
      {data?.map((vehicle) => (
        <Card key={vehicle.id} className="mb-3">
          <div className="flex items-center justify-between text-sm">
            <div>
              <p className="font-semibold">{vehicle.registration_number}</p>
              <p className="text-earth-700">
                {vehicle.vehicle_type.replaceAll("_", " ")} · {vehicle.capacity_kg} kg
                {vehicle.has_refrigeration ? " · refrigerated" : ""}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <StatusBadge status={vehicle.verification_status} />
              <Button
                variant="secondary"
                onClick={() =>
                  toggleAvailability.mutate({ id: vehicle.id, available: !vehicle.is_available })
                }
              >
                {vehicle.is_available ? "Set unavailable" : "Set available"}
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
