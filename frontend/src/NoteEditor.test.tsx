import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import NoteEditor from "./NoteEditor";
import { createMockApi } from "./data/mockApi";
import type { DataApi } from "./data/types";
import { renderWithApp } from "./testUtils";

let api: DataApi;
beforeEach(async () => {
  api = createMockApi();
  const work = await api.createCollection("Work", null);
  const proj = await api.createCollection("Project", work.id);
  await api.createCollection("Deep", proj.id);
  await api.createTag("focus");
  await api.createTag("home");
});

const body = () => screen.getByLabelText("Body");
const collection = () => screen.getByLabelText("Collection") as HTMLSelectElement;
const pickCollection = (name: string) => {
  const opt = Array.from(collection().options).find((o) => o.textContent?.trim() === name)!;
  fireEvent.change(collection(), { target: { value: opt.value } });
};

describe("create", () => {
  test("saves with type, body, collection and tags", async () => {
    const create = vi.spyOn(api, "createNote");
    const onSaved = vi.fn();
    renderWithApp(<NoteEditor type="idea" onSaved={onSaved} />, api);
    await screen.findByLabelText("Collection");
    fireEvent.change(body(), { target: { value: "hello" } });
    pickCollection("Project");
    fireEvent.click(screen.getByLabelText("focus"));
    fireEvent.click(screen.getByLabelText("home"));
    fireEvent.click(screen.getByLabelText("home"));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    const cols = await api.listCollections();
    const tags = await api.listTags();
    expect(create).toHaveBeenCalledTimes(1);
    expect(create).toHaveBeenCalledWith({
      type: "idea",
      body: "hello",
      collectionId: cols.find((c) => c.name === "Project")!.id,
      tagIds: [tags.find((t) => t.name === "focus")!.id],
    });
    expect(onSaved.mock.calls[0][0].body).toBe("hello");
  });

  test("shows a collection tree three levels deep, required, with no tag creation", async () => {
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, api);
    await screen.findByLabelText("Collection");
    const labels = Array.from(collection().options).map((o) => o.textContent);
    expect(labels.slice(1)).toEqual(["Work", "\u00a0\u00a0\u00a0\u00a0Project", "\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0Deep"]);
    expect(collection()).toBeRequired();
    expect(screen.getByRole("group", { name: "Tags" })).toBeInTheDocument();
    expect(screen.getAllByRole("checkbox").map((c) => c.parentElement?.textContent)).toEqual(["focus", "home"]);
    expect(screen.queryByRole("textbox", { name: /tag/i })).toBeNull();
  });

  test("saves with zero tags", async () => {
    const create = vi.spyOn(api, "createNote");
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, api);
    await screen.findByLabelText("Collection");
    fireEvent.change(body(), { target: { value: "x" } });
    pickCollection("Work");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create.mock.calls[0][0].tagIds).toEqual([]);
  });

  test("blocks save without a collection", async () => {
    const create = vi.spyOn(api, "createNote");
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, api);
    await screen.findByLabelText("Collection");
    fireEvent.change(body(), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("A Collection is required")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  test("blocks save with a whitespace-only body", async () => {
    const create = vi.spyOn(api, "createNote");
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, api);
    await screen.findByLabelText("Collection");
    fireEvent.change(body(), { target: { value: "   " } });
    pickCollection("Work");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Body is required")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  test("disables Save while in flight so a double click creates one note", async () => {
    let release!: () => void;
    const create = vi.spyOn(api, "createNote").mockImplementation(
      () => new Promise((res) => (release = () => res({} as never))),
    );
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, api);
    await screen.findByLabelText("Collection");
    fireEvent.change(body(), { target: { value: "x" } });
    pickCollection("Work");
    const save = screen.getByRole("button", { name: "Save" });
    fireEvent.click(save);
    fireEvent.click(save);
    expect(save).toBeDisabled();
    expect(create).toHaveBeenCalledTimes(1);
    release();
    await waitFor(() => expect(save).toBeEnabled());
  });

  test("shows an error on rejection, keeps values and allows retry", async () => {
    const create = vi.spyOn(api, "createNote").mockRejectedValueOnce(new Error("boom"));
    const onSaved = vi.fn();
    renderWithApp(<NoteEditor type="idea" onSaved={onSaved} />, api);
    await screen.findByLabelText("Collection");
    fireEvent.change(body(), { target: { value: "keep me" } });
    pickCollection("Work");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("boom")).toBeInTheDocument();
    expect(body()).toHaveValue("keep me");
    expect(collection().selectedOptions[0].textContent).toBe("Work");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(create).toHaveBeenCalledTimes(2);
  });

  test("saves a 10,000 character body untruncated", async () => {
    const create = vi.spyOn(api, "createNote");
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, api);
    await screen.findByLabelText("Collection");
    fireEvent.change(body(), { target: { value: "a".repeat(10000) } });
    pickCollection("Work");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create.mock.calls[0][0].body).toHaveLength(10000);
  });

  test.each([
    ["journal", "Mood"],
    ["reference", "Link"],
    ["plan", "Target date"],
    ["memory", "When"],
  ] as const)("shows %s fields", async (type, label) => {
    renderWithApp(<NoteEditor type={type} onSaved={vi.fn()} />, api);
    expect(await screen.findByLabelText(label)).toBeInTheDocument();
  });

  test("idea shows no extra fields", async () => {
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, api);
    await screen.findByLabelText("Collection");
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
  });
});

