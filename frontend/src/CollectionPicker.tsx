import { flattenTree, indentLabel } from "./collectionTree";
import type { Collection } from "./data/types";

interface Props {
  collections: Collection[];
  value: string;
  onChange: (id: string) => void;
  label?: string;
  required?: boolean;
  emptyOption?: string;
}

export default function CollectionPicker({ collections, value, onChange, label = "Collection", required, emptyOption }: Props) {
  if (collections.length === 0) {
    return <p>No collections yet</p>;
  }
  return (
    <label>
      {label}
      <select value={value} required={required} aria-required={required} onChange={(e) => onChange(e.target.value)}>
        <option value="">{emptyOption ?? "Select a collection"}</option>
        {flattenTree(collections).map((row) => (
          <option key={row.collection.id} value={row.collection.id}>
            {indentLabel(row)}
          </option>
        ))}
      </select>
    </label>
  );
}
