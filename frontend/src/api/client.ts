import createClient from "openapi-fetch";
import type { components, operations, paths } from "./schema";

type Schemas = components["schemas"];
type JsonResponse<Op extends keyof operations, Status extends number> = operations[Op]["responses"] extends {
  [S in Status]: { content: { "application/json": infer Body } };
}
  ? Body
  : never;
type JsonRequest<Op extends keyof operations> = operations[Op] extends {
  requestBody: { content: { "application/json": infer Body } };
}
  ? Body
  : never;

/** A note of any Type, as the API returns it (a union discriminated by `type`). */
export type NoteOut = JsonResponse<"getNote", 200>;
export type NoteCreate = JsonRequest<"createNote">;
export type NoteUpdate = Schemas["NoteUpdate"];
export type CollectionTreeNode = Schemas["CollectionTreeNode"];
export type CollectionOut = Schemas["CollectionOut"];
export type CollectionCreate = Schemas["CollectionCreate"];
export type CollectionUpdate = Schemas["CollectionUpdate"];
export type TagOut = Schemas["TagOut"];
export type TagCreate = Schemas["TagCreate"];
export type TagUpdate = Schemas["TagUpdate"];
export type TimelinePage = Schemas["TimelinePageOut"];
export type ResurfaceOut = Schemas["ResurfaceOut"];
/** The body of every error response: `{code, message, errors}`. */
export type ApiErrorBody = Schemas["Error"];

export type ApiClient = ReturnType<typeof createApiClient>;

/** A typed client for the Notes API; `baseUrl` is prefixed to every path (e.g. `/api`). */
export function createApiClient(baseUrl: string) {
  return createClient<paths>({ baseUrl });
}
