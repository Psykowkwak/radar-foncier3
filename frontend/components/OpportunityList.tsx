"use client";

import Link from "next/link";
import type { Opportunity } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

interface Props {
  opportunities: Opportunity[];
  selectedParcelId: string | null;
  onSelect: (parcelId: string) => void;
}

// Liste triee (deja triee par score_global desc cote API), clic -> selectionne +
// zoom carte (etat leve dans app/page.tsx, partage entre MapView et OpportunityList).
export default function OpportunityList({ opportunities, selectedParcelId, onSelect }: Props) {
  if (opportunities.length === 0) {
    return <p style={{ color: "var(--color-text-muted)" }}>Aucune opportunite pour ces filtres.</p>;
  }

  return (
    <div>
      {opportunities.map((opp) => (
        <div
          key={opp.parcel_id}
          className={`opportunity-item${selectedParcelId === opp.parcel_id ? " selected" : ""}`}
          onClick={() => onSelect(opp.parcel_id)}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <strong>{opp.reference ?? "Parcelle"}</strong>
            <ScoreBadge score={opp.score_global} />
          </div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
            {opp.parcel_area != null ? `${Math.round(opp.parcel_area)} m2` : "Surface inconnue"}
            {opp.built_category ? ` · ${opp.built_category}` : ""}
          </div>
          <div style={{ fontSize: 12, marginTop: 4 }}>
            <Link href={`/parcel/${opp.parcel_id}`} onClick={(e) => e.stopPropagation()}>
              Voir la fiche complete &rarr;
            </Link>
          </div>
        </div>
      ))}
    </div>
  );
}
