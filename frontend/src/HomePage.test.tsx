import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import App from "./App";
import { createMockApi } from "./data/mockApi";
import { renderWithApp } from "./testUtils";

const open = (route = "/") => renderWithApp(<App />, createMockApi(), route);

describe("Home", () => {
  test("shows three intent actions with descriptions", () => {
    open();
    for (const name of ["Capture", "Reflect", "Preserve"]) {
      expect(screen.getByRole("link", { name })).toBeInTheDocument();
    }
    expect(screen.getAllByText(/\.$/)).toHaveLength(3);
  });

  test.each([
    ["Capture", "Type: Idea"],
    ["Reflect", "Type: Journal"],
    ["Preserve", "Type: Memory"],
  ])("%s opens the editor with %s", async (name, typeText) => {
    open();
    fireEvent.click(screen.getByRole("link", { name }));
    expect(await screen.findByText(typeText)).toBeInTheDocument();
  });

  test("Reflect shows journal fields and Preserve shows memory fields", async () => {
    open();
    fireEvent.click(screen.getByRole("link", { name: "Reflect" }));
    for (const l of ["Mood", "Prompt", "Retrospective"]) expect(await screen.findByLabelText(l)).toBeInTheDocument();
  });

  test("Preserve shows when and where", async () => {
    open();
    fireEvent.click(screen.getByRole("link", { name: "Preserve" }));
    expect(await screen.findByLabelText("When")).toBeInTheDocument();
    expect(screen.getByLabelText("Where")).toBeInTheDocument();
  });

  test("Capture switch defaults to Idea and offers Reference and Plan", () => {
    open();
    expect(screen.getByRole("button", { name: "Idea" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Reference" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getAllByRole("group", { name: "Capture as" })).toHaveLength(1);
  });

  test.each([
    ["Idea", "Type: Idea"],
    ["Reference", "Type: Reference"],
    ["Plan", "Type: Plan"],
  ])("Capture switch %s opens %s", async (name, typeText) => {
    open();
    fireEvent.click(screen.getByRole("button", { name }));
    expect(await screen.findByText(typeText)).toBeInTheDocument();
  });

  test("Capture link targets idea by default; Reflect and Preserve have no switch", () => {
    open();
    expect(screen.getByRole("link", { name: "Capture" })).toHaveAttribute("href", "/notes/new?type=idea");
    expect(screen.getByRole("link", { name: "Reflect" })).toHaveAttribute("href", "/notes/new?type=journal");
    expect(screen.getByRole("link", { name: "Preserve" })).toHaveAttribute("href", "/notes/new?type=memory");
    expect(screen.getAllByRole("group")).toHaveLength(1);
  });
});

describe("/notes/new", () => {
  test.each(["/notes/new", "/notes/new?type=banana"])("%s falls back to Idea", async (route) => {
    open(route);
    expect(await screen.findByText("Type: Idea")).toBeInTheDocument();
  });

  test("lands on Home after a successful save", async () => {
    const api = createMockApi();
    await api.createCollection("Work", null);
    renderWithApp(<App />, api, "/notes/new?type=idea");
    await screen.findByLabelText("Collection");
    fireEvent.change(screen.getByLabelText("Body"), { target: { value: "hi" } });
    const select = screen.getByLabelText("Collection") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: select.options[1].value } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Home" })).toBeInTheDocument());
  });
});
