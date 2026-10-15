import type { Collection, DataApi, Note, Tag } from "./types";

export function createMockApi(): DataApi {
  let seq = 0;
  const nextId = () => String(++seq);
  const collections: Collection[] = [];
  const tags: Tag[] = [];
  const notes: Note[] = [];

  const find = <T extends { id: string }>(items: T[], id: string, what: string): T => {
    const item = items.find((i) => i.id === id);
    if (!item) throw new Error(`${what} ${id} not found`);
    return item;
  };

  return {
    async listCollections() {
      return collections.map((c) => ({ ...c }));
    },
    async createCollection(name, parentId) {
      const c = { id: nextId(), name, parentId };
      collections.push(c);
      return { ...c };
    },
    async renameCollection(id, name) {
      const c = find(collections, id, "Collection");
      c.name = name;
      return { ...c };
    },
    async moveCollection(id, parentId) {
      const c = find(collections, id, "Collection");
      c.parentId = parentId;
      return { ...c };
    },
    async deleteCollection(id) {
      find(collections, id, "Collection");
      if (collections.some((c) => c.parentId === id) || notes.some((n) => n.collectionId === id)) {
        throw new Error("Collection is not empty");
      }
      collections.splice(collections.findIndex((c) => c.id === id), 1);
    },

    async listTags() {
      return tags.map((t) => ({ ...t }));
    },
    async createTag(name) {
      if (tags.some((t) => t.name.toLowerCase() === name.toLowerCase())) {
        throw new Error("Tag already exists");
      }
      const t = { id: nextId(), name };
      tags.push(t);
      return { ...t };
    },
    async renameTag(id, name) {
      const t = find(tags, id, "Tag");
      t.name = name;
      return { ...t };
    },

    async listNotes() {
      return notes.map((n) => ({ ...n }));
    },
    async getNote(id) {
      const n = notes.find((x) => x.id === id);
      return n && { ...n };
    },
    async createNote(note) {
      const n = { ...note, id: nextId(), createdAt: new Date().toISOString() };
      notes.push(n);
      return { ...n };
    },
    async updateNote(id, patch) {
      const n = find(notes, id, "Note");
      Object.assign(n, patch);
      return { ...n };
    },
    async deleteNote(id) {
      find(notes, id, "Note");
      notes.splice(notes.findIndex((n) => n.id === id), 1);
    },
  };
}
