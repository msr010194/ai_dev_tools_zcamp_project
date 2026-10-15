import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test } from "vitest";
import App from "./App";

test.each([
  ["/", "Home"],
  ["/timeline", "Timeline"],
  ["/tags", "Tags"],
  ["/collections", "Collections"],
])("route %s renders the %s page", (path, heading) => {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
});
