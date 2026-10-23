"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, ErrorState, Field, inputClass, Loading } from "@/components/ui";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/i18n";
import { api, ApiRequestError, type Me } from "@/lib/api";

function FarmerOnboarding() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [farmName, setFarmName] = useState("");
  const [dzongkhag, setDzongkhag] = useState("");
  const [groupId, setGroupId] = useState("");

  const { data: profile } = useQuery({
    queryKey: ["farmer-profile"],
    queryFn: () =>
      api<{
        id: string;
        display_name: string;
        verification_status: string;
        membership_status: string;
      }>("/farmers/profile").catch(() => null),
  });
  const { data: groups } = useQuery({
    queryKey: ["groups"],
    queryFn: () => api<{ id: string; name: string; dzongkhag: string }[]>("/farmer-groups"),
  });
  const { data: farms } = useQuery({
    queryKey: ["farms"],
    queryFn: () => api<{ id: string; farm_name: string }[]>("/farms").catch(() => []),
  });

  const createProfile = useMutation({
    mutationFn: () =>
      api("/farmers/profile", { method: "POST", body: { display_name: displayName } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["farmer-profile"] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });
  const createFarm = useMutation({
    mutationFn: () => api("/farms", { method: "POST", body: { farm_name: farmName, dzongkhag } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["farms"] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });
  const requestMembership = useMutation({
    mutationFn: () =>
      api("/farmers/membership-request", { method: "POST", body: { farmer_group_id: groupId } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["farmer-profile"] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  return (
    <Card title="Farmer profile" className="mb-6">
      {error ? <ErrorState message={error} /> : null}
      {profile ? (
        <p className="mb-3 text-sm">
          {profile.display_name} · verification: <strong>{profile.verification_status}</strong> ·
          membership: <strong>{profile.membership_status}</strong>
        </p>
      ) : (
        <form
          className="mb-4"
          onSubmit={(event) => {
            event.preventDefault();
            createProfile.mutate();
          }}
        >
          <Field label="Display name" htmlFor="display_name">
            <input
              id="display_name"
              required
              minLength={2}
              className={inputClass}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </Field>
          <Button type="submit">{t.common.save}</Button>
        </form>
      )}

      {profile ? (
        <>
          <h3 className="mb-2 text-sm font-semibold">Farms ({farms?.length ?? 0})</h3>
          <form
            className="mb-4 grid grid-cols-2 items-end gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              createFarm.mutate();
            }}
          >
            <Field label="Farm name" htmlFor="farm_name">
              <input
                id="farm_name"
                required
                minLength={2}
                className={inputClass}
                value={farmName}
                onChange={(e) => setFarmName(e.target.value)}
              />
            </Field>
            <Field label="Dzongkhag" htmlFor="farm_dzongkhag">
              <input
                id="farm_dzongkhag"
                required
                minLength={2}
                className={inputClass}
                value={dzongkhag}
                onChange={(e) => setDzongkhag(e.target.value)}
              />
            </Field>
            <Button type="submit" className="col-span-2">
              Add farm
            </Button>
          </form>

          {profile.membership_status === "none" ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                requestMembership.mutate();
              }}
            >
              <Field label="Join a farmer group" htmlFor="group">
                <select
                  id="group"
                  required
                  className={inputClass}
                  value={groupId}
                  onChange={(e) => setGroupId(e.target.value)}
                >
                  <option value="">—</option>
                  {groups?.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name} ({group.dzongkhag})
                    </option>
                  ))}
                </select>
              </Field>
              <Button type="submit">Request membership</Button>
            </form>
          ) : null}
        </>
      ) : null}
    </Card>
  );
}

