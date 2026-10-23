import type { Note } from "./data/types";

export const SET_SIZE = 3;
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

export const eligibleNotes = (notes: Note[], now: number) =>
  notes.filter((n) => now - Date.parse(n.createdAt) > WEEK_MS);

// Never-resurfaced notes weigh most; a note resurfaced just now weighs least.
const weight = (n: Note, now: number) =>
  n.lastResurfacedAt === null ? 31 : 1 + Math.min(30, Math.max(0, (now - Date.parse(n.lastResurfacedAt)) / DAY_MS));

function weightedPick(pool: Note[], now: number, random: () => number): Note {
  const total = pool.reduce((sum, n) => sum + weight(n, now), 0);
  let r = random() * total;
  for (const n of pool) {
    r -= weight(n, now);
    if (r < 0) return n;
  }
  return pool[pool.length - 1];
}

/** Up to 3 distinct eligible notes, at least one Memory if any exists, avoiding `previousIds` when possible. */
export function pickNotes(eligible: Note[], previousIds: string[], now: number, random: () => number): Note[] {
  const target = Math.min(SET_SIZE, eligible.length);
  const fresh = eligible.filter((n) => !previousIds.includes(n.id));
  const candidates = fresh.length >= target ? fresh : eligible;
  const picked: Note[] = [];
  const take = (pool: Note[]) => {
    const available = pool.filter((n) => !picked.includes(n));
    if (available.length > 0 && picked.length < target) picked.push(weightedPick(available, now, random));
  };

  const memories = candidates.filter((n) => n.type === "memory");
  take(memories.length > 0 ? memories : eligible.filter((n) => n.type === "memory"));
  while (picked.length < target) {
    const before = picked.length;
    take(candidates);
    if (picked.length === before) take(eligible);
  }
  return picked;
}
