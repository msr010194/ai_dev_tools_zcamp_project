import { useCallback, useEffect, useState } from "react";
import { flattenTree, indentLabel, selfAndDescendantIds } from "./collectionTree";
import { useData } from "./data/DataContext";
import type { Collection } from "./data/types";

type Action = { kind: "add"; parentId: string | null } | { kind: "rename" | "move"; id: string };

const TOP = "top";
const NOT_EMPTY = "Collection is not empty. Move or delete its contents first.";

function NameForm({ initial, label, onSubmit, onCancel }: {
  initial: string;
  label: string;
  onSubmit: (name: string) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial);
  return (
    <form
      style={{ display: "inline" }}
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(name);
      }}
    >
      <input
        aria-label={label}
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && onCancel()}
      />
      <button type="submit">Save</button>
      <button type="button" onClick={onCancel}>
        Cancel
      </button>
    </form>
  );
}

export default function CollectionsPage() {
  const api = useData();
  const [collections, setCollections] = useState<Collection[] | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [message, setMessage] = useState<{ key: string; text: string } | null>(null);

  const refresh = useCallback(async () => setCollections(await api.listCollections()), [api]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!collections) return <h1>Collections</h1>;

  const duplicate = (name: string, parentId: string | null, excludeId?: string) =>
    collections.some(
      (c) => c.id !== excludeId && c.parentId === parentId && c.name.toLowerCase() === name.toLowerCase(),
    );

  // Runs a data layer call, then reloads so the tree shows the real state even on failure.
  const run = async (key: string, fn: () => Promise<unknown>) => {
    setMessage(null);
    try {
      await fn();
      setAction(null);
    } catch (err) {
      const text = err instanceof Error ? err.message : "Something went wrong";
      setMessage({ key, text: /not empty/i.test(text) ? NOT_EMPTY : text });
    }
    await refresh();
  };

  const checkName = (key: string, raw: string, parentId: string | null, excludeId?: string): string | null => {
    const name = raw.trim();
    if (name === "") {
      setMessage({ key, text: "Name is required" });
      return null;
    }
    if (duplicate(name, parentId, excludeId)) {
      setMessage({ key, text: "A collection with that name already exists here" });
      return null;
    }
    return name;
  };

  const add = (parentId: string | null, raw: string) => {
    const key = parentId ?? TOP;
    const name = checkName(key, raw, parentId);
    if (name) run(key, () => api.createCollection(name, parentId));
  };

  const rename = (c: Collection, raw: string) => {
    const name = checkName(c.id, raw, c.parentId, c.id);
    if (name) run(c.id, () => api.renameCollection(c.id, name));
  };

  const move = (c: Collection, parentId: string | null) => {
    const clash = collections.some(
      (o) => o.id !== c.id && o.parentId === parentId && o.name.toLowerCase() === c.name.toLowerCase(),
    );
    if (clash) setMessage({ key: c.id, text: "A collection with that name already exists there" });
    else run(c.id, () => api.moveCollection(c.id, parentId));
  };

  const remove = (c: Collection) => {
    if (window.confirm(`Delete collection "${c.name}"?`)) run(c.id, () => api.deleteCollection(c.id));
  };

  const cancel = () => {
    setAction(null);
    setMessage(null);
  };
  const messageFor = (key: string) =>
    message?.key === key ? <p role="alert">{message.text}</p> : null;
  const adding = (parentId: string | null) =>
    action?.kind === "add" && action.parentId === parentId && (
      <NameForm
        initial=""
        label={parentId ? "New child name" : "New collection name"}
        onSubmit={(n) => add(parentId, n)}
        onCancel={cancel}
      />
    );

  const rows = flattenTree(collections);

  return (
    <>
      <h1>Collections</h1>
      <button type="button" onClick={() => { setMessage(null); setAction({ kind: "add", parentId: null }); }}>
        Add collection
      </button>
      {adding(null)}
      {messageFor(TOP)}
      {rows.length === 0 ? (
        <p>No collections yet</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {rows.map(({ collection: c, depth }) => {
            const blocked = selfAndDescendantIds(collections, c.id);
            return (
              <li key={c.id} style={{ marginLeft: depth * 24 }}>
                {action?.kind === "rename" && action.id === c.id ? (
                  <NameForm initial={c.name} label={`Rename ${c.name}`} onSubmit={(n) => rename(c, n)} onCancel={cancel} />
                ) : (
                  <span>{c.name}</span>
                )}{" "}
                <button type="button" onClick={() => { setMessage(null); setAction({ kind: "rename", id: c.id }); }}>
                  Rename
                </button>
                <button type="button" onClick={() => { setMessage(null); setAction({ kind: "add", parentId: c.id }); }}>
                  Add child
                </button>
                <button type="button" onClick={() => { setMessage(null); setAction({ kind: "move", id: c.id }); }}>
                  Move
                </button>
                <button type="button" onClick={() => remove(c)}>
                  Delete
                </button>
                {action?.kind === "move" && action.id === c.id && (
                  <label>
                    Move {c.name} to
                    <select value={c.parentId ?? ""} onChange={(e) => move(c, e.target.value || null)}>
                      <option value="">Top level</option>
                      {rows
                        .filter((r) => !blocked.has(r.collection.id))
                        .map((r) => (
                          <option key={r.collection.id} value={r.collection.id}>
                            {indentLabel(r)}
                          </option>
                        ))}
                    </select>
                  </label>
                )}
                {adding(c.id)}
                {messageFor(c.id)}
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
