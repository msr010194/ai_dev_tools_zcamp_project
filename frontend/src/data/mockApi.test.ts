import { beforeEach, describe, expect, test } from "vitest";
import { createMockApi } from "./mockApi";
import type { DataApi } from "./types";

let api: DataApi;
beforeEach(() => {
  api = createMockApi();
});

describe("mock data api", () => {
  test("creates and lists collections, tags and notes", async () => {
    const c = await api.createCollection("Work", null);
    const t = await api.createTag("focus");
    const n = await api.createNote({ type: "idea", body: "x", collectionId: c.id, tagIds: [t.id] });
    expect(await api.listCollections()).toEqual([c]);
    expect(await api.listTags()).toEqual([t]);
    expect(await api.getNote(n.id)).toEqual(n);
  });

  test("rejects deleting a non-empty collection", async () => {
    const c = await api.createCollection("Work", null);
    await api.createNote({ type: "idea", body: "x", collectionId: c.id, tagIds: [] });
    await expect(api.deleteCollection(c.id)).rejects.toThrow();
  });
});
