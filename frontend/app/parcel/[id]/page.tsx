"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getParcel } from "@/lib/api";
import type { ParcelDetail } from "@/lib/types";
import ScoreBadge from "@/components/ScoreBadge";

export default function ParcelPage() {
  const params = useParams<{ id: string }>();
  const [parcel, setParcel] = useState<ParcelDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id) return;
    getParcel(params.id)
      .then(setParcel)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur de chargement"));
  }, [params?.id]);

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Link href="/">&larr; Retour</Link>
        <div className="warning-box" style={{ marginTop: 16 }}>
          {error}
        </div>
      </div>
    );
  }

  if (!parcel) {
    return (
      <div style={{ padding: 24 }}>
        <Link href="/">&larr; Retour</Link>
        <p>Chargement...</p>
      </div>
    );
  }

  const { analysis, score } = parcel;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <Link href="/">&larr; Retour a la carte</Link>
      <h1 style={{ fontSize: 22, marginTop: 12 }}>
        Parcelle {parcel.reference ?? parcel.id} -- {parcel.municipality_name}
      </h1>

      {score && (
        <div style={{ margin: "12px 0" }}>
          <ScoreBadge score={score.score_global} />
        </div>
      )}

      {parcel.warnings.length > 0 && (
        <div className="warning-box">
          <strong>Avertissements</strong>
          <ul style={{ margin: "4px 0 0 18px" }}>
            {parcel.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 16 }}>
        <section>
          <h2>Identite</h2>
          <table className="kv-table">
            <tbody>
              <tr>
                <td>Section</td>
                <td>{parcel.section ?? "N/A"}</td>
              </tr>
              <tr>
                <td>Numero</td>
                <td>{parcel.numero ?? "N/A"}</td>
              </tr>
              <tr>
                <td>Surface officielle (DGFiP)</td>
                <td>{parcel.area_official != null ? `${parcel.area_official} m2` : "Inconnue"}</td>
              </tr>
              <tr>
                <td>Surface calculee</td>
                <td>{parcel.area_computed != null ? `${Math.round(parcel.area_computed)} m2` : "Inconnue"}</td>
              </tr>
            </tbody>
          </table>

          <h2 style={{ marginTop: 20 }}>Urbanisme</h2>
          <table className="kv-table">
            <tbody>
              <tr>
                <td>Zone</td>
                <td>{parcel.typezone ? `${parcel.typezone} (${parcel.zone_libelle ?? ""})` : "Non determinee"}</td>
              </tr>
              <tr>
                <td>Statut de constructibilite</td>
                <td>{analysis?.constructibility_status ?? "DONNEES_INSUFFISANTES"}</td>
              </tr>
              <tr>
                <td>Confiance urbanisme</td>
                <td>
                  {analysis?.urbanism_confidence_score != null
                    ? `${Math.round(analysis.urbanism_confidence_score)}/100 (reglement non analyse au MVP)`
                    : "N/A"}
                </td>
              </tr>
            </tbody>
          </table>

          <h2 style={{ marginTop: 20 }}>Terrain</h2>
          <table className="kv-table">
            <tbody>
              <tr>
                <td>Largeur estimee</td>
                <td>{analysis?.width_estimated != null ? `${analysis.width_estimated.toFixed(1)} m` : "N/A"}</td>
              </tr>
              <tr>
                <td>Profondeur estimee</td>
                <td>{analysis?.depth_estimated != null ? `${analysis.depth_estimated.toFixed(1)} m` : "N/A"}</td>
              </tr>
              <tr>
                <td>Qualite geometrique</td>
                <td>{analysis?.geometry_quality_score != null ? `${Math.round(analysis.geometry_quality_score)}/100` : "N/A"}</td>
              </tr>
              <tr>
                <td>Contact voie</td>
                <td>{analysis?.road_frontage_length != null ? `${analysis.road_frontage_length.toFixed(1)} m` : "Inconnu (pas de couche voirie au MVP)"}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section>
          <h2>Bati</h2>
          <table className="kv-table">
            <tbody>
              <tr>
                <td>Categorie</td>
                <td>{analysis?.built_category ?? "Inconnue"}</td>
              </tr>
              <tr>
                <td>Emprise batie</td>
                <td>
                  {analysis?.building_coverage_ratio != null
                    ? `${Math.round(analysis.building_coverage_ratio * 100)} %`
                    : "Inconnue"}
                </td>
              </tr>
              <tr>
                <td>Surface non batie</td>
                <td>{analysis?.unbuilt_area != null ? `${Math.round(analysis.unbuilt_area)} m2` : "Inconnue"}</td>
              </tr>
              <tr>
                <td>Plus grande surface libre contigue</td>
                <td>
                  {analysis?.largest_contiguous_unbuilt_area != null
                    ? `${Math.round(analysis.largest_contiguous_unbuilt_area)} m2`
                    : "Inconnue"}
                </td>
              </tr>
            </tbody>
          </table>

          <h2 style={{ marginTop: 20 }}>Risques</h2>
          <p style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
            score_risques : {score ? `${Math.round(score.score_risques)}/100` : "N/A"} -- calcule uniquement si
            Georisques a repondu pour la commune (RGA/cavites), sinon valeur neutre documentee.
          </p>

          {score && (
            <>
              <h2 style={{ marginTop: 20 }}>Score detaille</h2>
              <table className="kv-table">
                <tbody>
                  <tr>
                    <td>Urbanisme</td>
                    <td>{Math.round(score.score_urbanisme)}</td>
                  </tr>
                  <tr>
                    <td>Geometrie</td>
                    <td>{Math.round(score.score_geometrie)}</td>
                  </tr>
                  <tr>
                    <td>Surface</td>
                    <td>{Math.round(score.score_surface)}</td>
                  </tr>
                  <tr>
                    <td>Acces (donnees insuffisantes au MVP)</td>
                    <td>{Math.round(score.score_acces)}</td>
                  </tr>
                  <tr>
                    <td>Reseaux (donnees insuffisantes au MVP)</td>
                    <td>{Math.round(score.score_reseaux)}</td>
                  </tr>
                  <tr>
                    <td>Risques</td>
                    <td>{Math.round(score.score_risques)}</td>
                  </tr>
                  <tr>
                    <td>Densification</td>
                    <td>{Math.round(score.score_densification)}</td>
                  </tr>
                  <tr>
                    <td>Complexite (donnees insuffisantes au MVP)</td>
                    <td>{Math.round(score.score_complexite)}</td>
                  </tr>
                  <tr>
                    <td>Qualite des donnees</td>
                    <td>{Math.round(score.score_qualite_donnees)}</td>
                  </tr>
                </tbody>
              </table>
              {score.explanation_text && (
                <p style={{ fontSize: 13, marginTop: 10, lineHeight: 1.5 }}>{score.explanation_text}</p>
              )}
            </>
          )}

          <h2 style={{ marginTop: 20 }}>Sources</h2>
          {parcel.sources.length > 0 ? (
            <ul style={{ fontSize: 13, margin: 0, paddingLeft: 18 }}>
              {parcel.sources.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Aucune source enregistree.</p>
          )}
        </section>
      </div>

      <div style={{ marginTop: 28, marginBottom: 40 }}>
        <button className="btn-primary" disabled title="Disponible en V2 -- moteur de faisabilite non implemente au MVP">
          Lancer une faisabilite
        </button>
      </div>
    </div>
  );
}
