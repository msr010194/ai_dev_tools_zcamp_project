import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import TimelinePage from "./TimelinePage";
import { createMockApi } from "./data/mockApi";
import type { DataApi } from "./data/types";
import { renderWithApp } from "./testUtils";
import { Route, Routes, useLocation } from "react-router-dom";

let api: DataApi;
let ids: { work: string; proj: string; home: string; a: string; b: string };

const tick = { n: 0 };
const addNote = (body: string, collectionId: string, tagIds: string[] = []) => {
  vi.setSystemTime(new Date(Date.UTC(2026, 0, 1) + ++tick.n * 60_000));
  return api.createNote({ type: "idea", body, collectionId, tagIds });
};

beforeEach(async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  tick.n = 0;
  api = createMockApi();
  const work = await api.createCollection("Work", null);
  const proj = await api.createCollection("Project", work.id);
  const home = await api.createCollection("Home", null);
  const a = await api.createTag("a");
  const b = await api.createTag("b");
  ids = { work: work.id, proj: proj.id, home: home.id, a: a.id, b: b.id };
});
afterEach(() => vi.useRealTimers());

const Where = () => <span data-testid="loc">{useLocation().pathname + useLocation().search}</span>;
const show = (route = "/timeline") =>
  renderWithApp(
    <>
      <Routes>
        <Route path="/timeline" element={<TimelinePage />} />
      </Routes>
      <Where />
    </>,
    api,
    route,
  );
const items = () => screen.getAllByRole("listitem");

describe("list", () => {
  test("newest first, with type, collection, tags and preview", async () => {
    await addNote("first", ids.work, [ids.a]);
    await addNote("second", ids.home);
    show();
    await screen.findByText("second");
    const li = items();
    expect(li[0]).toHaveTextContent("second");
    expect(li[1]).toHaveTextContent("first");
    expect(li[1]).toHaveTextContent("idea");
    expect(li[1]).toHaveTextContent("Work");
    expect(within(li[1]).getByRole("link", { name: "a" })).toBeInTheDocument();
    expect(within(li[0]).queryAllByRole("link")).toHaveLength(0);
  });

  test("truncates the body at 140 characters", async () => {
    await addNote("x".repeat(141), ids.work);
    await addNote("y".repeat(140), ids.work);
    show();
    await screen.findAllByRole("listitem");
    expect(items()[0]).toHaveTextContent("y".repeat(140));
    expect(items()[0]).not.toHaveTextContent("...");
    expect(items()[1]).toHaveTextContent("x".repeat(140) + "...");
  });

  test("shows 20 at a time and Load more disappears when done", async () => {
    for (let i = 0; i < 45; i++) await addNote(`n${i}`, ids.work);
    show();
    await screen.findAllByRole("listitem");
    expect(items()).toHaveLength(20);
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(items()).toHaveLength(40);
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(items()).toHaveLength(45);
    expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  });

  test("no notes at all", async () => {
    show();
    expect(await screen.findByText("No notes yet")).toBeInTheDocument();
  });

  test("filters matching nothing offer Clear filters", async () => {
    await addNote("one", ids.work);
    show(`/timeline?tag=${ids.a}`);
    expect(await screen.findByText("No notes match these filters")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(await screen.findByText("one")).toBeInTheDocument();
    expect(screen.getByTestId("loc")).toHaveTextContent("/timeline");
    expect(screen.getByTestId("loc").textContent).toBe("/timeline");
  });
});

describe("filters", () => {
  beforeEach(async () => {
    await addNote("work-a", ids.work, [ids.a]);
    await addNote("proj-b", ids.proj, [ids.b]);
    await addNote("proj-none", ids.proj);
    await addNote("home-a", ids.home, [ids.a]);
  });
  const texts = () => items().map((li) => li.querySelector("p")?.textContent);

  test("collection filter includes descendants and lists a tree", async () => {
    show();
    const select = (await screen.findByLabelText("Collection filter")) as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.textContent!.trim())).toEqual([
      "All collections",
      "Home",
      "Work",
      "Project",
    ]);
    fireEvent.change(select, { target: { value: ids.work } });
    expect(texts()).toEqual(["proj-none", "proj-b", "work-a"]);
  });

  test("tag filter", async () => {
    show();
    fireEvent.change(await screen.findByLabelText("Tag filter"), { target: { value: ids.a } });
    expect(texts()).toEqual(["home-a", "work-a"]);
  });

  test("untagged toggle", async () => {
    show();
    fireEvent.click(await screen.findByLabelText("Untagged"));
    expect(texts()).toEqual(["proj-none"]);
  });

  test("tag and untagged are mutually exclusive", async () => {
    show(`/timeline?tag=${ids.a}`);
    fireEvent.click(await screen.findByLabelText("Untagged"));
    expect(screen.getByLabelText("Tag filter")).toHaveValue("");
    expect(screen.getByLabelText("Untagged")).toBeChecked();
    fireEvent.change(screen.getByLabelText("Tag filter"), { target: { value: ids.b } });
    expect(screen.getByLabelText("Untagged")).not.toBeChecked();
    expect(texts()).toEqual(["proj-b"]);
  });

  test("collection combined with tag or untagged", async () => {
    show(`/timeline?collection=${ids.work}&tag=${ids.a}`);
    await screen.findAllByRole("listitem");
    expect(texts()).toEqual(["work-a"]);
    fireEvent.click(screen.getByLabelText("Untagged"));
    expect(texts()).toEqual(["proj-none"]);
  });

  test("URL drives the filters", async () => {
    show(`/timeline?tag=${ids.b}`);
    await screen.findAllByRole("listitem");
    expect(screen.getByLabelText("Tag filter")).toHaveValue(ids.b);
    expect(texts()).toEqual(["proj-b"]);
  });

  test("unknown ids show the empty state", async () => {
    show("/timeline?tag=nope");
    expect(await screen.findByText("No notes match these filters")).toBeInTheDocument();
  });

  test("unknown collection id shows the empty state", async () => {
    show("/timeline?collection=nope");
    expect(await screen.findByText("No notes match these filters")).toBeInTheDocument();
  });

  test("a tag chip opens the tag-filtered timeline", async () => {
    show();
    await screen.findAllByRole("listitem");
    fireEvent.click(within(items()[0]).getByRole("link", { name: "a" }));
    expect(screen.getByTestId("loc")).toHaveTextContent(`/timeline?tag=${ids.a}`);
  });

  test("changing a filter resets paging to 20", async () => {
    for (let i = 0; i < 25; i++) await addNote(`m${i}`, ids.home, [ids.b]);
    show();
    await screen.findAllByRole("listitem");
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(items()).toHaveLength(29);
    fireEvent.change(screen.getByLabelText("Tag filter"), { target: { value: ids.b } });
    expect(items()).toHaveLength(20);
  });
});
