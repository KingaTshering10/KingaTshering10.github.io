"use client";

/** Small accessible UI kit: buttons, cards, badges, form fields, states. */

import { forwardRef } from "react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export const Button = forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }
>(function Button({ variant = "primary", className, ...props }, ref) {
  return (
    <button
      ref={ref}
      className={cx(
        "inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-field-600",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-field-600 text-white hover:bg-field-700",
        variant === "secondary" &&
          "border border-field-600 bg-white text-field-700 hover:bg-field-50",
        variant === "danger" && "bg-red-700 text-white hover:bg-red-800",
        className,
      )}
      {...props}
    />
  );
});

export function Card({
  title,
  children,
  className,
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("rounded-xl border border-earth-100 bg-white p-4 shadow-sm", className)}>
      {title ? <h2 className="mb-3 text-base font-semibold text-field-800">{title}</h2> : null}
      {children}
    </section>
  );
}

const STATUS_STYLES: Record<string, string> = {
  // status is always shown as label text, never colour alone
  draft: "bg-earth-50 text-earth-700 border-earth-100",
  forecast: "bg-maize-100 text-maize-700 border-maize-100",
  confirmed: "bg-field-100 text-field-700 border-field-100",
  published: "bg-field-100 text-field-700 border-field-100",
  approved: "bg-field-100 text-field-800 border-field-100",
  completed: "bg-field-100 text-field-800 border-field-100",
  paid: "bg-field-100 text-field-800 border-field-100",
  rejected: "bg-red-50 text-red-800 border-red-100",
  cancelled: "bg-red-50 text-red-800 border-red-100",
  overdue: "bg-red-50 text-red-800 border-red-100",
  disputed: "bg-red-50 text-red-800 border-red-100",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-earth-50 text-earth-700 border-earth-100";
  return (
    <span
      className={cx("inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium", style)}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-4">
      <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-field-800">
        {label}
      </label>
      {children}
      {hint && !error ? <p className="mt-1 text-xs text-earth-700">{hint}</p> : null}
      {error ? (
        <p role="alert" className="mt-1 text-xs font-medium text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export const inputClass =
  "block w-full min-h-11 rounded-lg border border-earth-100 bg-white px-3 py-2 text-sm " +
  "focus:border-field-600 focus:outline-none focus:ring-1 focus:ring-field-600";

export function Loading({ label }: { label: string }) {
  return (
    <p role="status" className="py-8 text-center text-sm text-earth-700">
      {label}
    </p>
  );
}

export function Empty({ label }: { label: string }) {
  return (
    <p className="rounded-lg border border-dashed border-earth-100 py-8 text-center text-sm text-earth-700">
      {label}
    </p>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      {message}
    </p>
  );
}

export function ConfirmDialog({
  open,
  message,
  confirmLabel,
  cancelLabel,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-lg">
        <p className="mb-4 text-sm text-field-800">{message}</p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}
