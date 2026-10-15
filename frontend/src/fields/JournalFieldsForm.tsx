import type { JournalFields, RetroPeriod } from "./types";

interface Props {
  value: JournalFields;
  onChange: (value: JournalFields) => void;
  /** Once a prompt has been saved it can no longer be edited. */
  promptLocked?: boolean;
}

export default function JournalFieldsForm({ value, onChange, promptLocked = false }: Props) {
  return (
    <>
      <label>
        Mood
        <input value={value.mood} onChange={(e) => onChange({ ...value, mood: e.target.value })} />
      </label>
      <label>
        Prompt
        <input
          value={value.prompt}
          readOnly={promptLocked}
          onChange={(e) => onChange({ ...value, prompt: e.target.value })}
        />
      </label>
      <label>
        <input
          type="checkbox"
          checked={value.isRetrospective}
          onChange={(e) =>
            onChange({
              ...value,
              isRetrospective: e.target.checked,
              period: e.target.checked ? value.period : "",
            })
          }
        />
        Retrospective
      </label>
      {value.isRetrospective && (
        <label>
          Period
          <select
            value={value.period}
            onChange={(e) => onChange({ ...value, period: e.target.value as RetroPeriod | "" })}
          >
            <option value="">Select…</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
      )}
    </>
  );
}
