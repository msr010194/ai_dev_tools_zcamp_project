import type { ReferenceFields, ReferenceKind } from "./types";

interface Props {
  value: ReferenceFields;
  onChange: (value: ReferenceFields) => void;
}

export default function ReferenceFieldsForm({ value, onChange }: Props) {
  return (
    <>
      <label>
        Sub-kind
        <select
          value={value.subKind}
          onChange={(e) => onChange({ ...value, subKind: e.target.value as ReferenceKind })}
        >
          <option value="written">Written</option>
          <option value="visual">Visual</option>
          <option value="audio">Audio</option>
        </select>
      </label>
      <label>
        Link
        <input value={value.link} onChange={(e) => onChange({ ...value, link: e.target.value })} />
      </label>
    </>
  );
}
