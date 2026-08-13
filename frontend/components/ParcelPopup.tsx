"use client";

import type { Opportunity } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

interface Props {
  parcel: Opportunity;
}

// Contenu de la popup affichee au clic sur une parcelle de la carte (utilise par
// MapView si une popup MapLibre est souhaitee en plus du panneau lateral --
// composant garde separe pour reutilisation independante).
export default function ParcelPopup({ parcel }: Props) {
  return (
    <div style={{ minWidth: 180 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{parcel.reference ?? "Parcelle"}</div>
      <div style={{ marginBottom: 4 }}>
        <ScoreBadge score={parcel.score_global} />
      </div>
      <div style={{ fontSize: 12 }}>
        {parcel.parcel_area != null ? `${Math.round(parcel.parcel_area)} m2` : "Surface inconnue"}
      </div>
    </div>
  );
}
