import { useState } from "react";
import { loadFilters, saveFilters, type SearchFilters } from "../lib/searchFilters";

export function useSearchFilters() {
  const [filters, setFilters] = useState<SearchFilters>(loadFilters);

  const update = (next: SearchFilters) => {
    setFilters(next);
    saveFilters(next);
  };

  return { filters, update };
}
