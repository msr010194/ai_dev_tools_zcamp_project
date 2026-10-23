import { useEffect, useRef, useState } from "react";
import { useData } from "./data/DataContext";
import type { Collection, Note } from "./data/types";
import { preview } from "./noteUtils";
import { eligibleNotes, pickNotes } from "./resurface";

interface Props {
  random?: () => number;
  now?: () => number;
}

export default function ResurfacingPanel({ random = Math.random, now = Date.now }: Props) {
  const api = useData();
  const [shown, setShown] = useState<Note[] | null>(null);
  const [eligibleCount, setEligibleCount] = useState(0);
  const [collections, setCollections] = useState<Collection[]>([]);
  const started = useRef(false);
  const recorded = useRef<Note[] | null>(null);
  const pending = useRef<Promise<unknown>[]>([]);

  const choose = async (previousIds: string[]) => {
    await Promise.allSettled(pending.current);
    const [notes, cols] = await Promise.all([api.listNotes(), api.listCollections()]);
    const eligible = eligibleNotes(notes, now());
    setCollections(cols);
    setEligibleCount(eligible.length);
    setShown(pickNotes(eligible, previousIds, now(), random));
  };

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    choose([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Record each appearance once, not on every re-render.
  useEffect(() => {
    if (!shown || recorded.current === shown) return;
    recorded.current = shown;
    pending.current = shown.map((n) => api.markResurfaced(n.id).catch(() => undefined));
  }, [shown, api]);

  if (!shown) return null;

  return (
    <section aria-label="Resurfacing">
      <h2>Revisit</h2>
      {eligibleCount === 0 ? (
        <p>Nothing to revisit yet</p>
      ) : (
        <>
          <ul>
            {shown.map((n) => (
              <li key={n.id}>
                <strong>{n.type}</strong> · {collections.find((c) => c.id === n.collectionId)?.name ?? ""}
                <p>{preview(n.body)}</p>
              </li>
            ))}
          </ul>
          <button type="button" onClick={() => choose(shown.map((n) => n.id))}>
            Show another
          </button>
        </>
      )}
    </section>
  );
}
