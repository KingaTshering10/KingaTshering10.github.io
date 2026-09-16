"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Empty, Loading } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

interface NotificationItem {
  id: string;
  subject: string;
  body: string;
  read_at: string | null;
  created_at: string;
}

export default function NotificationsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api<{ items: NotificationItem[] }>("/notifications?page_size=50"),
  });

  const readAll = useMutation({
    mutationFn: () => api("/notifications/read-all", { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      void queryClient.invalidateQueries({ queryKey: ["unread"] });
    },
  });

  if (isLoading) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t.nav.notifications}</h1>
        <Button variant="secondary" onClick={() => readAll.mutate()}>
          Mark all read
        </Button>
      </div>
      {!data || data.items.length === 0 ? <Empty label={t.common.empty} /> : null}
      <ul className="grid gap-2">
        {data?.items.map((notification) => (
          <li
            key={notification.id}
            className={`rounded-xl border p-3 ${
              notification.read_at ? "border-earth-100 bg-white" : "border-field-500 bg-field-50"
            }`}
          >
            <p className="font-medium">{notification.subject}</p>
            <p className="text-sm text-earth-700">{notification.body}</p>
            <p className="mt-1 text-xs text-earth-700">
              {new Date(notification.created_at).toLocaleString()}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
