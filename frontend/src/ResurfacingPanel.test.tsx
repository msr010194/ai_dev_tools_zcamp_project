import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import ResurfacingPanel from "./ResurfacingPanel";
import { createMockApi } from "./data/mockApi";
import type { DataApi, NoteType } from "./data/types";
import { renderWithApp } from "./testUtils";

const DAY = 24 * 60 * 60 * 1000;
const NOW = Date.UTC(2026, 5, 30);
let api: DataApi;
let col: string;

beforeEach(async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(NOW);
  api = createMockApi();
  col = (await api.createCollection("Work", null)).id;
});
afterEach(() => vi.useRealTimers());

const addNote = async (body: string, daysOld: number, type: NoteType = "idea") => {
  vi.setSystemTime(NOW - daysOld * DAY);
  const n = await api.createNote({ type, body, collectionId: col, tagIds: [] });
  vi.setSystemTime(NOW);
  return n;
};
const show = (random = () => 0) => renderWithApp(<ResurfacingPanel random={random} />, api);
const bodies = () => screen.getAllByRole("listitem").map((li) => li.querySelector("p")?.textContent);

describe("selection", () => {
  test("shows at most 3 notes with type, collection and a 140 char preview", async () => {
    for (let i = 0; i < 5; i++) await addNote(i === 0 ? "z".repeat(150) : `n${i}`, 10 + i);
    show();
    await screen.findAllByRole("listitem");
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    const first = screen.getAllByRole("listitem")[0];
    expect(first).toHaveTextContent("idea");
    expect(first).toHaveTextContent("Work");
    const long = bodies().find((b) => b?.startsWith("z"));
    expect(long).toBe("z".repeat(140) + "...");
  });

  test("only notes older than 7 days are eligible", async () => {
    await addNote("old", 8);
    await addNote("edge", 7);
    await addNote("new", 1);
    show();
    await screen.findAllByRole("listitem");
    expect(bodies()).toEqual(["old"]);
  });

  test("includes a Memory when one is eligible, whatever the random source says", async () => {
    for (let i = 0; i < 6; i++) await addNote(`idea${i}`, 20);
    await addNote("memory", 20, "memory");
    for (const r of [0, 0.5, 0.99]) {
      const { unmount } = show(() => r);
      await screen.findAllByRole("listitem");
      expect(bodies()).toContain("memory");
      unmount();
    }
  });

  test("never shows the same note twice in one set", async () => {
    for (let i = 0; i < 4; i++) await addNote(`n${i}`, 20);
    show(() => 0);
    await screen.findAllByRole("listitem");
    expect(new Set(bodies()).size).toBe(3);
  });

  test("a never-resurfaced note beats one resurfaced just now", async () => {
    const seen = await addNote("seen", 20);
    await addNote("fresh", 20);
    await api.markResurfaced(seen.id);
    const picks: string[] = [];
    for (const r of [0.05, 0.5, 0.97]) {
      const { unmount } = show(() => r);
      await screen.findAllByRole("listitem");
      picks.push(bodies()[0]!);
      unmount();
    }
    // Weights are 1 (just resurfaced) vs 31 (never): only draws below 1/32 pick "seen" first.
    expect(picks).toEqual(["fresh", "fresh", "fresh"]);
  });

  test("fewer than 3 eligible notes shows only those", async () => {
    await addNote("a", 9);
    await addNote("b", 12);
    show();
    await screen.findAllByRole("listitem");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("recording", () => {
  test("marks each shown note exactly once, and the mock updates it", async () => {
    const a = await addNote("a", 9);
    const b = await addNote("b", 12);
    const mark = vi.spyOn(api, "markResurfaced");
    show();
    await screen.findAllByRole("listitem");
    await waitFor(() => expect(mark).toHaveBeenCalledTimes(2));
    expect(mark.mock.calls.map((c) => c[0]).sort()).toEqual([a.id, b.id].sort());
    const stored = await api.getNote(a.id);
    expect(stored?.resurfaceCount).toBe(1);
    expect(stored?.lastResurfacedAt).toBe(new Date(NOW).toISOString());
  });

  test("a failing markResurfaced does not hide the notes", async () => {
    await addNote("a", 9);
    vi.spyOn(api, "markResurfaced").mockRejectedValue(new Error("nope"));
    show();
    expect(await screen.findByText("a")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("show another", () => {
  test("replaces the set, avoiding previous notes, and records the new ones", async () => {
    for (let i = 0; i < 6; i++) await addNote(`n${i}`, 20 + i);
    const mark = vi.spyOn(api, "markResurfaced");
    show(() => 0);
    await screen.findAllByRole("listitem");
    const first = bodies();
    await waitFor(() => expect(mark).toHaveBeenCalledTimes(3));
    fireEvent.click(screen.getByRole("button", { name: "Show another" }));
    await waitFor(() => expect(mark).toHaveBeenCalledTimes(6));
    const second = bodies();
    expect(second.filter((b) => first.includes(b))).toEqual([]);
  });

  test("may repeat when there are not enough other notes, and stays usable", async () => {
    await addNote("a", 20);
    await addNote("b", 21);
    const mark = vi.spyOn(api, "markResurfaced");
    show();
    await screen.findAllByRole("listitem");
    fireEvent.click(screen.getByRole("button", { name: "Show another" }));
    await waitFor(() => expect(mark).toHaveBeenCalledTimes(4));
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Show another" })).toBeEnabled();
  });
});

describe("empty", () => {
  test.each([
    ["no notes", [] as number[]],
    ["only recent notes", [1, 3]],
  ])("%s", async (_name, ages) => {
    for (const age of ages) await addNote("x", age);
    show();
    expect(await screen.findByText("Nothing to revisit yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show another" })).toBeNull();
  });
});
