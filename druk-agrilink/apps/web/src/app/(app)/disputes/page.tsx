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
import { api, ApiRequestError, type Me } from "@/lib/api";
import type { Dispute } from "@/lib/types";

const CATEGORIES = [
  "overdue_payment",
  "incorrect_amount",
  "missing_payment",
  "unexplained_deduction",
  "delivery_rejection",
  "quantity_mismatch",
  "other",
];

export default function DisputesPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [values, setValues] = useState({
    category: "overdue_payment",
    description: "",
    entityType: "payment_record",
    entityId: "",
  });
  const [resolutions, setResolutions] = useState<Record<string, string>>({});

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/users/me") });
  const { data, isLoading } = useQuery({
    queryKey: ["disputes"],
    queryFn: () => api<Dispute[]>("/disputes"),
  });

  const create = useMutation({
    mutationFn: () =>
      api("/disputes", {
        method: "POST",
        body: {
          category: values.category,
          description: values.description,
          related_entity_type: values.entityType,
          related_entity_id: values.entityId,
        },
      }),
    onSuccess: () => {
      setShowForm(false);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["disputes"] });
    },
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  const act = useMutation({
    mutationFn: ({ id, action, resolution }: { id: string; action: string; resolution?: string }) =>
      api(`/disputes/${id}/${action}`, {
        method: "POST",
        body: action === "resolve" ? { resolution } : undefined,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["disputes"] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  if (isLoading) return <Loading label={t.common.loading} />;
  const isStaff = me?.role === "coordinator" || me?.role === "admin";

  return (
    <div className="max-w-xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t.nav.disputes}</h1>
        <Button onClick={() => setShowForm(!showForm)}>{t.dispute.open}</Button>
      </div>
      {error ? (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      ) : null}

      {showForm ? (
        <Card className="mb-6">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              create.mutate();
            }}
          >
            <Field label={t.dispute.category} htmlFor="category">
              <select
                id="category"
                className={inputClass}
                value={values.category}
                onChange={(event) => setValues({ ...values, category: event.target.value })}
              >
                {CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Related record type" htmlFor="entityType">
              <select
                id="entityType"
                className={inputClass}
                value={values.entityType}
                onChange={(event) => setValues({ ...values, entityType: event.target.value })}
              >
                <option value="payment_record">Payment</option>
                <option value="collection_record">Collection receipt</option>
                <option value="delivery_record">Delivery</option>
                <option value="buyer_order">Order</option>
              </select>
            </Field>
            <Field label="Related record ID" htmlFor="entityId">
              <input
                id="entityId"
                required
                className={inputClass}
                value={values.entityId}
                onChange={(event) => setValues({ ...values, entityId: event.target.value })}
                placeholder="Paste the ID from the record's page"
              />
            </Field>
            <Field label={t.dispute.description} htmlFor="description">
              <textarea
                id="description"
                rows={3}
                required
                minLength={10}
                className={inputClass}
                value={values.description}
                onChange={(event) => setValues({ ...values, description: event.target.value })}
              />
            </Field>
            <Button type="submit" disabled={create.isPending}>
              {t.common.submit}
            </Button>
          </form>
        </Card>
      ) : null}

      {!data || data.length === 0 ? <Empty label={t.common.empty} /> : null}
      {data?.map((dispute) => (
        <Card key={dispute.id} className="mb-3">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-semibold">{dispute.category.replaceAll("_", " ")}</span>
            <StatusBadge status={dispute.status} />
          </div>
          <p className="mb-2 text-sm text-earth-700">{dispute.description}</p>
          {dispute.resolution ? (
            <p className="rounded-lg bg-field-50 p-2 text-sm">
              <strong>{t.dispute.resolution}:</strong> {dispute.resolution}
            </p>
          ) : null}
          {isStaff && dispute.status === "open" ? (
            <Button
              variant="secondary"
              className="mt-2"
              onClick={() => act.mutate({ id: dispute.id, action: "assign" })}
            >
              {t.dispute.assign}
            </Button>
          ) : null}
          {isStaff && dispute.status === "under_review" ? (
            <form
              className="mt-2"
              onSubmit={(event) => {
                event.preventDefault();
                act.mutate({
                  id: dispute.id,
                  action: "resolve",
                  resolution: resolutions[dispute.id] ?? "",
                });
              }}
            >
              <Field label={t.dispute.resolution} htmlFor={`resolution-${dispute.id}`}>
                <textarea
                  id={`resolution-${dispute.id}`}
                  rows={2}
                  required
                  minLength={5}
                  className={inputClass}
                  value={resolutions[dispute.id] ?? ""}
                  onChange={(event) =>
                    setResolutions({ ...resolutions, [dispute.id]: event.target.value })
                  }
                />
              </Field>
              <Button type="submit">{t.dispute.resolve}</Button>
            </form>
          ) : null}
        </Card>
      ))}
    </div>
  );
}
