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

const schema = z
  .object({
    delivery_location_id: z.string().uuid("Select a delivery location"),
    required_delivery_date: z.string().min(1),
    product_id: z.string().uuid("Select a product"),
    required_quantity: z.coerce.number().positive(),
    unit: z.enum(["kg", "crate", "bundle", "piece"]),
    offered_unit_price: z.coerce.number().positive(),
    maximum_unit_price: z.coerce.number().positive().optional().or(z.nan()),
    minimum_grade_id: z.string().optional().or(z.literal("")),
    packaging_requirement: z.string().max(120).optional().or(z.literal("")),
    payment_terms: z.string().max(120).optional().or(z.literal("")),
    special_instructions: z.string().optional().or(z.literal("")),
    save_as_draft: z.boolean(),
  })
  .refine(
    (values) =>
      Number.isNaN(values.maximum_unit_price ?? NaN) ||
      (values.maximum_unit_price ?? 0) >= values.offered_unit_price,
    { message: "Maximum price must be at least the offered price", path: ["maximum_unit_price"] },
  );
type FormValues = z.infer<typeof schema>;

export default function NewOrderPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const { data: locations } = useQuery({
    queryKey: ["delivery-locations"],
    queryFn: () =>
      api<{ items: { id: string; name: string; dzongkhag: string }[] }>(
        "/locations?location_type=delivery_point&page_size=100",
      ),
  });
  const { data: products } = useQuery({
    queryKey: ["products"],
    queryFn: () => api<{ items: { id: string; name: string }[] }>("/products?page_size=100"),
  });
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { unit: "kg", save_as_draft: true },
  });
  const productId = watch("product_id");
  const { data: grades } = useQuery({
    queryKey: ["grades", productId],
    queryFn: () =>
      api<{ id: string; code: string; name: string }[]>(`/products/${productId}/grades`),
    enabled: Boolean(productId),
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await api("/buyer-orders", {
        method: "POST",
        body: {
          delivery_location_id: values.delivery_location_id,
          required_delivery_date: values.required_delivery_date,
          payment_terms: values.payment_terms || null,
          special_instructions: values.special_instructions || null,
          save_as_draft: values.save_as_draft,
          items: [
            {
              product_id: values.product_id,
              required_quantity: String(values.required_quantity),
              unit: values.unit,
              offered_unit_price: String(values.offered_unit_price),
              maximum_unit_price: Number.isNaN(values.maximum_unit_price ?? NaN)
                ? null
                : String(values.maximum_unit_price),
              minimum_grade_id: values.minimum_grade_id || null,
              packaging_requirement: values.packaging_requirement || null,
            },
          ],
        },
      });
      router.push("/orders");
    } catch (error) {
      setServerError(error instanceof ApiRequestError ? error.message : t.common.error);
    }
  });

  return (
    <div className="max-w-lg">
      <h1 className="mb-6 text-2xl font-bold">{t.order.newOrder}</h1>
      {serverError ? (
        <div className="mb-4">
          <ErrorState message={serverError} />
        </div>
      ) : null}
      <form onSubmit={onSubmit} noValidate>
        <Field
          label={t.order.deliveryLocation}
          htmlFor="delivery_location_id"
          error={errors.delivery_location_id?.message}
        >
          <select
            id="delivery_location_id"
            className={inputClass}
            {...register("delivery_location_id")}
          >
            <option value="">—</option>
            {locations?.items.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name} ({location.dzongkhag})
              </option>
            ))}
          </select>
        </Field>
        <Field
          label={t.order.deliveryDate}
          htmlFor="required_delivery_date"
          error={errors.required_delivery_date?.message}
        >
          <input
            id="required_delivery_date"
            type="date"
            className={inputClass}
            {...register("required_delivery_date")}
          />
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
            label={t.order.requiredQuantity}
            htmlFor="required_quantity"
            error={errors.required_quantity?.message}
          >
            <input
              id="required_quantity"
              type="number"
              step="0.01"
              min="0"
              inputMode="decimal"
              className={inputClass}
              {...register("required_quantity")}
            />
          </Field>
          <Field label={t.common.unit} htmlFor="unit">
            <select id="unit" className={inputClass} {...register("unit")}>
              <option value="kg">kg</option>
              <option value="crate">crate</option>
            </select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field
            label={t.order.offeredPrice}
            htmlFor="offered_unit_price"
            error={errors.offered_unit_price?.message}
          >
            <input
              id="offered_unit_price"
              type="number"
              step="0.01"
              min="0"
              inputMode="decimal"
              className={inputClass}
              {...register("offered_unit_price")}
            />
          </Field>
          <Field
            label={t.order.maxPrice}
            htmlFor="maximum_unit_price"
            error={errors.maximum_unit_price?.message}
          >
            <input
              id="maximum_unit_price"
              type="number"
              step="0.01"
              min="0"
              inputMode="decimal"
              className={inputClass}
              {...register("maximum_unit_price")}
            />
          </Field>
        </div>
        <Field label={t.order.minGrade} htmlFor="minimum_grade_id">
          <select id="minimum_grade_id" className={inputClass} {...register("minimum_grade_id")}>
            <option value="">—</option>
            {grades?.map((grade) => (
              <option key={grade.id} value={grade.id}>
                {grade.code} — {grade.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t.order.packagingReq} htmlFor="packaging_requirement">
          <input
            id="packaging_requirement"
            className={inputClass}
            {...register("packaging_requirement")}
          />
        </Field>
        <Field label="Payment terms" htmlFor="payment_terms">
          <input id="payment_terms" className={inputClass} {...register("payment_terms")} />
        </Field>
        <Field label={t.order.instructions} htmlFor="special_instructions">
          <textarea
            id="special_instructions"
            rows={2}
            className={inputClass}
            {...register("special_instructions")}
          />
        </Field>
        <label className="mb-4 flex items-center gap-2 text-sm">
          <input type="checkbox" className="h-5 w-5" {...register("save_as_draft")} />
          {t.order.saveDraft}
        </label>
        <Button type="submit" disabled={isSubmitting} className="w-full">
          {isSubmitting ? t.common.loading : t.common.submit}
        </Button>
      </form>
    </div>
  );
}
