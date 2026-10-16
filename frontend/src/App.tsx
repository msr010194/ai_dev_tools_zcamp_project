import { Route, Routes } from "react-router-dom";
import CollectionsPage from "./CollectionsPage";
import HomePage from "./HomePage";
import Layout from "./Layout";
import NewNotePage from "./NewNotePage";
import TagsPage from "./TagsPage";
import TimelinePage from "./TimelinePage";

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
