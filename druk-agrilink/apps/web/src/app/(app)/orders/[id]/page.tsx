"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Button, Card, ErrorState, Loading, StatusBadge } from "@/components/ui";
import { formatMoney, formatQuantity, useI18n } from "@/i18n";
import { api, ApiRequestError, type Me } from "@/lib/api";
import type { Order } from "@/lib/types";

export default function OrderDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/users/me") });
  const { data: order, isLoading } = useQuery({
    queryKey: ["order", params.id],
    queryFn: () => api<Order>(`/buyer-orders/${params.id}`),
  });

  const publish = useMutation({
    mutationFn: () => api(`/buyer-orders/${params.id}/publish`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["order", params.id] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });
  const cancel = useMutation({
    mutationFn: () => api(`/buyer-orders/${params.id}/cancel`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["order", params.id] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });
  const generate = useMutation({
    mutationFn: (itemId: string) =>
      api("/match-proposals/generate", { method: "POST", body: { buyer_order_item_id: itemId } }),
    onSuccess: (result) => {
      setError(null);
      const count = (result as { count: number }).count;
      if (count === 0) setError("No compatible supply found for this item right now.");
      void queryClient.invalidateQueries({ queryKey: ["proposals"] });
    },
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  if (isLoading || !order) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {t.order.deliveryDate}: {order.required_delivery_date}
        </h1>
        <StatusBadge status={order.order_status} />
      </div>
      {error ? (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      ) : null}
      <Card className="mb-4">
        <ul className="divide-y divide-earth-100">
          {order.items?.map((item) => (
            <li
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
            >
              <div>
                <p className="font-medium">
                  {formatQuantity(item.required_quantity, item.unit)} @{" "}
                  {formatMoney(item.offered_unit_price)}/{item.unit}
                  {item.maximum_unit_price
                    ? ` (max ${formatMoney(item.maximum_unit_price)})`
                    : null}
                </p>
                {item.accepted_quantity ? (
                  <p className="text-earth-700">
                    Accepted: {formatQuantity(item.accepted_quantity, item.unit)}
                  </p>
                ) : null}
              </div>
              {(me?.role === "coordinator" || me?.role === "admin") &&
              ["published", "matching"].includes(order.order_status) ? (
                <Button onClick={() => generate.mutate(item.id)} disabled={generate.isPending}>
                  {t.proposal.generateProposals}
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      </Card>
      <div className="flex gap-2">
        {me?.role === "buyer" && order.order_status === "draft" ? (
          <Button onClick={() => publish.mutate()} disabled={publish.isPending}>
            {t.order.publish}
          </Button>
        ) : null}
        {me?.role === "buyer" &&
        ["draft", "published", "matching", "proposed"].includes(order.order_status) ? (
          <Button variant="danger" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
            {t.common.cancel}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
