"use client";

import { useQuery } from "@tanstack/react-query";
import { Empty, Loading } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

interface AuditEntry {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  reason: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  created_at: string;
}

export default function AuditLogPage() {
  const { t } = useI18n();
  const { data, isLoading } = useQuery({
    queryKey: ["audit"],
    queryFn: () => api<{ items: AuditEntry[] }>("/admin/audit-logs?page_size=50"),
  });

  if (isLoading) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.auditLog}</h1>
      {!data || data.items.length === 0 ? <Empty label={t.common.empty} /> : null}
      <div className="overflow-x-auto rounded-xl border border-earth-100 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-earth-100 text-xs uppercase text-earth-700">
            <tr>
              <th className="p-3">Action</th>
              <th className="p-3">Entity</th>
              <th className="p-3">Change</th>
              <th className="p-3">When</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-earth-100">
            {data?.items.map((entry) => (
              <tr key={entry.id}>
                <td className="p-3 font-medium">{entry.action}</td>
                <td className="p-3">{entry.entity_type}</td>
                <td className="p-3 text-xs">
                  {entry.after_state ? JSON.stringify(entry.after_state) : (entry.reason ?? "—")}
                </td>
                <td className="p-3 text-xs">{new Date(entry.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
