"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Button, ErrorState, Field, inputClass } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api, ApiRequestError, login } from "@/lib/api";

const schema = z.object({
  email: z.string().email(),
  password: z
    .string()
    .min(10)
    .regex(/[a-z]/, "Needs a lower-case letter")
    .regex(/[A-Z]/, "Needs an upper-case letter")
    .regex(/\d/, "Needs a digit"),
  role: z.enum(["farmer", "coordinator", "buyer", "transporter"]),
  phone: z.string().max(32).optional().or(z.literal("")),
  preferred_language: z.enum(["en", "dz"]),
});
type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { role: "farmer", preferred_language: "en" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await api("/auth/register", {
        method: "POST",
        body: { ...values, phone: values.phone || null },
      });
      await login(values.email, values.password);
      router.push("/dashboard");
    } catch (error) {
      setServerError(error instanceof ApiRequestError ? error.message : t.common.error);
    }
  });

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
      <div className="mb-6 flex items-center justify-between">
        <Link href="/" className="font-bold text-field-800">
          {t.appName}
        </Link>
        <LanguageSwitcher />
      </div>
      <h1 className="mb-6 text-2xl font-bold">{t.auth.register}</h1>
      {serverError ? (
        <div className="mb-4">
          <ErrorState message={serverError} />
        </div>
      ) : null}
      <form onSubmit={onSubmit} noValidate>
        <Field label={t.auth.role} htmlFor="role" error={errors.role?.message}>
          <select id="role" className={inputClass} {...register("role")}>
            <option value="farmer">{t.auth.roleFarmer}</option>
            <option value="coordinator">{t.auth.roleCoordinator}</option>
            <option value="buyer">{t.auth.roleBuyer}</option>
            <option value="transporter">{t.auth.roleTransporter}</option>
          </select>
        </Field>
        <Field label={t.auth.email} htmlFor="email" error={errors.email?.message}>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className={inputClass}
            {...register("email")}
          />
        </Field>
        <Field
          label={t.auth.password}
          htmlFor="password"
          hint={t.auth.passwordHint}
          error={errors.password?.message}
        >
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            className={inputClass}
            {...register("password")}
          />
        </Field>
        <Field label={t.auth.phone} htmlFor="phone" error={errors.phone?.message}>
          <input
            id="phone"
            type="tel"
            autoComplete="tel"
            className={inputClass}
            {...register("phone")}
          />
        </Field>
        <Field label={t.auth.language} htmlFor="preferred_language">
          <select
            id="preferred_language"
            className={inputClass}
            {...register("preferred_language")}
          >
            <option value="en">English</option>
            <option value="dz">རྫོང་ཁ (Dzongkha)</option>
          </select>
        </Field>
        <Button type="submit" disabled={isSubmitting} className="w-full">
          {isSubmitting ? t.common.loading : t.auth.register}
        </Button>
      </form>
      <p className="mt-4 text-sm text-earth-700">
        {t.auth.haveAccount}{" "}
        <Link href="/login" className="font-semibold text-field-700 underline">
          {t.auth.login}
        </Link>
      </p>
    </main>
  );
}
