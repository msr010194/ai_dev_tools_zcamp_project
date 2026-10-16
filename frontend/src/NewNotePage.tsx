import { useNavigate, useSearchParams } from "react-router-dom";
import NoteEditor from "./NoteEditor";
import type { NoteType } from "./data/types";

const types: NoteType[] = ["journal", "idea", "reference", "plan", "memory"];

export default function NewNotePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const requested = params.get("type");
  const type = types.find((t) => t === requested) ?? "idea";
  return (
    <>
      <h1>New note</h1>
      <NoteEditor key={type} type={type} onSaved={() => navigate("/")} />
    </>
  );
}
