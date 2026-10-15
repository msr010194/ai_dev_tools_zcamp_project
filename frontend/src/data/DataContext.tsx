import { createContext, useContext, type ReactNode } from "react";
import type { DataApi } from "./types";

const DataContext = createContext<DataApi | null>(null);

export function DataProvider({ api, children }: { api: DataApi; children: ReactNode }) {
  return <DataContext.Provider value={api}>{children}</DataContext.Provider>;
}

export function useData(): DataApi {
  const api = useContext(DataContext);
  if (!api) throw new Error("useData must be used within a DataProvider");
  return api;
}
