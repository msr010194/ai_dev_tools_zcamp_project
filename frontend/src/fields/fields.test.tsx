import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, test } from "vitest";
import JournalFieldsForm from "./JournalFieldsForm";
import PlanFieldsForm from "./PlanFieldsForm";
import TypeFields from "./TypeFields";
import { emptyFields, type JournalFields, type PlanFields } from "./types";

function renderType(type: "journal" | "idea" | "reference" | "plan" | "memory") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const props: any = { type, value: emptyFields(type), onChange: () => {} };
  return render(<TypeFields {...props} />);
}

const labelsFor = (type: Parameters<typeof renderType>[0]) => {
  const { container, unmount } = renderType(type);
  const labels = Array.from(container.querySelectorAll("label, legend")).map((l) =>
    Array.from(l.childNodes)
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent)
      .join("")
      .trim(),
  );
  unmount();
  return labels;
};

describe("each Type shows only its own fields", () => {
  test("journal", () => {
    expect(labelsFor("journal")).toEqual(["Mood", "Prompt", "Retrospective"]);
  });
  test("idea has no extra fields", () => {
    expect(labelsFor("idea")).toEqual([]);
  });
  test("reference", () => {
    expect(labelsFor("reference")).toEqual(["Sub-kind", "Link"]);
  });
  test("plan", () => {
    expect(labelsFor("plan")).toEqual(["Target date", "State", "Checklist"]);
  });
  test("memory", () => {
    expect(labelsFor("memory")).toEqual(["When", "Where"]);
  });
});

describe("JournalFieldsForm", () => {
  function Harness({ locked }: { locked: boolean }) {
    const [v, setV] = useState<JournalFields>({ ...emptyFields("journal"), prompt: "Why?" });
    return <JournalFieldsForm value={v} onChange={setV} promptLocked={locked} />;
  }

  test("prompt is read-only when locked", () => {
    render(<Harness locked />);
    expect(screen.getByLabelText("Prompt")).toHaveAttribute("readonly");
  });

  test("prompt is editable when not locked", () => {
    render(<Harness locked={false} />);
    expect(screen.getByLabelText("Prompt")).not.toHaveAttribute("readonly");
  });

  test("period selector only appears for retrospectives", () => {
    render(<Harness locked={false} />);
    expect(screen.queryByLabelText("Period")).toBeNull();
    fireEvent.click(screen.getByLabelText("Retrospective"));
    fireEvent.change(screen.getByLabelText("Period"), { target: { value: "monthly" } });
    expect(screen.getByLabelText("Period")).toHaveValue("monthly");
  });
});

describe("PlanFieldsForm checklist", () => {
  function Harness() {
    const [v, setV] = useState<PlanFields>(emptyFields("plan"));
    return <PlanFieldsForm value={v} onChange={setV} />;
  }

  test("adds, edits, checks and removes items", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("Add item"));
    fireEvent.change(screen.getByLabelText("Item 1 text"), { target: { value: "Buy milk" } });
    fireEvent.click(screen.getByLabelText("Item 1 done"));
    expect(screen.getByLabelText("Item 1 text")).toHaveValue("Buy milk");
    expect(screen.getByLabelText("Item 1 done")).toBeChecked();
    fireEvent.click(screen.getByLabelText("Remove item 1"));
    expect(screen.queryByLabelText("Item 1 text")).toBeNull();
  });
});
