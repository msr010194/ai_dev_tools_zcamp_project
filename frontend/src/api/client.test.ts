import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";
import { createApiClient, type ApiErrorBody, type NoteCreate, type NoteOut } from "./client";

const note: NoteOut = {
  id: "abc",
  type: "idea",
  body: "Hello",
  collection_id: "c1",
  tag_ids: [],
  created_at: "2026-01-01T00:00:00Z",
  last_resurfaced_at: null,
  resurface_count: 0,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("createApiClient types", () => {
  it("returns the five-variant note union for GET /notes/{note_id}", () => {
    const client = createApiClient("/api");
    const call = () => client.GET("/notes/{note_id}", { params: { path: { note_id: "abc" } } });
    type Result = Awaited<ReturnType<typeof call>>;

    expectTypeOf<NonNullable<Result["data"]>>().toEqualTypeOf<NoteOut>();
    expectTypeOf<NoteOut["type"]>().toEqualTypeOf<"journal" | "idea" | "reference" | "plan" | "memory">();
    expectTypeOf<NonNullable<Result["error"]>>().toEqualTypeOf<ApiErrorBody>();
    expectTypeOf<ApiErrorBody>().toEqualTypeOf<{
      code: string;
      message: string;
      errors: { location: "body" | "query" | "path"; field: string | null; message: string }[];
    }>();
  });

  it("narrows on type to expose Type-specific fields", () => {
    const describeNote = (n: NoteOut) => (n.type === "plan" ? n.checklist.map((item) => item.position) : []);
    expect(describeNote(note)).toEqual([]);
  });

  it("rejects bad requests at compile time", () => {
    const client = createApiClient("/api");
    const neverCalled = () => {
      // @ts-expect-error collection_id is required
      const missingCollection: NoteCreate = { type: "idea", body: "x" };
      void client.POST("/notes", { body: missingCollection });
      // @ts-expect-error the note_id path parameter is required
      void client.GET("/notes/{note_id}", { params: { path: {} } });
    };
    expect(typeof neverCalled).toBe("function");
  });
});

describe("createApiClient runtime", () => {
  it("requests baseUrl + path and returns the parsed body as data", async () => {
    const fetchMock = vi.fn(async (_input: Request) =>
      new Response(JSON.stringify(note), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = createApiClient("http://x/api");
    const { data, error } = await client.GET("/notes/{note_id}", { params: { path: { note_id: "abc" } } });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const request = fetchMock.mock.calls[0][0];
    expect(request.url).toBe("http://x/api/notes/abc");
    expect(request.method).toBe("GET");
    expect(data).toEqual(note);
    expect(error).toBeUndefined();
  });

  it("returns the error body for non-2xx responses", async () => {
    const body: ApiErrorBody = { code: "note_not_found", message: "Note not found", errors: [] };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(body), { status: 404, headers: { "Content-Type": "application/json" } })),
    );

    const { data, error, response } = await createApiClient("http://x/api").GET("/notes/{note_id}", {
      params: { path: { note_id: "missing" } },
    });

    expect(data).toBeUndefined();
    expect(error).toEqual(body);
    expect(response.status).toBe(404);
  });
});
