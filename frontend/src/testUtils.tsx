import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { DataProvider } from "./data/DataContext";
import type { DataApi } from "./data/types";

export function renderWithApp(ui: ReactElement, api: DataApi, route = "/") {
  return render(
    <DataProvider api={api}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </DataProvider>,
  );
}
