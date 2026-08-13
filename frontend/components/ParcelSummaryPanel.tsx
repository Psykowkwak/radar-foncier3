"use client";

import Link from "next/link";
import type { Opportunity } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

interface Props {
  parcel: Opportunity | null;
}

// Resume affiche quand une parcelle est selectionnee (clic liste ou clic carte).
export default function ParcelSummaryPanel({ parcel }: Props) {
  if (!parcel) {
    return <p style={{ color: "var(--color-text-muted)" }}>Selectionnez une parcelle sur la carte ou dans la liste.</p>;
  }
  return (
    <div className="section-block">
      <h2>Parcelle selectionnee</h2>
      <table className="kv-table">
        <tbody>
          <tr>
            <td>Reference</td>
            <td>{parcel.reference ?? "N/A"}</td>
          </tr>
          <tr>
            <td>Surface</td>
            <td>{parcel.parcel_area != null ? `${Math.round(parcel.parcel_area)} m2` : "Inconnue"}</td>
          </tr>
          <tr>
            <td>Categorie de bati</td>
            <td>{parcel.built_category ?? "Inconnue"}</td>
          </tr>
          <tr>
            <td>Constructibilite</td>
            <td>{parcel.constructibility_status}</td>
          </tr>
          <tr>
            <td>Score</td>
            <td>
              <ScoreBadge score={parcel.score_global} />
            </td>
          </tr>
        </tbody>
      </table>
      <div style={{ marginTop: 10 }}>
        <Link href={`/parcel/${parcel.parcel_id}`}>Voir la fiche complete &rarr;</Link>
      </div>
    </div>
  );
}
