import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  Button,
  ConfirmDialog,
  Empty,
  ErrorState,
  Field,
  Loading,
  StatusBadge,
} from "@/components/ui";

describe("StatusBadge", () => {
  it("communicates status with text, not colour alone", () => {
    render(<StatusBadge status="partially_allocated" />);
    expect(screen.getByText("partially allocated")).toBeInTheDocument();
  });
});

describe("Field", () => {
  it("associates label and announces errors via role=alert", () => {
    render(
      <Field label="Quantity" htmlFor="qty" error="Quantity is required">
        <input id="qty" />
      </Field>,
    );
    expect(screen.getByLabelText("Quantity")).toBeInTheDocument();
    expect(screen.getByRole("alert").textContent).toBe("Quantity is required");
  });
});

describe("state components", () => {
  it("renders loading, empty, and error states", () => {
    render(
      <>
        <Loading label="Loading…" />
        <Empty label="Nothing here yet." />
        <ErrorState message="Something went wrong." />
      </>,
    );
    expect(screen.getByRole("status").textContent).toBe("Loading…");
    expect(screen.getByText("Nothing here yet.")).toBeInTheDocument();
    expect(screen.getByRole("alert").textContent).toBe("Something went wrong.");
  });
});

describe("ConfirmDialog", () => {
  it("requires explicit confirmation for consequential actions", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open
        message="Are you sure?"
        confirmLabel="Confirm"
        cancelLabel="Cancel"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Confirm"));
    expect(onConfirm).toHaveBeenCalled();
  });
});

describe("Button", () => {
  it("meets minimum touch-target height", () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole("button").className).toContain("min-h-11");
  });
});
