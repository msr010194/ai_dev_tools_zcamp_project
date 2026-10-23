import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import CollectionsPage from "./CollectionsPage";
import { createMockApi } from "./data/mockApi";
import type { DataApi } from "./data/types";
import { renderWithApp } from "./testUtils";

let api: DataApi;
let ids: Record<string, string>;

beforeEach(async () => {
  api = createMockApi();
  const work = await api.createCollection("Work", null);
  const proj = await api.createCollection("Project", work.id);
  const deep = await api.createCollection("Deep", proj.id);
  const arch = await api.createCollection("Archive", null);
  ids = { work: work.id, proj: proj.id, deep: deep.id, arch: arch.id };
});
afterEach(() => vi.restoreAllMocks());

const show = async () => {
  renderWithApp(<CollectionsPage />, api);
  await screen.findByText("Work");
};
const row = (name: string) => screen.getByText(name).closest("li") as HTMLElement;
const names = () => screen.getAllByRole("listitem").map((li) => li.querySelector("span")?.textContent);
const submitIn = (el: HTMLElement) => fireEvent.submit(el.closest("form")!);
const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });

describe("tree", () => {
  test("renders nested, alphabetically sorted, indented rows", async () => {
    await show();
    expect(names()).toEqual(["Archive", "Work", "Project", "Deep"]);
    expect(row("Work").style.marginLeft).toBe("0px");
    expect(row("Project").style.marginLeft).toBe("24px");
    expect(row("Deep").style.marginLeft).toBe("48px");
  });

  test("empty state offers Add collection", async () => {
    api = createMockApi();
    renderWithApp(<CollectionsPage />, api);
    expect(await screen.findByText("No collections yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add collection" })).toBeInTheDocument();
  });
});

