"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, Empty, ErrorState, Loading, StatusBadge } from "@/components/ui";
import { formatMoney, formatQuantity, useI18n } from "@/i18n";
import { api, ApiRequestError, type Me } from "@/lib/api";
import type { Proposal } from "@/lib/types";

function FactorBar({ name, value }: { name: string; value: number }) {
  return (
    <div className="mb-1">
      <div className="flex justify-between text-xs">
        <span>{name.replaceAll("_", " ")}</span>
        <span className="font-medium">{value}</span>
      </div>
      <div className="h-2 rounded bg-earth-50" role="presentation">
        <div className="h-2 rounded bg-field-500" style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
}

export default function ProposalsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/users/me") });
  const { data, isLoading } = useQuery({
    queryKey: ["proposals"],
    queryFn: () => api<Proposal[]>("/match-proposals"),
  });

  const act = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api(`/match-proposals/${id}/${action}`, {
        method: "POST",
        body: action === "reject" ? { reason: "Rejected from proposal review" } : undefined,
      }),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["proposals"] });
    },
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  if (isLoading) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-3xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.matchProposals}</h1>
      {error ? (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      ) : null}
      {!data || data.length === 0 ? <Empty label={t.common.empty} /> : null}
      {data?.map((proposal) => (
        <Card key={proposal.id} className="mb-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="font-semibold">
                {proposal.product_name} ·{" "}
                {formatQuantity(proposal.proposed_quantity, proposal.unit)}
              </span>
              <span className="ml-3 rounded-full bg-field-100 px-3 py-1 text-sm font-bold text-field-800">
                {t.proposal.score}: {proposal.score}/100
              </span>
            </div>
            <StatusBadge status={proposal.status} />
          </div>

          <div className="mb-3 grid gap-4 sm:grid-cols-2">
            <div>
              <h3 className="mb-2 text-sm font-semibold">{t.proposal.score}</h3>
              {Object.entries(proposal.score_factors).map(([name, value]) => (
                <FactorBar key={name} name={name} value={value} />
              ))}
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold">{t.proposal.explanation}</h3>
              <ul className="list-disc pl-5 text-sm text-earth-700">
                {proposal.score_explanation.map((sentence) => (
                  <li key={sentence}>{sentence}</li>
                ))}
              </ul>
              {proposal.estimated_transport_cost ? (
                <p className="mt-2 text-sm">
                  {t.proposal.transportCost} ({t.common.approximate}):{" "}
                  <strong>{formatMoney(proposal.estimated_transport_cost)}</strong>
                </p>
              ) : null}
              {proposal.estimated_spoilage_risk ? (
                <p className="text-sm">
                  {t.proposal.spoilageRisk}: <strong>{proposal.estimated_spoilage_risk}</strong>
                </p>
              ) : null}
            </div>
          </div>

          <div className="mb-3">
            <h3 className="mb-1 text-sm font-semibold">{t.proposal.allocations}</h3>
            <ul className="text-sm text-earth-700">
              {proposal.allocations.map((allocation) => (
                <li
                  key={allocation.id}
                  className="flex justify-between border-t border-earth-100 py-1"
                >
                  <span>
                    {formatQuantity(allocation.allocated_quantity, proposal.unit)} @{" "}
                    {formatMoney(allocation.agreed_unit_price)}
                  </span>
                  <StatusBadge status={allocation.farmer_response} />
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-wrap gap-2">
            {(me?.role === "coordinator" || me?.role === "admin") &&
            proposal.status === "generated" ? (
              <Button onClick={() => act.mutate({ id: proposal.id, action: "send-to-review" })}>
                Review
              </Button>
            ) : null}
            {(me?.role === "coordinator" || me?.role === "admin") &&
            proposal.status === "coordinator_review" ? (
              <Button onClick={() => act.mutate({ id: proposal.id, action: "send-to-farmers" })}>
                {t.proposal.sendToFarmers}
              </Button>
            ) : null}
            {me?.role === "buyer" && proposal.status === "buyer_confirmation" ? (
              <>
                <Button onClick={() => act.mutate({ id: proposal.id, action: "buyer-approve" })}>
                  {t.common.approve}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => act.mutate({ id: proposal.id, action: "reject" })}
                >
                  {t.common.reject}
                </Button>
              </>
            ) : null}
          </div>
        </Card>
      ))}
    </div>
  );
}
