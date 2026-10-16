import { Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import HomePage from "./HomePage";
import NewNotePage from "./NewNotePage";
import { CollectionsPage, TagsPage, TimelinePage } from "./pages";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="notes/new" element={<NewNotePage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="tags" element={<TagsPage />} />
        <Route path="collections" element={<CollectionsPage />} />
      </Route>
    </Routes>
  );
}
