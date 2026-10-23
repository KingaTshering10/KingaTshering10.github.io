"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card, Empty, Loading } from "@/components/ui";
import { formatMoney, formatQuantity, useI18n } from "@/i18n";
import { api, type Me } from "@/lib/api";
import type { CollectionReceipt } from "@/lib/types";

function Receipt({ receipt, canConfirm }: { receipt: CollectionReceipt; canConfirm: boolean }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const confirm = useMutation({
    mutationFn: () => api(`/collections/${receipt.id}/farmer-confirm`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["collections"] }),
  });

  return (
    <Card className="mb-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-semibold">{t.collection.receipt}</h2>
        <span className="font-mono text-sm">{receipt.receipt_number}</span>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <dt className="text-earth-700">Farmer</dt>
        <dd className="text-right font-medium">{receipt.farmer_display_name ?? "—"}</dd>
        <dt className="text-earth-700">{t.harvest.product}</dt>
        <dd className="text-right font-medium">{receipt.product_name ?? "—"}</dd>
        <dt className="text-earth-700">{t.common.date}</dt>
        <dd className="text-right font-medium">
          {new Date(receipt.created_at).toLocaleDateString()}
        </dd>
        <dt className="text-earth-700">{t.collection.presented}</dt>
        <dd className="text-right font-medium">
          {formatQuantity(receipt.presented_quantity, receipt.unit)}
        </dd>
        <dt className="text-earth-700">{t.collection.accepted}</dt>
        <dd className="text-right font-medium">
          {formatQuantity(receipt.accepted_quantity, receipt.unit)}
        </dd>
        <dt className="text-earth-700">{t.collection.rejected}</dt>
        <dd className="text-right font-medium">
          {formatQuantity(receipt.rejected_quantity, receipt.unit)}
          {receipt.rejection_reason ? ` — ${receipt.rejection_reason}` : ""}
        </dd>
        <dt className="text-earth-700">{t.collection.unitPrice}</dt>
        <dd className="text-right font-medium">{formatMoney(receipt.unit_price)}</dd>
        <dt className="border-t border-earth-100 pt-1 text-earth-700">{t.collection.gross}</dt>
        <dd className="border-t border-earth-100 pt-1 text-right font-medium">
          {formatMoney(receipt.gross_amount)}
        </dd>
        <dt className="text-earth-700">− {t.collection.transportDeduction}</dt>
        <dd className="text-right font-medium">{formatMoney(receipt.transport_deduction)}</dd>
        <dt className="text-earth-700">− {t.collection.platformFee}</dt>
        <dd className="text-right font-medium">{formatMoney(receipt.platform_fee)}</dd>
        <dt className="text-earth-700">− {t.collection.otherDeduction}</dt>
        <dd className="text-right font-medium">{formatMoney(receipt.other_deduction)}</dd>
        <dt className="border-t-2 border-field-600 pt-1 font-semibold">{t.collection.netDue}</dt>
        <dd className="border-t-2 border-field-600 pt-1 text-right text-lg font-bold text-field-800">
          {formatMoney(receipt.net_amount_due)}
        </dd>
      </dl>
      <div className="mt-3 flex items-center justify-between text-xs text-earth-700">
        <span>
          {receipt.coordinator_confirmation ? `✓ ${t.collection.coordinatorConfirmed}` : ""}
          {receipt.farmer_confirmation ? ` · ✓ ${t.collection.farmerConfirmed}` : ""}
        </span>
        {canConfirm && !receipt.farmer_confirmation ? (
          <Button onClick={() => confirm.mutate()} disabled={confirm.isPending}>
            {t.collection.confirmReceipt}
          </Button>
        ) : null}
      </div>
    </Card>
  );
}

export default function CollectionsPage() {
  const { t } = useI18n();
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/users/me") });
  const { data, isLoading } = useQuery({
    queryKey: ["collections"],
    queryFn: () => api<CollectionReceipt[]>("/collections"),
  });

  if (isLoading) return <Loading label={t.common.loading} />;
  return (
    <div className="max-w-xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.collections}</h1>
      {!data || data.length === 0 ? <Empty label={t.common.empty} /> : null}
      {data?.map((receipt) => (
        <Receipt key={receipt.id} receipt={receipt} canConfirm={me?.role === "farmer"} />
      ))}
    </div>
  );
}
