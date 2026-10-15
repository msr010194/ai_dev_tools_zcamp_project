export type NoteType = "journal" | "idea" | "reference" | "plan" | "memory";

export interface Collection {
  id: string;
  name: string;
  parentId: string | null;
}

export interface Tag {
  id: string;
  name: string;
}

export interface Note {
  id: string;
  type: NoteType;
  body: string;
  collectionId: string;
  tagIds: string[];
  createdAt: string;
}

export type NewNote = Omit<Note, "id" | "createdAt">;

export interface DataApi {
  listCollections(): Promise<Collection[]>;
  createCollection(name: string, parentId: string | null): Promise<Collection>;
  renameCollection(id: string, name: string): Promise<Collection>;
  moveCollection(id: string, parentId: string | null): Promise<Collection>;
  deleteCollection(id: string): Promise<void>;

  listTags(): Promise<Tag[]>;
  createTag(name: string): Promise<Tag>;
  renameTag(id: string, name: string): Promise<Tag>;

  listNotes(): Promise<Note[]>;
  getNote(id: string): Promise<Note | undefined>;
  createNote(note: NewNote): Promise<Note>;
  updateNote(id: string, patch: Partial<NewNote>): Promise<Note>;
  deleteNote(id: string): Promise<void>;
}
