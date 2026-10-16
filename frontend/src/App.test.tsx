import { screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";
import { createMockApi } from "./data/mockApi";
import { renderWithApp } from "./testUtils";

test.each([
  ["/", "Home"],
  ["/timeline", "Timeline"],
  ["/tags", "Tags"],
  ["/collections", "Collections"],
])("route %s renders the %s page", (path, heading) => {
  renderWithApp(<App />, createMockApi(), path);
  expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
});
