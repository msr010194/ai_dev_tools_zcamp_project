import type { PlanFields, PlanState } from "./types";

interface Props {
  value: PlanFields;
  onChange: (value: PlanFields) => void;
}

export default function PlanFieldsForm({ value, onChange }: Props) {
  const setItem = (index: number, patch: Partial<PlanFields["checklist"][number]>) =>
    onChange({
      ...value,
      checklist: value.checklist.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    });

  return (
    <>
      <label>
        Target date
        <input
          type="date"
          value={value.targetDate}
          onChange={(e) => onChange({ ...value, targetDate: e.target.value })}
        />
      </label>
      <label>
        State
        <select
          value={value.state}
          onChange={(e) => onChange({ ...value, state: e.target.value as PlanState })}
        >
          <option value="not_started">Not started</option>
          <option value="in_progress">In progress</option>
          <option value="done">Done</option>
          <option value="abandoned">Abandoned</option>
        </select>
      </label>
      <fieldset>
        <legend>Checklist</legend>
        <ul>
          {value.checklist.map((item, i) => (
            <li key={i}>
              <input
                type="checkbox"
                aria-label={`Item ${i + 1} done`}
                checked={item.done}
                onChange={(e) => setItem(i, { done: e.target.checked })}
              />
              <input
                aria-label={`Item ${i + 1} text`}
                value={item.text}
                onChange={(e) => setItem(i, { text: e.target.value })}
              />
              <button
                type="button"
                aria-label={`Remove item ${i + 1}`}
                onClick={() => onChange({ ...value, checklist: value.checklist.filter((_, j) => j !== i) })}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={() => onChange({ ...value, checklist: [...value.checklist, { text: "", done: false }] })}
        >
          Add item
        </button>
      </fieldset>
    </>
  );
}
