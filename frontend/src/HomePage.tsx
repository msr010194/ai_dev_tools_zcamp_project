import { Link, useNavigate } from "react-router-dom";
import type { NoteType } from "./data/types";

const captureTypes: { type: NoteType; label: string }[] = [
  { type: "idea", label: "Idea" },
  { type: "reference", label: "Reference" },
  { type: "plan", label: "Plan" },
];

export default function HomePage() {
  const navigate = useNavigate();
  const captureType: NoteType = "idea";
  return (
    <>
      <h1>Home</h1>
      <section aria-label="Capture">
        <h2>
          <Link to={`/notes/new?type=${captureType}`}>Capture</Link>
        </h2>
        <p>Jot down an idea, reference, or plan.</p>
        <div role="group" aria-label="Capture as">
          {captureTypes.map((c) => (
            <button
              key={c.type}
              type="button"
              aria-pressed={c.type === captureType}
              onClick={() => navigate(`/notes/new?type=${c.type}`)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </section>
      <section aria-label="Reflect">
        <h2>
          <Link to="/notes/new?type=journal">Reflect</Link>
        </h2>
        <p>Write a journal entry about how things are going.</p>
      </section>
      <section aria-label="Preserve">
        <h2>
          <Link to="/notes/new?type=memory">Preserve</Link>
        </h2>
        <p>Keep a memory worth remembering.</p>
      </section>
    </>
  );
}
