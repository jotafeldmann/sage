import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProductSearch } from "./ProductSearch";

describe("ProductSearch", () => {
  it("shows every product initially", () => {
    render(<ProductSearch />);

    expect(screen.getByText("Keyboard")).toBeInTheDocument();
    expect(screen.getByText("Monitor")).toBeInTheDocument();
    expect(screen.getByText("Mouse")).toBeInTheDocument();
  });

  it("narrows the visible products as you search, ignoring case", async () => {
    render(<ProductSearch />);

    await userEvent.type(screen.getByLabelText("Search products"), "MONIT");

    expect(screen.getByText("Monitor")).toBeInTheDocument();
    expect(screen.queryByText("Keyboard")).not.toBeInTheDocument();
    expect(screen.queryByText("Mouse")).not.toBeInTheDocument();
  });

  it("matches every product sharing a prefix, case-insensitively", async () => {
    render(<ProductSearch />);

    await userEvent.type(screen.getByLabelText("Search products"), "mo");

    expect(screen.getByText("Monitor")).toBeInTheDocument();
    expect(screen.getByText("Mouse")).toBeInTheDocument();
    expect(screen.queryByText("Keyboard")).not.toBeInTheDocument();
  });

  it("shows the empty state when nothing matches", async () => {
    render(<ProductSearch />);

    await userEvent.type(screen.getByLabelText("Search products"), "zzz");

    expect(screen.getByText("No products found")).toBeInTheDocument();
  });
});
