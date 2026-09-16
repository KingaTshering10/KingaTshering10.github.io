"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Empty, Loading, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

interface UserRow {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export default function AdminUsersPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => api<{ items: UserRow[] }>("/admin/users?page_size=50"),
  });

  const toggle = useMutation({
    mutationFn: ({ id, suspend }: { id: string; suspend: boolean }) =>
      api(`/admin/users/${id}/${suspend ? "suspend" : "reinstate"}`, {
        method: "POST",
        body: { reason: suspend ? "Suspended by administrator" : "Reinstated by administrator" },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  if (isLoading) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.users}</h1>
      {!data || data.items.length === 0 ? <Empty label={t.common.empty} /> : null}
      <div className="overflow-x-auto rounded-xl border border-earth-100 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-earth-100 text-xs uppercase text-earth-700">
            <tr>
              <th className="p-3">Email</th>
              <th className="p-3">Role</th>
              <th className="p-3">{t.common.status}</th>
              <th className="p-3">{t.common.actions}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-earth-100">
            {data?.items.map((user) => (
              <tr key={user.id}>
                <td className="p-3">{user.email}</td>
                <td className="p-3">{user.role}</td>
                <td className="p-3">
                  <StatusBadge status={user.is_active ? "confirmed" : "cancelled"} />
                </td>
                <td className="p-3">
                  {user.role !== "admin" ? (
                    <Button
                      variant={user.is_active ? "danger" : "secondary"}
                      onClick={() => toggle.mutate({ id: user.id, suspend: user.is_active })}
                    >
                      {user.is_active ? "Suspend" : "Reinstate"}
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
