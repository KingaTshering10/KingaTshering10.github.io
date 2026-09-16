"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card, Empty, Loading, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

interface Group {
  id: string;
  name: string;
  dzongkhag: string;
}
interface Member {
  id: string;
  display_name: string;
  membership_status: string;
  verification_status: string;
}

function GroupMembers({ group }: { group: Group }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { data: members } = useQuery({
    queryKey: ["members", group.id],
    queryFn: () => api<Member[]>(`/farmer-groups/${group.id}/members`),
  });

  const approveMembership = useMutation({
    mutationFn: (profileId: string) =>
      api(`/farmer-groups/${group.id}/members/${profileId}/approve`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["members", group.id] }),
  });
  const verify = useMutation({
    mutationFn: ({ profileId, approve }: { profileId: string; approve: boolean }) =>
      api(`/farmers/${profileId}/verify`, { method: "POST", body: { approve } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["members", group.id] }),
  });

  return (
    <Card title={`${group.name} (${group.dzongkhag})`} className="mb-4">
      {!members || members.length === 0 ? (
        <p className="text-sm text-earth-700">{t.common.empty}</p>
      ) : (
        <ul className="divide-y divide-earth-100">
          {members.map((member) => (
            <li
              key={member.id}
              className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
            >
              <div>
                <span className="font-medium">{member.display_name}</span>
                <span className="ml-2">
                  <StatusBadge status={member.verification_status} />
                </span>
              </div>
              <div className="flex gap-2">
                {member.membership_status === "requested" ? (
                  <Button onClick={() => approveMembership.mutate(member.id)}>
                    Approve membership
                  </Button>
                ) : null}
                {member.verification_status === "pending" ? (
                  <>
                    <Button onClick={() => verify.mutate({ profileId: member.id, approve: true })}>
                      Verify
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => verify.mutate({ profileId: member.id, approve: false })}
                    >
                      {t.common.reject}
                    </Button>
                  </>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function FarmersPage() {
  const { t } = useI18n();
  const { data: groups, isLoading } = useQuery({
    queryKey: ["my-groups"],
    queryFn: () => api<Group[]>("/farmer-groups/mine"),
  });

  if (isLoading) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.farmers}</h1>
      {!groups || groups.length === 0 ? <Empty label={t.common.empty} /> : null}
      {groups?.map((group) => <GroupMembers key={group.id} group={group} />)}
    </div>
  );
}
