"""Export extraction.

A missed export costs context quality, never correctness - the validator remains
the authority. So these tests care most about not *lying*: never inventing an
export, never leaking an implementation body.
"""

from __future__ import annotations

import pytest

from sage.tools.signatures import MAX_DECLARATION_CHARS, describe_module, extract_exports


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("export interface Product { id: string }", ["interface Product"]),
        (
            "export type Filter = (p: Product) => boolean;",
            ["type Filter = (p: Product) => boolean"],
        ),
        ("export const products: Product[] = [];", ["const products: Product[]"]),
        ("export class Store {}", ["class Store"]),
        ("export enum Mode { A, B }", ["enum Mode { A, B }"]),
        ("export function noop() {}", ["function noop()"]),
        (
            "export async function load(id: string): Promise<Product> { return x; }",
            ["async function load(id: string): Promise<Product>"],
        ),
        ("export default Thing;", ["default Thing"]),
        ("export { helper, other as renamed };", ["helper", "other as renamed"]),
        ('export * from "./other";', ['export * from "./other"']),
    ],
)
def test_each_export_form_is_recognised(source: str, expected: list[str]) -> None:
    assert extract_exports(source) == expected


def test_a_destructured_parameter_list_is_kept_whole() -> None:
    """Braces in parameters must not be mistaken for the function body."""
    source = "export function Widget({ items, onPick }: WidgetProps): JSX.Element { return null; }"

    assert extract_exports(source) == [
        "function Widget({ items, onPick }: WidgetProps): JSX.Element"
    ]


def test_implementation_bodies_are_never_included() -> None:
    source = """export function total(items: Item[]) {
  const secret = "should-not-appear";
  return items.length;
}
"""
    rendered = "\n".join(extract_exports(source))

    assert "should-not-appear" not in rendered
    assert rendered == "function total(items: Item[])"


def test_non_exported_declarations_are_ignored() -> None:
    source = """const internal = 1;
function alsoInternal() {}
export const shown = 2;
"""

    assert extract_exports(source) == ["const shown"]


def test_imports_are_not_mistaken_for_exports() -> None:
    source = 'import { useState } from "react";\nexport const x = 1;\n'

    exports = extract_exports(source)

    assert "useState" not in "\n".join(exports)


def test_a_very_long_declaration_is_capped() -> None:
    options = "|".join(f'"opt{i}"' for i in range(80))
    source = f"export type Wide = {options};"

    (rendered,) = extract_exports(source)

    assert len(rendered) <= MAX_DECLARATION_CHARS + 4
    assert rendered.endswith("...")


def test_a_module_with_no_exports_is_skipped() -> None:
    assert describe_module("src/main.tsx", 'import "./x";\nconsole.log(1);\n') is None


def test_non_source_files_are_skipped() -> None:
    assert describe_module("package.json", '{"name": "x"}') is None
    assert describe_module("README.md", "export const fake = 1;") is None


def test_a_module_is_rendered_with_its_path() -> None:
    rendered = describe_module("src/products.ts", "export const products = [];")

    assert rendered is not None
    assert rendered.startswith("src/products.ts exports:")
    assert "const products" in rendered