describe("add", () => {
  test("adds a trimmed top-level collection without reload", async () => {
    await show();
    fireEvent.click(screen.getByRole("button", { name: "Add collection" }));
    type("New collection name", "  Zed  ");
    submitIn(screen.getByLabelText("New collection name"));
    await screen.findByText("Zed");
    expect((await api.listCollections()).find((c) => c.name === "Zed")).toMatchObject({ parentId: null });
  });

  test("adds a child under a row", async () => {
    await show();
    fireEvent.click(within(row("Archive")).getByRole("button", { name: "Add child" }));
    type("New child name", "Old");
    submitIn(screen.getByLabelText("New child name"));
    await screen.findByText("Old");
    expect((await api.listCollections()).find((c) => c.name === "Old")?.parentId).toBe(ids.arch);
  });

  test("rejects empty names", async () => {
    const create = vi.spyOn(api, "createCollection");
    await show();
    fireEvent.click(screen.getByRole("button", { name: "Add collection" }));
    type("New collection name", "   ");
    submitIn(screen.getByLabelText("New collection name"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Name is required");
    expect(create).not.toHaveBeenCalled();
  });

  test("rejects a sibling duplicate ignoring case", async () => {
    const create = vi.spyOn(api, "createCollection");
    await show();
    fireEvent.click(screen.getByRole("button", { name: "Add collection" }));
    type("New collection name", "work");
    submitIn(screen.getByLabelText("New collection name"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/already exists/);
    expect(create).not.toHaveBeenCalled();
  });
});

describe("rename", () => {
  test("submit saves and keeps position", async () => {
    await show();
    fireEvent.click(within(row("Archive")).getByRole("button", { name: "Rename" }));
    type("Rename Archive", " Attic ");
    submitIn(screen.getByLabelText("Rename Archive"));
    await screen.findByText("Attic");
    expect(names()).toEqual(["Attic", "Work", "Project", "Deep"]);
  });

  test("Escape cancels", async () => {
    const rename = vi.spyOn(api, "renameCollection");
    await show();
    fireEvent.click(within(row("Archive")).getByRole("button", { name: "Rename" }));
    type("Rename Archive", "Changed");
    fireEvent.keyDown(screen.getByLabelText("Rename Archive"), { key: "Escape" });
    expect(screen.getByText("Archive")).toBeInTheDocument();
    expect(rename).not.toHaveBeenCalled();
  });

  test("applies empty and duplicate rules", async () => {
    const rename = vi.spyOn(api, "renameCollection");
    await show();
    fireEvent.click(within(row("Archive")).getByRole("button", { name: "Rename" }));
    type("Rename Archive", "");
    submitIn(screen.getByLabelText("Rename Archive"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Name is required");
    type("Rename Archive", "WORK");
    submitIn(screen.getByLabelText("Rename Archive"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/already exists/);
    expect(rename).not.toHaveBeenCalled();
  });
});

describe("move", () => {
  const openMove = (name: string) => fireEvent.click(within(row(name)).getByRole("button", { name: "Move" }));

  test("excludes self and descendants and offers Top level", async () => {
    await show();
    openMove("Work");
    const select = screen.getByLabelText("Move Work to") as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.textContent!.trim())).toEqual(["Top level", "Archive"]);
  });

  test("moves a collection with its subtree", async () => {
    await show();
    openMove("Project");
    fireEvent.change(screen.getByLabelText("Move Project to"), { target: { value: ids.arch } });
    await waitFor(() => expect(names()).toEqual(["Archive", "Project", "Deep", "Work"]));
    expect(row("Deep").style.marginLeft).toBe("48px");
  });

  test("rejects a move that creates a duplicate sibling name", async () => {
    await api.createCollection("Project", ids.arch);
    const move = vi.spyOn(api, "moveCollection");
    renderWithApp(<CollectionsPage />, api);
    await screen.findByText("Work");
    fireEvent.click(within(screen.getAllByText("Project")[1].closest("li")!).getByRole("button", { name: "Move" }));
    fireEvent.change(screen.getByLabelText("Move Project to"), { target: { value: ids.arch } });
    expect(await screen.findByRole("alert")).toHaveTextContent(/already exists/);
    expect(move).not.toHaveBeenCalled();
  });
});

describe("delete", () => {
  const del = (name: string) => fireEvent.click(within(row(name)).getByRole("button", { name: "Delete" }));

  test("confirmation names the collection; cancel changes nothing", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const remove = vi.spyOn(api, "deleteCollection");
    await show();
    del("Archive");
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("Archive"));
    expect(remove).not.toHaveBeenCalled();
    expect(screen.getByText("Archive")).toBeInTheDocument();
  });

  test("deletes an empty collection", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await show();
    del("Archive");
    await waitFor(() => expect(screen.queryByText("Archive")).toBeNull());
  });

  test("rejects deleting a collection with children", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await show();
    del("Work");
    expect(await within(row("Work")).findByRole("alert")).toHaveTextContent(
      "Collection is not empty. Move or delete its contents first.",
    );
    expect(screen.getByText("Work")).toBeInTheDocument();
  });

  test("rejects deleting a collection with notes", async () => {
    await api.createNote({ type: "idea", body: "x", collectionId: ids.arch, tagIds: [] });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await show();
    del("Archive");
    expect(await within(row("Archive")).findByRole("alert")).toHaveTextContent("Collection is not empty");
  });

  test("shows an error for other failures and reloads real state", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(api, "deleteCollection").mockRejectedValue(new Error("server down"));
    await show();
    del("Archive");
    expect(await within(row("Archive")).findByRole("alert")).toHaveTextContent("server down");
  });
});

describe("load failures", () => {
  test("a failed initial load shows an error and Retry loads the tree", async () => {
    vi.spyOn(api, "listCollections").mockRejectedValueOnce(new Error("offline"));
    renderWithApp(<CollectionsPage />, api);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load collections: offline");
    expect(screen.queryByText("No collections yet")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Work")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("a failed reload after a successful add shows an error instead of a stale tree", async () => {
    await show();
    vi.spyOn(api, "listCollections").mockRejectedValueOnce(new Error("offline"));
    fireEvent.click(screen.getByRole("button", { name: "Add collection" }));
    type("New collection name", "Zed");
    submitIn(screen.getByLabelText("New collection name"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load collections: offline");
    expect(screen.queryByText("Work")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Zed")).toBeInTheDocument();
  });
});
