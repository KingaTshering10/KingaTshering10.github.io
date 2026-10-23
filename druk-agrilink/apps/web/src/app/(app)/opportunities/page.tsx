"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, ConfirmDialog, Empty, Loading, StatusBadge } from "@/components/ui";
import { formatMoney, formatQuantity, useI18n } from "@/i18n";
import { api } from "@/lib/api";
import type { Proposal } from "@/lib/types";

export default function OpportunitiesPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [pendingDecision, setPendingDecision] = useState<{
    allocationId: string;
    accept: boolean;
  } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["proposals"],
    queryFn: () => api<Proposal[]>("/match-proposals"),
  });

  const respond = useMutation({
    mutationFn: ({ allocationId, accept }: { allocationId: string; accept: boolean }) =>
      api(`/match-proposals/allocations/${allocationId}/respond`, {
        method: "POST",
        body: { accept },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["proposals"] }),
  });

  if (isLoading) return <Loading label={t.common.loading} />;
  const open = data?.filter((p) => p.status === "farmer_confirmation") ?? [];
  const others = data?.filter((p) => p.status !== "farmer_confirmation") ?? [];

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.opportunities}</h1>
      {open.length === 0 && others.length === 0 ? <Empty label={t.common.empty} /> : null}

      {open.map((proposal) => (
        <Card key={proposal.id} className="mb-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-semibold">
              {proposal.product_name} · {formatQuantity(proposal.proposed_quantity, proposal.unit)}
            </span>
            <StatusBadge status={proposal.status} />
          </div>
          <ul className="mb-3 list-disc pl-5 text-sm text-earth-700">
            {proposal.score_explanation.map((sentence) => (
              <li key={sentence}>{sentence}</li>
            ))}
          </ul>
          {proposal.allocations
            .filter((allocation) => allocation.farmer_response === "pending")
            .map((allocation) => (
              <div
                key={allocation.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-earth-100 p-3"
              >
                <div className="text-sm">
                  <p className="font-medium">
                    {formatQuantity(allocation.allocated_quantity, proposal.unit)} @{" "}
                    {formatMoney(allocation.agreed_unit_price)}/{proposal.unit}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() =>
                      setPendingDecision({ allocationId: allocation.id, accept: true })
                    }
                  >
                    {t.common.accept}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() =>
                      setPendingDecision({ allocationId: allocation.id, accept: false })
                    }
                  >
                    {t.common.decline}
                  </Button>
                </div>
              </div>
            ))}
        </Card>
      ))}

      {others.length > 0 ? (
        <Card title="History">
          <ul className="divide-y divide-earth-100 text-sm">
            {others.map((proposal) => (
              <li key={proposal.id} className="flex items-center justify-between py-2">
                <span>
                  {proposal.product_name} ·{" "}
                  {formatQuantity(proposal.proposed_quantity, proposal.unit)}
                </span>
                <StatusBadge status={proposal.status} />
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <ConfirmDialog
        open={pendingDecision !== null}
        message={t.common.areYouSure}
        confirmLabel={t.common.confirm}
        cancelLabel={t.common.cancel}
        onConfirm={() => {
          if (pendingDecision) respond.mutate(pendingDecision);
          setPendingDecision(null);
        }}
        onCancel={() => setPendingDecision(null)}
      />
    </div>
  );
}
