import type { MemoryFields } from "./types";

interface Props {
  value: MemoryFields;
  onChange: (value: MemoryFields) => void;
}

export default function MemoryFieldsForm({ value, onChange }: Props) {
  return (
    <>
      <label>
        When
        <input value={value.when} onChange={(e) => onChange({ ...value, when: e.target.value })} />
      </label>
      <label>
        Where
        <input value={value.where} onChange={(e) => onChange({ ...value, where: e.target.value })} />
      </label>
    </>
  );
}
