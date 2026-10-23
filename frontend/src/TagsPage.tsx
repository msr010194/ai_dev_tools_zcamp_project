import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useData } from "./data/DataContext";
import type { Note, Tag } from "./data/types";

export default function TagsPage() {
  const api = useData();
  const [tags, setTags] = useState<Tag[] | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [newName, setNewName] = useState("");
  const [editing, setEditing] = useState<{ id: string; name: string } | null>(null);
  const [message, setMessage] = useState<{ key: string; text: string } | null>(null);
  const [loadError, setLoadError] = useState("");

  // On a failed load the list is hidden rather than left stale.
  const refresh = useCallback(async () => {
    try {
      const [t, n] = await Promise.all([api.listTags(), api.listNotes()]);
      setTags(t);
      setNotes(n);
      setLoadError("");
    } catch (err) {
      setTags(null);
      setLoadError(err instanceof Error ? err.message : "Something went wrong");
    }
  }, [api]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loadError) {
    return (
      <>
        <h1>Tags</h1>
        <p role="alert">Could not load tags: {loadError}</p>
        <button type="button" onClick={() => refresh()}>
          Retry
        </button>
      </>
    );
  }
  if (!tags) return <h1>Tags</h1>;

  const check = (key: string, raw: string, excludeId?: string): string | null => {
    const name = raw.trim();
    if (name === "") {
      setMessage({ key, text: "Name is required" });
      return null;
    }
    if (tags.some((t) => t.id !== excludeId && t.name.toLowerCase() === name.toLowerCase())) {
      setMessage({ key, text: "That tag already exists" });
      return null;
    }
    return name;
  };

  const attempt = async (key: string, fn: () => Promise<unknown>) => {
    try {
      await fn();
      return true;
    } catch (err) {
      setMessage({ key, text: err instanceof Error ? err.message : "Something went wrong" });
      return false;
    }
  };

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    const name = check("new", newName);
    if (!name) return;
    if (await attempt("new", () => api.createTag(name))) {
      setNewName("");
      await refresh();
    }
  };

  const rename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    setMessage(null);
    const name = check(editing.id, editing.name, editing.id);
    if (!name) return;
    if (await attempt(editing.id, () => api.renameTag(editing.id, name))) {
      setEditing(null);
      await refresh();
    }
  };

  const sorted = [...tags].sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
  const messageFor = (key: string) => (message?.key === key ? <p role="alert">{message.text}</p> : null);

  return (
    <>
      <h1>Tags</h1>
      <form onSubmit={create}>
        <input aria-label="New tag name" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button type="submit">Create tag</button>
      </form>
      {messageFor("new")}
      {sorted.length === 0 ? (
        <p>No tags yet</p>
      ) : (
        <ul>
          {sorted.map((t) => (
            <li key={t.id}>
              {editing?.id === t.id ? (
                <form style={{ display: "inline" }} onSubmit={rename}>
                  <input
                    aria-label={`Rename ${t.name}`}
                    autoFocus
                    value={editing.name}
                    onChange={(e) => setEditing({ id: t.id, name: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === "Escape") {
                        setEditing(null);
                        setMessage(null);
                      }
                    }}
                  />
                </form>
              ) : (
                <>
                  <Link to={`/timeline?tag=${t.id}`}>{t.name}</Link> ({notes.filter((n) => n.tagIds.includes(t.id)).length}){" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMessage(null);
                      setEditing({ id: t.id, name: t.name });
                    }}
                  >
                    Rename
                  </button>
                </>
              )}
              {messageFor(t.id)}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
