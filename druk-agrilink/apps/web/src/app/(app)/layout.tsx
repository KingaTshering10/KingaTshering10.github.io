"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/i18n";
import { api, hasSession, logout, type Me } from "@/lib/api";

function useNavItems(role: Me["role"] | undefined) {
  const { t } = useI18n();
  if (!role) return [];
  const items: Record<Me["role"], [string, string][]> = {
    farmer: [
      ["/dashboard", t.nav.dashboard],
      ["/harvests", t.nav.myHarvests],
      ["/opportunities", t.nav.opportunities],
      ["/collections", t.nav.collections],
      ["/payments", t.nav.payments],
      ["/notifications", t.nav.notifications],
      ["/settings", t.nav.profile],
    ],
    coordinator: [
      ["/dashboard", t.nav.overview],
      ["/farmers", t.nav.farmers],
      ["/harvests", t.nav.harvestSupply],
      ["/orders", t.nav.buyerOrders],
      ["/proposals", t.nav.matchProposals],
      ["/collections", t.nav.collections],
      ["/shipments", t.nav.shipments],
      ["/payments", t.nav.payments],
      ["/disputes", t.nav.disputes],
      ["/settings", t.nav.settings],
    ],
    buyer: [
      ["/dashboard", t.nav.procurement],
      ["/orders/new", t.nav.createOrder],
      ["/orders", t.nav.activeOrders],
      ["/proposals", t.nav.matchProposals],
      ["/deliveries", t.nav.deliveries],
      ["/payments", t.nav.payments],
      ["/settings", t.nav.organization],
    ],
    transporter: [
      ["/dashboard", t.nav.dashboard],
      ["/trips", t.nav.assignedTrips],
      ["/vehicles", t.nav.vehicles],
      ["/payments", t.nav.payments],
      ["/settings", t.nav.profile],
    ],
    admin: [
      ["/dashboard", t.nav.operations],
      ["/admin/verification", t.nav.verification],
      ["/admin/users", t.nav.users],
      ["/admin/audit", t.nav.auditLog],
      ["/analytics", t.nav.analytics],
      ["/disputes", t.nav.disputes],
      ["/settings", t.nav.settings],
    ],
  };
  return items[role];
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!hasSession()) router.replace("/login");
  }, [router]);

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/users/me"),
  });
  const { data: unread } = useQuery({
    queryKey: ["unread"],
    queryFn: () => api<{ unread: number }>("/notifications/unread-count"),
    refetchInterval: 60_000,
  });

  const navItems = useNavItems(me?.role);

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="border-b border-earth-100 bg-white md:min-h-screen md:w-60 md:border-b-0 md:border-r">
        <div className="flex items-center justify-between p-4">
          <Link href="/dashboard" className="flex items-center gap-2 font-bold text-field-800">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/icon.svg" alt="" className="h-8 w-8" />
            {t.appName}
          </Link>
        </div>
        <nav
          aria-label="Main navigation"
          className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-4"
        >
          {navItems.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? "page" : undefined}
              className={`whitespace-nowrap rounded-lg px-3 py-2.5 text-sm font-medium ${
                pathname === href
                  ? "bg-field-100 text-field-800"
                  : "text-earth-700 hover:bg-earth-50"
              }`}
            >
              {label}
              {href === "/notifications" && unread && unread.unread > 0 ? (
                <span className="ml-2 rounded-full bg-field-600 px-2 py-0.5 text-xs text-white">
                  {unread.unread}
                </span>
              ) : null}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2 border-t border-earth-100 p-4">
          <LanguageSwitcher />
          <button
            onClick={async () => {
              await logout();
              router.push("/login");
            }}
            className="min-h-11 rounded-lg px-3 text-sm font-medium text-earth-700 hover:bg-earth-50"
          >
            {t.nav.logout}
          </button>
        </div>
      </aside>
      <main className="flex-1 p-4 md:p-8">{children}</main>
    </div>
  );
}
