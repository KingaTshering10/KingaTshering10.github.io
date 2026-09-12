"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card, Empty, Loading } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

interface Queue {
  farmers: { id: string; display_name: string }[];
  buyer_organizations: { id: string; name: string }[];
  transport_providers: { id: string; name: string }[];
  farmer_groups: { id: string; name: string }[];
  vehicles: { id: string; registration_number: string }[];
}

const VERIFY_PATHS: Record<string, string> = {
  farmers: "/farmers/{id}/verify",
  buyer_organizations: "/admin/buyer-organizations/{id}/verify",
  transport_providers: "/admin/transport-providers/{id}/verify",
  farmer_groups: "/admin/farmer-groups/{id}/verify",
  vehicles: "/admin/vehicles/{id}/verify",
};

export default function VerificationQueuePage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["verification-queue"],
    queryFn: () => api<Queue>("/admin/verification-queue"),
  });

  const decide = useMutation({
    mutationFn: ({ kind, id, approve }: { kind: string; id: string; approve: boolean }) =>
      api((VERIFY_PATHS[kind] ?? "").replace("{id}", id), {
        method: "POST",
        body: { approve, reason: approve ? null : "Rejected during verification review" },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["verification-queue"] }),
  });

  if (isLoading || !data) return <Loading label={t.common.loading} />;

  const sections: [keyof Queue, string, (item: never) => string][] = [
    ["farmers", "Farmers", (item: { display_name: string }) => item.display_name],
    ["buyer_organizations", "Buyer organizations", (item: { name: string }) => item.name],
    ["transport_providers", "Transport providers", (item: { name: string }) => item.name],
    ["farmer_groups", "Farmer groups", (item: { name: string }) => item.name],
    ["vehicles", "Vehicles", (item: { registration_number: string }) => item.registration_number],
  ] as never;

  const isEmpty = sections.every(([key]) => data[key].length === 0);

  return (
    <div className="max-w-xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.verification}</h1>
      {isEmpty ? <Empty label={t.common.empty} /> : null}
      {sections.map(([key, title, label]) =>
        data[key].length > 0 ? (
          <Card key={key} title={title} className="mb-4">
            <ul className="divide-y divide-earth-100">
              {data[key].map((item) => (
                <li key={item.id} className="flex items-center justify-between py-2 text-sm">
                  <span>{label(item as never)}</span>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => decide.mutate({ kind: key, id: item.id, approve: true })}
                    >
                      {t.common.approve}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => decide.mutate({ kind: key, id: item.id, approve: false })}
                    >
                      {t.common.reject}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        ) : null,
      )}
    </div>
  );
}
