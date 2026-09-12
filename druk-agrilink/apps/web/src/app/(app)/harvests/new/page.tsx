"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, ErrorState, Field, inputClass } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api, ApiRequestError } from "@/lib/api";
import { saveDraft } from "@/lib/offline";

const schema = z
  .object({
    farm_id: z.string().uuid("Select a farm"),
    product_id: z.string().uuid("Select a product"),
    forecast_quantity: z.coerce.number().positive(),
    unit: z.enum(["kg", "crate", "bundle", "piece"]),
    harvest_start_date: z.string().min(1),
    harvest_end_date: z.string().min(1),
    minimum_unit_price: z.coerce.number().min(0),
    confidence_level: z.enum(["low", "medium", "high"]),
    packaging_type: z.string().max(60).optional().or(z.literal("")),
    notes: z.string().optional().or(z.literal("")),
    save_as_draft: z.boolean(),
  })
  .refine((values) => values.harvest_end_date >= values.harvest_start_date, {
    message: "End date must not be before start date",
    path: ["harvest_end_date"],
  });
type FormValues = z.infer<typeof schema>;

export default function NewHarvestPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [savedOffline, setSavedOffline] = useState(false);

  const { data: farms } = useQuery({
    queryKey: ["farms"],
    queryFn: () => api<{ id: string; farm_name: string }[]>("/farms"),
  });
  const { data: products } = useQuery({
    queryKey: ["products"],
    queryFn: () => api<{ items: { id: string; name: string }[] }>("/products?page_size=100"),
  });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { unit: "kg", confidence_level: "medium", save_as_draft: false },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const payload = {
      ...values,
      forecast_quantity: String(values.forecast_quantity),
      minimum_unit_price: String(values.minimum_unit_price),
      packaging_type: values.packaging_type || null,
      notes: values.notes || null,
    };
    try {
      await api("/harvest-listings", { method: "POST", body: payload });
      router.push("/harvests");
    } catch (error) {
      if (
        !navigator.onLine ||
        (error instanceof TypeError && !(error instanceof ApiRequestError))
      ) {
        // offline: queue the draft for sync
        await saveDraft({
          id: crypto.randomUUID(),
          kind: "harvest_listing_create",
          path: "/harvest-listings",
          method: "POST",
          payload: { ...payload, save_as_draft: true },
          createdAt: new Date().toISOString(),
          status: "queued",
        });
        setSavedOffline(true);
        return;
      }
      setServerError(error instanceof ApiRequestError ? error.message : t.common.error);
    }
  });

  if (savedOffline) {
    return (
      <div className="max-w-lg">
        <h1 className="mb-4 text-2xl font-bold">{t.harvest.newListing}</h1>
        <p className="rounded-lg border border-maize-100 bg-maize-100 p-4 text-sm">
          {t.harvest.savedOffline}
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-lg">
      <h1 className="mb-6 text-2xl font-bold">{t.harvest.newListing}</h1>
      {serverError ? (
        <div className="mb-4">
          <ErrorState message={serverError} />
        </div>
      ) : null}
      <form onSubmit={onSubmit} noValidate>
        <Field label={t.harvest.farm} htmlFor="farm_id" error={errors.farm_id?.message}>
          <select id="farm_id" className={inputClass} {...register("farm_id")}>
            <option value="">—</option>
            {farms?.map((farm) => (
              <option key={farm.id} value={farm.id}>
                {farm.farm_name}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t.harvest.product} htmlFor="product_id" error={errors.product_id?.message}>
          <select id="product_id" className={inputClass} {...register("product_id")}>
            <option value="">—</option>
            {products?.items.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field
            label={t.harvest.forecastQuantity}
            htmlFor="forecast_quantity"
            error={errors.forecast_quantity?.message}
          >
            <input
              id="forecast_quantity"
              type="number"
              step="0.01"
              min="0"
              inputMode="decimal"
              className={inputClass}
              {...register("forecast_quantity")}
            />
          </Field>
          <Field label={t.common.unit} htmlFor="unit">
            <select id="unit" className={inputClass} {...register("unit")}>
              <option value="kg">kg</option>
              <option value="crate">crate</option>
              <option value="bundle">bundle</option>
              <option value="piece">piece</option>
            </select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field
            label={t.harvest.windowStart}
            htmlFor="harvest_start_date"
            error={errors.harvest_start_date?.message}
          >
            <input
              id="harvest_start_date"
              type="date"
              className={inputClass}
              {...register("harvest_start_date")}
            />
          </Field>
          <Field
            label={t.harvest.windowEnd}
            htmlFor="harvest_end_date"
            error={errors.harvest_end_date?.message}
          >
            <input
              id="harvest_end_date"
              type="date"
              className={inputClass}
              {...register("harvest_end_date")}
            />
          </Field>
        </div>
        <Field
          label={t.harvest.minPrice}
          htmlFor="minimum_unit_price"
          error={errors.minimum_unit_price?.message}
        >
          <input
            id="minimum_unit_price"
            type="number"
            step="0.01"
            min="0"
            inputMode="decimal"
            className={inputClass}
            {...register("minimum_unit_price")}
          />
        </Field>
        <Field label={t.harvest.confidence} htmlFor="confidence_level">
          <select id="confidence_level" className={inputClass} {...register("confidence_level")}>
            <option value="low">{t.harvest.confidenceLow}</option>
            <option value="medium">{t.harvest.confidenceMedium}</option>
            <option value="high">{t.harvest.confidenceHigh}</option>
          </select>
        </Field>
        <Field label={t.harvest.packaging} htmlFor="packaging_type">
          <input id="packaging_type" className={inputClass} {...register("packaging_type")} />
        </Field>
        <Field label={t.harvest.notes} htmlFor="notes">
          <textarea id="notes" rows={2} className={inputClass} {...register("notes")} />
        </Field>
        <label className="mb-4 flex items-center gap-2 text-sm">
          <input type="checkbox" className="h-5 w-5" {...register("save_as_draft")} />
          {t.harvest.saveDraft}
        </label>
        <Button type="submit" disabled={isSubmitting} className="w-full">
          {isSubmitting ? t.common.loading : t.common.submit}
        </Button>
      </form>
    </div>
  );
}
