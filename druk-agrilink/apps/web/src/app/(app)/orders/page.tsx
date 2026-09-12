"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Button, Empty, Loading, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import type { Order } from "@/lib/types";

export default function OrdersPage() {
  const { t } = useI18n();
  const { data, isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: () => api<Order[]>("/buyer-orders"),
  });

  return (
    <div className="max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t.nav.buyerOrders}</h1>
        <Link href="/orders/new">
          <Button>{t.order.newOrder}</Button>
        </Link>
      </div>
      {isLoading ? <Loading label={t.common.loading} /> : null}
      {data && data.length === 0 ? <Empty label={t.common.empty} /> : null}
      <ul className="grid gap-3">
        {data?.map((order) => (
          <li key={order.id}>
            <Link
              href={`/orders/${order.id}`}
              className="block rounded-xl border border-earth-100 bg-white p-4 shadow-sm hover:border-field-500"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold">
                  {t.order.deliveryDate}: {order.required_delivery_date}
                </span>
                <StatusBadge status={order.order_status} />
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