function BuyerOnboarding() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({ name: "", type: "school" });

  const { data: org } = useQuery({
    queryKey: ["buyer-org"],
    queryFn: () =>
      api<{ name: string; verification_status: string }>("/buyers/organization").catch(() => null),
  });
  const create = useMutation({
    mutationFn: () =>
      api("/buyers/organization", {
        method: "POST",
        body: { name: values.name, organization_type: values.type },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["buyer-org"] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  return (
    <Card title="Buyer organization" className="mb-6">
      {error ? <ErrorState message={error} /> : null}
      {org ? (
        <p className="text-sm">
          {org.name} · verification: <strong>{org.verification_status}</strong>
          {org.verification_status !== "verified" ? (
            <span className="mt-2 block rounded bg-maize-100 p-2 text-xs">
              {t.order.verificationPending}
            </span>
          ) : null}
        </p>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            create.mutate();
          }}
        >
          <Field label="Organization name" htmlFor="org_name">
            <input
              id="org_name"
              required
              minLength={2}
              className={inputClass}
              value={values.name}
              onChange={(e) => setValues({ ...values, name: e.target.value })}
            />
          </Field>
          <Field label="Organization type" htmlFor="org_type">
            <select
              id="org_type"
              className={inputClass}
              value={values.type}
              onChange={(e) => setValues({ ...values, type: e.target.value })}
            >
              {[
                "hotel",
                "restaurant",
                "school",
                "hospital",
                "retailer",
                "wholesaler",
                "processor",
                "government_institution",
                "exporter",
                "other",
              ].map((type) => (
                <option key={type} value={type}>
                  {type.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </Field>
          <Button type="submit">{t.common.save}</Button>
        </form>
      )}
    </Card>
  );
}

function TransporterOnboarding() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");

  const { data: provider } = useQuery({
    queryKey: ["provider"],
    queryFn: () =>
      api<{ organization_name: string; verification_status: string }>(
        "/transport-providers/me",
      ).catch(() => null),
  });
  const create = useMutation({
    mutationFn: () =>
      api("/transport-providers", { method: "POST", body: { organization_name: name } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["provider"] }),
    onError: (err) => setError(err instanceof ApiRequestError ? err.message : t.common.error),
  });

  return (
    <Card title="Transport provider" className="mb-6">
      {error ? <ErrorState message={error} /> : null}
      {provider ? (
        <p className="text-sm">
          {provider.organization_name} · verification:{" "}
          <strong>{provider.verification_status}</strong>
        </p>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            create.mutate();
          }}
        >
          <Field label="Company name" htmlFor="provider_name">
            <input
              id="provider_name"
              required
              minLength={2}
              className={inputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <Button type="submit">{t.common.save}</Button>
        </form>
      )}
    </Card>
  );
}

export default function SettingsPage() {
  const { t } = useI18n();
  const [deactivationReason, setDeactivationReason] = useState("");
  const [deactivationSent, setDeactivationSent] = useState(false);
  const { data: me, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/users/me"),
  });
  const { data: prefs } = useQuery({
    queryKey: ["notification-prefs"],
    queryFn: () =>
      api<{ email_enabled: boolean; sms_enabled: boolean; push_enabled: boolean; note: string }>(
        "/users/me/notification-preferences",
      ),
  });
  const queryClient = useQueryClient();
  const savePrefs = useMutation({
    mutationFn: (body: Record<string, boolean>) =>
      api("/users/me/notification-preferences", { method: "PUT", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notification-prefs"] }),
  });
  const requestDeactivation = useMutation({
    mutationFn: () =>
      api("/users/me/deactivation-request", {
        method: "POST",
        body: { reason: deactivationReason },
      }),
    onSuccess: () => setDeactivationSent(true),
  });

  if (isLoading || !me) return <Loading label={t.common.loading} />;

  return (
    <div className="max-w-xl">
      <h1 className="mb-6 text-2xl font-bold">{t.nav.settings}</h1>

      <Card title={t.auth.language} className="mb-6">
        <LanguageSwitcher />
      </Card>

      {me.role === "farmer" ? <FarmerOnboarding /> : null}
      {me.role === "buyer" ? <BuyerOnboarding /> : null}
      {me.role === "transporter" ? <TransporterOnboarding /> : null}

      {prefs ? (
        <Card title={t.nav.notifications} className="mb-6">
          <p className="mb-2 text-xs text-earth-700">{prefs.note}</p>
          {(["email_enabled", "sms_enabled", "push_enabled"] as const).map((key) => (
            <label key={key} className="mb-2 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-5 w-5"
                checked={prefs[key]}
                onChange={(event) =>
                  savePrefs.mutate({
                    email_enabled: prefs.email_enabled,
                    sms_enabled: prefs.sms_enabled,
                    push_enabled: prefs.push_enabled,
                    [key]: event.target.checked,
                  })
                }
              />
              {key.replace("_enabled", "").toUpperCase()}
            </label>
          ))}
        </Card>
      ) : null}

      <Card title="Account">
        <p className="mb-2 text-sm">
          {me.email} · {me.role}
        </p>
        {deactivationSent ? (
          <p className="rounded bg-field-50 p-2 text-sm">
            Deactivation request received. An administrator will review it.
          </p>
        ) : (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              requestDeactivation.mutate();
            }}
          >
            <Field label="Request account deactivation (reason)" htmlFor="deactivation">
              <input
                id="deactivation"
                required
                minLength={3}
                className={inputClass}
                value={deactivationReason}
                onChange={(e) => setDeactivationReason(e.target.value)}
              />
            </Field>
            <Button variant="danger" type="submit">
              Request deactivation
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
