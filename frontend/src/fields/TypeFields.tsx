import type { NoteType } from "../data/types";
import JournalFieldsForm from "./JournalFieldsForm";
import MemoryFieldsForm from "./MemoryFieldsForm";
import PlanFieldsForm from "./PlanFieldsForm";
import ReferenceFieldsForm from "./ReferenceFieldsForm";
import type { FieldsByType } from "./types";

type Props = {
  [T in NoteType]: {
    type: T;
    value: FieldsByType[T];
    onChange: (value: FieldsByType[T]) => void;
    promptLocked?: boolean;
  };
}[NoteType];

export default function TypeFields(props: Props) {
  switch (props.type) {
    case "journal":
      return (
        <JournalFieldsForm value={props.value} onChange={props.onChange} promptLocked={props.promptLocked} />
      );
    case "reference":
      return <ReferenceFieldsForm value={props.value} onChange={props.onChange} />;
    case "plan":
      return <PlanFieldsForm value={props.value} onChange={props.onChange} />;
    case "memory":
      return <MemoryFieldsForm value={props.value} onChange={props.onChange} />;
    case "idea":
      return null;
  }
}
