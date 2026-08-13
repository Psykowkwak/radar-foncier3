"use client";

import { useEffect, useRef, useState } from "react";
import { searchMunicipalities } from "@/lib/api";
import type { MunicipalitySearchResult } from "@/lib/types";

interface Props {
  onSelect: (municipality: MunicipalitySearchResult) => void;
}

// Autocomplete commune -- appelle GET /api/municipalities/search (backend), qui
// relaie vers le geocodage Geoplateforme (voir docs/DATA_SOURCES.md C.1).
// Debounce 300ms pour rester tres en dessous de la limite documentee (50 req/s/IP).
export default function MunicipalitySearch({ onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MunicipalitySearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchMunicipalities(query);
        setResults(res);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  return (
    <div className="field">
      <label htmlFor="municipality-search">Commune</label>
      <input
        id="municipality-search"
        type="text"
        placeholder="Rechercher une commune..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {loading && <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>Recherche...</div>}
      {results.length > 0 && (
        <ul
          style={{
            listStyle: "none",
            margin: "4px 0 0 0",
            padding: 0,
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius)",
            maxHeight: 220,
            overflowY: "auto",
          }}
        >
          {results.map((r) => (
            <li
              key={r.insee_code}
              onClick={() => {
                onSelect(r);
                setQuery(`${r.name} (${r.postcode ?? r.insee_code})`);
                setResults([]);
              }}
              style={{ padding: "6px 8px", cursor: "pointer", borderBottom: "1px solid var(--color-border)" }}
            >
              {r.name} {r.postcode ? `(${r.postcode})` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
