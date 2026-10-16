import { useEffect, useState, type ComponentProps } from "react";
import CollectionPicker from "./CollectionPicker";
import TagPicker from "./TagPicker";
import { useData } from "./data/DataContext";
import type { Collection, Note, NoteType, Tag } from "./data/types";
import TypeFields from "./fields/TypeFields";
import { emptyFields, type TypeFieldValue } from "./fields/types";

interface Props {
  type: NoteType;
  note?: Note;
  /** Type-specific values already stored for the note (the Note shape has no place for them yet). */
  initialFields?: TypeFieldValue;
  onSaved: (note: Note) => void;
}

export default function NoteEditor({ type: typeProp, note, initialFields, onSaved }: Props) {
  const api = useData();
  const type = note?.type ?? typeProp;
  const [collections, setCollections] = useState<Collection[] | null>(null);
  const [tags, setTags] = useState<Tag[]>([]);
  const [body, setBody] = useState(note?.body ?? "");
  const [collectionId, setCollectionId] = useState("");
  const [tagIds, setTagIds] = useState<string[]>([]);
  const [fields, setFields] = useState<TypeFieldValue>(initialFields ?? emptyFields(type));
  const [bodyError, setBodyError] = useState("");
  const [collectionError, setCollectionError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const promptLocked =
    !!note && !!initialFields && "prompt" in initialFields && (initialFields as { prompt: string }).prompt !== "";

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.listCollections(), api.listTags()]).then(([cs, ts]) => {
      if (cancelled) return;
      setCollections(cs);
      setTags(ts);
      // References to deleted collections/tags are dropped.
      if (note && cs.some((c) => c.id === note.collectionId)) setCollectionId(note.collectionId);
      if (note) setTagIds(note.tagIds.filter((id) => ts.some((t) => t.id === id)));
    });
    return () => {
      cancelled = true;
    };
  }, [api, note]);

  if (collections === null) return <p>Loading…</p>;

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    const bodyMissing = body.trim() === "";
    const collectionMissing = collectionId === "";
    setBodyError(bodyMissing ? "Body is required" : "");
    setCollectionError(collectionMissing ? "A Collection is required" : "");
    if (bodyMissing || collectionMissing) return;
    setSaving(true);
    setSaveError("");
    try {
      const saved = note
        ? await api.updateNote(note.id, { body, collectionId, tagIds })
        : await api.createNote({ type, body, collectionId, tagIds });
      onSaved(saved);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Could not save the note");
    } finally {
      setSaving(false);
    }
  };

  const typeFieldProps = {
    type,
    value: fields,
    onChange: setFields,
    promptLocked,
  } as ComponentProps<typeof TypeFields>;

  return (
    <form onSubmit={save} noValidate>
      <p>Type: {type[0].toUpperCase() + type.slice(1)}</p>
      <label>
        Body
        <textarea value={body} onChange={(e) => setBody(e.target.value)} />
      </label>
      {bodyError && <p role="alert">{bodyError}</p>}
      <CollectionPicker collections={collections} value={collectionId} onChange={setCollectionId} required />
      {collectionError && <p role="alert">{collectionError}</p>}
      <TagPicker tags={tags} selected={tagIds} onChange={setTagIds} />
      <TypeFields {...typeFieldProps} />
      {saveError && <p role="alert">{saveError}</p>}
      <button type="submit" disabled={saving}>
        Save
      </button>
    </form>
  );
}
