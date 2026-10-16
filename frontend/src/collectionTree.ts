import type { Collection } from "./data/types";

export interface TreeRow {
  collection: Collection;
  depth: number;
}

const byName = (a: Collection, b: Collection) =>
  a.name.localeCompare(b.name, undefined, { sensitivity: "base" });

/** Depth-first rows, siblings sorted alphabetically; collections with a missing parent are treated as roots. */
export function flattenTree(collections: Collection[]): TreeRow[] {
  const ids = new Set(collections.map((c) => c.id));
  const childrenOf = (parentId: string | null) =>
    collections
      .filter((c) => (parentId === null ? c.parentId === null || !ids.has(c.parentId) : c.parentId === parentId))
      .sort(byName);
  const rows: TreeRow[] = [];
  const visit = (parentId: string | null, depth: number) => {
    for (const c of childrenOf(parentId)) {
      rows.push({ collection: c, depth });
      visit(c.id, depth + 1);
    }
  };
  visit(null, 0);
  return rows;
}

/** The collection's own id plus the ids of all its descendants. */
export function selfAndDescendantIds(collections: Collection[], id: string): Set<string> {
  const result = new Set([id]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const c of collections) {
      if (c.parentId !== null && result.has(c.parentId) && !result.has(c.id)) {
        result.add(c.id);
        grew = true;
      }
    }
  }
  return result;
}

export const indentLabel = (row: TreeRow) => "\u00a0\u00a0\u00a0\u00a0".repeat(row.depth) + row.collection.name;
