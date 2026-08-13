"use client";

import type { Filters } from "@/lib/types";

interface Props {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

// Filtres : surface min/max, score min, type d'operation, terrain vide seulement.
// Les 9 types d'operation sont listes tels que geres par le moteur de faisabilite
// (docs/FEASIBILITY_ENGINE.md) -- le filtre n'a d'effet qu'une fois
// suggested_operations alimente (voir docs/ROADMAP.md, hors MVP).
const OPERATION_TYPES = [
  "division_simple",
  "lotissement",
  "maisons_groupees",
  "petit_collectif",
  "immeuble_collectif",
  "demolition_reconstruction",
];

export default function FilterPanel({ filters, onChange }: Props) {
  return (
    <div className="section-block">
      <h2>Filtres</h2>
      <div className="field">
        <label htmlFor="min-score">Score minimum</label>
        <input
          id="min-score"
          type="number"
          min={0}
          max={100}
          value={filters.min_score ?? ""}
          onChange={(e) => onChange({ ...filters, min_score: e.target.value ? Number(e.target.value) : null })}
        />
      </div>
      <div className="field">
        <label htmlFor="min-area">Surface min (m2)</label>
        <input
          id="min-area"
          type="number"
          min={0}
          value={filters.min_area ?? ""}
          onChange={(e) => onChange({ ...filters, min_area: e.target.value ? Number(e.target.value) : null })}
        />
      </div>
      <div className="field">
        <label htmlFor="max-area">Surface max (m2)</label>
        <input
          id="max-area"
          type="number"
          min={0}
          value={filters.max_area ?? ""}
          onChange={(e) => onChange({ ...filters, max_area: e.target.value ? Number(e.target.value) : null })}
        />
      </div>
      <div className="field">
        <label htmlFor="operation-type">Type d&apos;operation</label>
        <select
          id="operation-type"
          value={filters.operation_type ?? ""}
          onChange={(e) => onChange({ ...filters, operation_type: e.target.value || null })}
        >
          <option value="">Tous</option>
          {OPERATION_TYPES.map((op) => (
            <option key={op} value={op}>
              {op.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="checkbox"
            checked={filters.vacant_only}
            onChange={(e) => onChange({ ...filters, vacant_only: e.target.checked })}
          />
          Terrain vide uniquement
        </label>
      </div>
    </div>
  );
}
