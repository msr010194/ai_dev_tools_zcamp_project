import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import TagsPage from "./TagsPage";
import { createMockApi } from "./data/mockApi";
import type { DataApi } from "./data/types";
import { renderWithApp } from "./testUtils";

let api: DataApi;
let ids: { work: string; Home: string; idle: string };

beforeEach(async () => {
  api = createMockApi();
  const c = await api.createCollection("C", null);
  const work = await api.createTag("work");
  const home = await api.createTag("Home");
  const idle = await api.createTag("idle");
  ids = { work: work.id, Home: home.id, idle: idle.id };
  await api.createNote({ type: "idea", body: "1", collectionId: c.id, tagIds: [work.id, home.id] });
  await api.createNote({ type: "idea", body: "2", collectionId: c.id, tagIds: [work.id] });
});
afterEach(() => vi.restoreAllMocks());

const show = async () => {
  renderWithApp(<TagsPage />, api);
  await screen.findByRole("link", { name: "work" });
};
const items = () => screen.getAllByRole("listitem");
const newName = (v: string) => fireEvent.change(screen.getByLabelText("New tag name"), { target: { value: v } });
const submitNew = () => fireEvent.submit(screen.getByLabelText("New tag name").closest("form")!);

test("lists tags alphabetically ignoring case, with counts including zero", async () => {
  await show();
  expect(items().map((li) => li.textContent?.replace("Rename", "").trim())).toEqual(["Home (1)", "idle (0)", "work (2)"]);
});

test("each tag links to the timeline and has no delete", async () => {
  await show();
  expect(screen.getByRole("link", { name: "work" })).toHaveAttribute("href", `/timeline?tag=${ids.work}`);
  expect(screen.queryByRole("button", { name: /delete/i })).toBeNull();
});

test("no tags: message and create form", async () => {
  api = createMockApi();
  renderWithApp(<TagsPage />, api);
  expect(await screen.findByText("No tags yet")).toBeInTheDocument();
  expect(screen.getByLabelText("New tag name")).toBeInTheDocument();
});

describe("create", () => {
  test("adds a trimmed tag with count 0 and clears the input", async () => {
    await show();
    newName("  zeta ");
    submitNew();
    expect(await screen.findByRole("link", { name: "zeta" })).toBeInTheDocument();
    expect(screen.getByText("zeta").closest("li")).toHaveTextContent("zeta (0)");
    expect(screen.getByLabelText("New tag name")).toHaveValue("");
  });

  test("rejects empty names", async () => {
    const create = vi.spyOn(api, "createTag");
    await show();
    newName("   ");
    submitNew();
    expect(await screen.findByRole("alert")).toHaveTextContent("Name is required");
    expect(create).not.toHaveBeenCalled();
  });

  test("rejects a case-insensitive duplicate", async () => {
    const create = vi.spyOn(api, "createTag");
    await show();
    newName("Work");
    submitNew();
    expect(await screen.findByRole("alert")).toHaveTextContent("That tag already exists");
    expect(create).not.toHaveBeenCalled();
  });

  test("shows an error when the data layer fails and leaves the list", async () => {
    vi.spyOn(api, "createTag").mockRejectedValue(new Error("server down"));
    await show();
    newName("fresh");
    submitNew();
    expect(await screen.findByRole("alert")).toHaveTextContent("server down");
    expect(items()).toHaveLength(3);
  });
});

describe("rename", () => {
  const startRename = (name: string) =>
    fireEvent.click(screen.getByRole("link", { name }).closest("li")!.querySelector("button")!);
  const field = (name: string) => screen.getByLabelText(`Rename ${name}`);

  test("saves in place and keeps the count", async () => {
    await show();
    startRename("work");
    fireEvent.change(field("work"), { target: { value: " job " } });
    fireEvent.submit(field("work").closest("form")!);
    const link = await screen.findByRole("link", { name: "job" });
    expect(link.closest("li")).toHaveTextContent("job (2)");
    expect((await api.listNotes())[0].tagIds).toContain(ids.work);
  });

  test("Escape cancels", async () => {
    const rename = vi.spyOn(api, "renameTag");
    await show();
    startRename("work");
    fireEvent.change(field("work"), { target: { value: "other" } });
    fireEvent.keyDown(field("work"), { key: "Escape" });
    expect(screen.getByRole("link", { name: "work" })).toBeInTheDocument();
    expect(rename).not.toHaveBeenCalled();
  });

  test("rejects empty and duplicate names", async () => {
    const rename = vi.spyOn(api, "renameTag");
    await show();
    startRename("work");
    fireEvent.change(field("work"), { target: { value: " " } });
    fireEvent.submit(field("work").closest("form")!);
    expect(await screen.findByRole("alert")).toHaveTextContent("Name is required");
    fireEvent.change(field("work"), { target: { value: "HOME" } });
    fireEvent.submit(field("work").closest("form")!);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("That tag already exists"));
    expect(rename).not.toHaveBeenCalled();
  });

  test("allows a different case of its own name", async () => {
    await show();
    startRename("work");
    fireEvent.change(field("work"), { target: { value: "Work" } });
    fireEvent.submit(field("work").closest("form")!);
    expect(await screen.findByRole("link", { name: "Work" })).toBeInTheDocument();
  });

  test("shows an error when rename fails and leaves the list unchanged", async () => {
    vi.spyOn(api, "renameTag").mockRejectedValue(new Error("server down"));
    await show();
    startRename("work");
    fireEvent.change(field("work"), { target: { value: "job" } });
    fireEvent.submit(field("work").closest("form")!);
    expect(await screen.findByRole("alert")).toHaveTextContent("server down");
    expect((await api.listTags()).map((t) => t.name)).toContain("work");
  });
});
