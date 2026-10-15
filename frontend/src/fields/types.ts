import type { NoteType } from "../data/types";

export type RetroPeriod = "weekly" | "monthly";
export type ReferenceKind = "written" | "visual" | "audio";
export type PlanState = "not_started" | "in_progress" | "done" | "abandoned";

export interface ChecklistItem {
  text: string;
  done: boolean;
}

export interface JournalFields {
  mood: string;
  prompt: string;
  isRetrospective: boolean;
  period: RetroPeriod | "";
}

export interface ReferenceFields {
  subKind: ReferenceKind;
  link: string;
}

export interface PlanFields {
  targetDate: string;
  state: PlanState;
  checklist: ChecklistItem[];
}

export interface MemoryFields {
  when: string;
  where: string;
}

export interface FieldsByType {
  journal: JournalFields;
  idea: Record<string, never>;
  reference: ReferenceFields;
  plan: PlanFields;
  memory: MemoryFields;
}

export type TypeFieldValue = FieldsByType[NoteType];

export function emptyFields<T extends NoteType>(type: T): FieldsByType[T];
export function emptyFields(type: NoteType): TypeFieldValue {
  switch (type) {
    case "journal":
      return { mood: "", prompt: "", isRetrospective: false, period: "" };
    case "reference":
      return { subKind: "written", link: "" };
    case "plan":
      return { targetDate: "", state: "not_started", checklist: [] };
    case "memory":
      return { when: "", where: "" };
    case "idea":
      return {};
  }
}
