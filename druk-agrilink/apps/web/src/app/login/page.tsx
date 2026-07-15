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
import { ApiRequestError, login } from "@/lib/api";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
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
      <h1 className="mb-6 text-2xl font-bold">{t.auth.login}</h1>
      {serverError ? (
        <div className="mb-4">
          <ErrorState message={serverError} />
        </div>
      ) : null}
      <form onSubmit={onSubmit} noValidate>
        <Field label={t.auth.email} htmlFor="email" error={errors.email?.message}>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className={inputClass}
            {...register("email")}
          />
        </Field>
        <Field label={t.auth.password} htmlFor="password" error={errors.password?.message}>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className={inputClass}
            {...register("password")}
          />
        </Field>
        <Button type="submit" disabled={isSubmitting} className="w-full">
          {isSubmitting ? t.common.loading : t.auth.login}
        </Button>
      </form>
      <p className="mt-4 text-sm text-earth-700">
        {t.auth.needAccount}{" "}
        <Link href="/register" className="font-semibold text-field-700 underline">
          {t.auth.register}
        </Link>
      </p>
    </main>
  );
}
