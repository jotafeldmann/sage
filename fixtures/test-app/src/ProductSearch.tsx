import { useMemo, useState } from "react";

import { products } from "./products";

export function ProductSearch() {
  const [query, setQuery] = useState("");

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return products;
    }
    return products.filter((product) => product.name.toLowerCase().includes(needle));
  }, [query]);

  return (
    <section>
      <label htmlFor="product-search">Search products</label>
      <input
        id="product-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />

      {visible.length === 0 ? (
        <p>No products found</p>
      ) : (
        <ul>
          {visible.map((product) => (
            <li key={product.id}>{product.name}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