describe("edit", () => {
  test("pre-fills, updates without creating, and cannot change type", async () => {
    const cols = await api.listCollections();
    const tags = await api.listTags();
    const note = await api.createNote({
      type: "journal",
      body: "old",
      collectionId: cols[1].id,
      tagIds: [tags[0].id],
    });
    const create = vi.spyOn(api, "createNote");
    const update = vi.spyOn(api, "updateNote");
    const onSaved = vi.fn();
    renderWithApp(<NoteEditor type="idea" note={note} onSaved={onSaved} />, api);
    await waitFor(() => expect(collection().value).toBe(cols[1].id));
    expect(body()).toHaveValue("old");
    expect(screen.getByLabelText("focus")).toBeChecked();
    expect(screen.getByLabelText("home")).not.toBeChecked();
    expect(screen.getByText("Type: Journal")).toBeInTheDocument();
    fireEvent.change(body(), { target: { value: "new" } });
    fireEvent.click(screen.getByLabelText("focus"));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(create).not.toHaveBeenCalled();
    expect(update).toHaveBeenCalledWith(note.id, { body: "new", collectionId: cols[1].id, tagIds: [] });
    expect((await api.getNote(note.id))?.tagIds).toEqual([]);
  });

  test("a missing collection counts as unselected and a missing tag is dropped", async () => {
    const tags = await api.listTags();
    const note = await api.createNote({
      type: "idea",
      body: "orphan",
      collectionId: "gone",
      tagIds: [tags[0].id, "gone-tag"],
    });
    const update = vi.spyOn(api, "updateNote");
    renderWithApp(<NoteEditor type="idea" note={note} onSaved={vi.fn()} />, api);
    await screen.findByLabelText("Collection");
    expect(collection().value).toBe("");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("A Collection is required")).toBeInTheDocument();
    expect(update).not.toHaveBeenCalled();
    pickCollection("Work");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(update).toHaveBeenCalled());
    expect(update.mock.calls[0][1]?.tagIds).toEqual([tags[0].id]);
  });

  test("an already set Journal prompt is read-only", async () => {
    const cols = await api.listCollections();
    const note = await api.createNote({ type: "journal", body: "b", collectionId: cols[0].id, tagIds: [] });
    renderWithApp(
      <NoteEditor
        type="journal"
        note={note}
        initialFields={{ mood: "", prompt: "Why?", isRetrospective: false, period: "" }}
        onSaved={vi.fn()}
      />,
      api,
    );
    expect(await screen.findByLabelText("Prompt")).toHaveAttribute("readonly");
  });
});

describe("empty data", () => {
  test("no collections or tags", async () => {
    const empty = createMockApi();
    const create = vi.spyOn(empty, "createNote");
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, empty);
    expect(await screen.findByText("No collections yet")).toBeInTheDocument();
    expect(screen.getByText("No tags yet")).toBeInTheDocument();
    fireEvent.change(body(), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("A Collection is required")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  test("no tags still saves", async () => {
    const noTags = createMockApi();
    await noTags.createCollection("Work", null);
    const create = vi.spyOn(noTags, "createNote");
    renderWithApp(<NoteEditor type="idea" onSaved={vi.fn()} />, noTags);
    await screen.findByText("No tags yet");
    fireEvent.change(body(), { target: { value: "x" } });
    pickCollection("Work");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
  });
});
