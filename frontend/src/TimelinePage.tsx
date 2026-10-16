import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import CollectionPicker from "./CollectionPicker";
import { selfAndDescendantIds } from "./collectionTree";
import { useData } from "./data/DataContext";
import type { Collection, Note, Tag } from "./data/types";
import { preview } from "./noteUtils";

const PAGE = 20;

export default function TimelinePage() {
  const api = useData();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<{ notes: Note[]; collections: Collection[]; tags: Tag[] } | null>(null);
  const collectionFilter = params.get("collection") ?? "";
  const tagFilter = params.get("tag") ?? "";
  const untagged = params.get("untagged") === "1";
  const filterKey = `${collectionFilter}|${tagFilter}|${untagged}`;
  const [shown, setShown] = useState({ key: filterKey, count: PAGE });

  useEffect(() => {
    Promise.all([api.listNotes(), api.listCollections(), api.listTags()]).then(([notes, collections, tags]) =>
      setData({ notes, collections, tags }),
    );
  }, [api]);

  if (!data) return <h1>Timeline</h1>;

  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    setParams(next);
  };

  const collectionName = (id: string) => data.collections.find((c) => c.id === id)?.name ?? "";
  const tagName = (id: string) => data.tags.find((t) => t.id === id)?.name;
  const collectionIds = collectionFilter ? selfAndDescendantIds(data.collections, collectionFilter) : null;

  const matching = data.notes
    .filter((n) => !collectionIds || collectionIds.has(n.collectionId))
    .filter((n) => !tagFilter || n.tagIds.includes(tagFilter))
    .filter((n) => !untagged || n.tagIds.length === 0)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));

  const count = shown.key === filterKey ? shown.count : PAGE;
  const visible = matching.slice(0, count);
  const hasFilters = collectionFilter !== "" || tagFilter !== "" || untagged;

  return (
    <>
      <h1>Timeline</h1>
      <div>
        <CollectionPicker
          collections={data.collections}
          label="Collection filter"
          emptyOption="All collections"
          value={collectionFilter}
          onChange={(id) => update({ collection: id })}
        />
        <label>
          Tag filter
          <select value={tagFilter} onChange={(e) => update({ tag: e.target.value, untagged: null })}>
            <option value="">All tags</option>
            {data.tags.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={untagged}
            onChange={(e) => update({ untagged: e.target.checked ? "1" : null, tag: null })}
          />
          Untagged
        </label>
      </div>
      {data.notes.length === 0 ? (
        <p>No notes yet</p>
      ) : matching.length === 0 ? (
        <div>
          <p>No notes match these filters</p>
          {hasFilters && (
            <button type="button" onClick={() => setParams(new URLSearchParams())}>
              Clear filters
            </button>
          )}
        </div>
      ) : (
        <>
          <ul>
            {visible.map((n) => (
              <li key={n.id}>
                <strong>{n.type}</strong> · {collectionName(n.collectionId)}
                {n.tagIds.map((id) => {
                  const name = tagName(id);
                  return name ? (
                    <Link key={id} to={`/timeline?tag=${id}`} style={{ marginLeft: 8 }}>
                      {name}
                    </Link>
                  ) : null;
                })}
                <p>{preview(n.body)}</p>
              </li>
            ))}
          </ul>
          {matching.length > visible.length && (
            <button type="button" onClick={() => setShown({ key: filterKey, count: count + PAGE })}>
              Load more
            </button>
          )}
        </>
      )}
    </>
  );
}
