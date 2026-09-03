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
import { formatMoney, useI18n } from "@/i18n";
import { api, ApiRequestError, type Me } from "@/lib/api";
import type { Payment } from "@/lib/types";

function RecordForm({ payment, onDone }: { payment: Payment; onDone: () => void }) {
  const { t } = useI18n();
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({
    amount: String(Number(payment.amount) - Number(payment.amount_paid)),
    method: "bank_transfer",
    reference: "",
    paidAt: new Date().toISOString().slice(0, 10),
  });

  const record = useMutation({
    mutationFn: () =>
      api(`/payments/${payment.id}/record`, {
        method: "POST",
        body: {
          amount: values.amount,
          payment_method: values.method,
          payment_reference: values.reference,
          paid_at: `${values.paidAt}T12:00:00Z`,
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
      <div className="grid grid-cols-2 gap-2">
        <Field label={t.payment.amount} htmlFor={`amount-${payment.id}`}>
          <input
            id={`amount-${payment.id}`}
            type="number"
            step="0.01"
            min="0.01"
            required
            className={inputClass}
            value={values.amount}
            onChange={(event) => setValues({ ...values, amount: event.target.value })}
          />
        </Field>
        <Field label={t.payment.method} htmlFor={`method-${payment.id}`}>
          <select
            id={`method-${payment.id}`}
            className={inputClass}
            value={values.method}
            onChange={(event) => setValues({ ...values, method: event.target.value })}
          >
            <option value="bank_transfer">Bank transfer</option>
            <option value="mbob">mBoB</option>
            <option value="cash">Cash</option>
            <option value="cheque">Cheque</option>
          </select>
        </Field>
        <Field label={t.payment.reference} htmlFor={`reference-${payment.id}`}>
          <input
            id={`reference-${payment.id}`}
            required
            minLength={2}
            className={inputClass}
            value={values.reference}
            onChange={(event) => setValues({ ...values, reference: event.target.value })}
          />
        </Field>
        <Field label={t.common.date} htmlFor={`paidAt-${payment.id}`}>
          <input
            id={`paidAt-${payment.id}`}
            type="date"
            required
            className={inputClass}
            value={values.paidAt}
            onChange={(event) => setValues({ ...values, paidAt: event.target.value })}
          />
        </Field>
      </div>
      <Button type="submit" disabled={record.isPending}>
        {t.payment.recordPayment}
      </Button>
    </form>
  );
}

export default function PaymentsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [openId, setOpenId] = useState<string | null>(null);

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/users/me") });
  const { data, isLoading } = useQuery({
    queryKey: ["payments"],
    queryFn: () => api<Payment[]>("/payments"),
  });

  if (isLoading) return <Loading label={t.common.loading} />;
  const canRecord = me?.role === "coordinator" || me?.role === "admin" || me?.role === "buyer";

  return (
    <div className="max-w-xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.payments}</h1>
      {!data || data.length === 0 ? <Empty label={t.common.empty} /> : null}
      {data?.map((payment) => (
        <Card key={payment.id} className="mb-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold">{formatMoney(payment.amount)}</p>
              <p className="text-xs text-earth-700">
                {payment.payer_type.replaceAll("_", " ")} →{" "}
                {payment.recipient_type.replaceAll("_", " ")}
                {payment.due_date ? ` · ${t.payment.due} ${payment.due_date}` : ""}
              </p>
              {payment.payment_reference ? (
                <p className="text-xs text-earth-700">
                  {t.payment.reference}: {payment.payment_reference} ({payment.payment_method})
                </p>
              ) : null}
              {Number(payment.amount_paid) > 0 && payment.status !== "paid" ? (
                <p className="text-xs text-earth-700">
                  {t.payment.paid}: {formatMoney(payment.amount_paid)}
                </p>
              ) : null}
            </div>
            <div className="flex flex-col items-end gap-2">
              <StatusBadge status={payment.status} />
              {canRecord && !["paid", "cancelled", "waived"].includes(payment.status) ? (
                <Button
                  variant="secondary"
                  onClick={() => setOpenId(openId === payment.id ? null : payment.id)}
                >
                  {t.payment.recordPayment}
                </Button>
              ) : null}
            </div>
          </div>
          {openId === payment.id ? (
            <RecordForm
              payment={payment}
              onDone={() => {
                setOpenId(null);
                void queryClient.invalidateQueries({ queryKey: ["payments"] });
              }}
            />
          ) : null}
        </Card>
      ))}
    </div>
  );
}
