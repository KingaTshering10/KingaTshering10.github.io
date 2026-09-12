"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { I18nProvider, useI18n } from "@/i18n";
import { api } from "@/lib/api";
import { syncDrafts } from "@/lib/offline";

function OfflineBanner() {
  const { t } = useI18n();
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    setOffline(!navigator.onLine);
    const goOffline = () => setOffline(true);
    const goOnline = () => {
      setOffline(false);
      // automatic retry of the sync queue on reconnect
      void syncDrafts(api as never);
    };
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

  if (!offline) return null;
  return (
    <div role="status" className="bg-maize-100 px-4 py-2 text-center text-sm text-maize-700">
      {t.common.offline}
    </div>
  );
}

function ServiceWorkerRegistration() {
  useEffect(() => {
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      void navigator.serviceWorker.register("/sw.js");
    }
  }, []);
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 15_000 } } }),
  );
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <OfflineBanner />
        <ServiceWorkerRegistration />
        {children}
      </I18nProvider>
    </QueryClientProvider>
  );
}
