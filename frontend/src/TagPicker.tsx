import type { Tag } from "./data/types";

interface Props {
  tags: Tag[];
  selected: string[];
  onChange: (ids: string[]) => void;
}

export default function TagPicker({ tags, selected, onChange }: Props) {
  if (tags.length === 0) {
    return <p>No tags yet</p>;
  }
  const toggle = (id: string, on: boolean) =>
    onChange(on ? [...selected, id] : selected.filter((s) => s !== id));
  return (
    <fieldset>
      <legend>Tags</legend>
      {tags.map((t) => (
        <label key={t.id} style={{ marginRight: 12 }}>
          <input type="checkbox" checked={selected.includes(t.id)} onChange={(e) => toggle(t.id, e.target.checked)} />
          {t.name}
        </label>
      ))}
    </fieldset>
  );
}
