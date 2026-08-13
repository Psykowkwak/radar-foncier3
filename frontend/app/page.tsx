"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getAnalysisJob, getOpportunities, getTopOpportunities, launchAnalysis } from "@/lib/api";
import type { AnalysisJob, Filters, MunicipalitySearchResult, Opportunity } from "@/lib/types";
import MunicipalitySearch from "@/components/MunicipalitySearch";
import FilterPanel from "@/components/FilterPanel";
import MapView from "@/components/MapView";
import OpportunityList from "@/components/OpportunityList";
import ParcelSummaryPanel from "@/components/ParcelSummaryPanel";

// Score minimum par defaut a 60 : "parcelles_selectionnees" (retenues) ne signifie
// que "non exclue d'office" (voir docs/SCORING_ENGINE.md), pas "bonne opportunite"
// -- sur une grande commune, la quasi-totalite des parcelles est "retenue" au sens
// strict. Sans un filtre par defaut, la premiere liste affichee est illisible
// (plusieurs milliers d'items) et peu utile. L'utilisateur peut redescendre le
// filtre a 0 pour tout voir.
const DEFAULT_FILTERS: Filters = {
  min_score: 60,
  min_area: null,
  max_area: null,
  operation_type: null,
  vacant_only: false,
};

export default function HomePage() {
  const [municipality, setMunicipality] = useState<MunicipalitySearchResult | null>(null);
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [allParcels, setAllParcels] = useState<Opportunity[]>([]);
  const [filteredParcels, setFilteredParcels] = useState<Opportunity[]>([]);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(null);
  const [flyToParcelId, setFlyToParcelId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Deux modes de classement (voir backend app/api/routes/opportunities.py) :
  // "score" = score_global (urbanisme/geometrie/...), "rentabilite" = marge
  // apparente estimee du bilan promoteur simplifie (app/services/feasibility.py),
  // qui exclut les parcelles ou le gain reel ne couvre pas demolition + construction.
  const [rankingMode, setRankingMode] = useState<"score" | "rentabilite">("score");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const handleSelectMunicipality = useCallback(
    async (m: MunicipalitySearchResult) => {
      setMunicipality(m);
      setError(null);
      setAllParcels([]);
      setFilteredParcels([]);
      setSelectedParcelId(null);
      stopPolling();
      try {
        const launched = await launchAnalysis(m.insee_code);
        setJob({
          id: launched.job_id,
          municipality_id: launched.municipality_id,
          status: launched.status,
          progress_pct: 0,
          current_step: "preparation",
          started_at: null,
          finished_at: null,
          parcels_total: null,
          parcels_selected: null,
          parcels_excluded: null,
          exclusion_reasons: null,
          error_log: null,
        });
        pollRef.current = setInterval(async () => {
          try {
            const updated = await getAnalysisJob(launched.job_id);
            setJob(updated);
            if (updated.status === "COMPLETED" || updated.status === "FAILED") {
              stopPolling();
            }
          } catch (e) {
            stopPolling();
            setError(e instanceof Error ? e.message : "Erreur de suivi du job");
          }
        }, 2000);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erreur au lancement de l'analyse");
      }
    },
    [stopPolling]
  );

  // Recharge la liste (filtree) + l'overlay carte (non filtre) a la fin du job.
  useEffect(() => {
    if (!municipality || job?.status !== "COMPLETED") return;
    getOpportunities(municipality.insee_code, {}).then(setAllParcels).catch(() => setAllParcels([]));
  }, [municipality, job?.status]);

  useEffect(() => {
    if (!municipality || job?.status !== "COMPLETED") return;
    if (rankingMode === "rentabilite") {
      getTopOpportunities(municipality.insee_code, 50)
        .then(setFilteredParcels)
        .catch((e) => setError(e instanceof Error ? e.message : "Erreur de chargement du classement rentabilite"));
      return;
    }
    getOpportunities(municipality.insee_code, filters)
      .then(setFilteredParcels)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur de chargement des opportunites"));
  }, [municipality, job?.status, filters, rankingMode]);

  useEffect(() => stopPolling, [stopPolling]);

  const handleSelectParcel = useCallback((parcelId: string) => {
    setSelectedParcelId(parcelId);
    setFlyToParcelId(parcelId);
  }, []);

  const selectedParcel = allParcels.find((p) => p.parcel_id === selectedParcelId) ?? null;

  return (
    <div className="app-shell">
      <aside className="panel">
        <h1>Radar Foncier Intelligent</h1>
        <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 16 }}>
          MVP -- score provisoire tant que tous les sous-scores ne sont pas alimentes par
          des donnees reelles (voir docs/SCORING_ENGINE.md).
        </p>

        <MunicipalitySearch onSelect={handleSelectMunicipality} />

        {job && (
          <div className="section-block">
            <h2>Analyse en cours</h2>
            <div className="progress-bar-track">
              <div className="progress-bar-fill" style={{ width: `${job.progress_pct}%` }} />
            </div>
            <div style={{ fontSize: 12, marginTop: 4, color: "var(--color-text-muted)" }}>
              {job.status} -- {job.current_step ?? "..."} ({job.progress_pct}%)
            </div>
            {job.status === "COMPLETED" && (
              <div style={{ fontSize: 12, marginTop: 6 }}>
                {job.parcels_total ?? 0} parcelles analysees, {job.parcels_selected ?? 0} retenues,{" "}
                {job.parcels_excluded ?? 0} exclues.
              </div>
            )}
            {job.status === "FAILED" && (
              <div className="warning-box" style={{ marginTop: 8 }}>
                Echec de l&apos;analyse. {job.error_log ? JSON.stringify(job.error_log) : ""}
              </div>
            )}
          </div>
        )}

        {error && <div className="warning-box">{error}</div>}

        <div className="section-block">
          <h2>Classement</h2>
          <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
            <button
              className="btn-primary"
              style={{ background: rankingMode === "score" ? "var(--color-accent)" : "var(--color-text-muted)" }}
              onClick={() => setRankingMode("score")}
            >
              Meilleur score
            </button>
            <button
              className="btn-primary"
              style={{ background: rankingMode === "rentabilite" ? "var(--color-accent)" : "var(--color-text-muted)" }}
              onClick={() => setRankingMode("rentabilite")}
            >
              Top 50 rentabilite
            </button>
          </div>
          {rankingMode === "rentabilite" && (
            <p style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
              Classe par marge apparente estimee (prix de vente DVF reel - foncier -
              demolition eventuelle - construction), pas par score d&apos;urbanisme. Une
              maison existante couteuse a demolir pour un gain marginal ressort en bas
              ou disparait du classement. Estimation d&apos;ordre de grandeur, ne
              remplace pas une etude de faisabilite.
            </p>
          )}
        </div>

        {rankingMode === "score" && <FilterPanel filters={filters} onChange={setFilters} />}
      </aside>

      <main className="map-container">
        <MapView
          parcels={allParcels}
          selectedParcelId={selectedParcelId}
          onSelectParcel={handleSelectParcel}
          flyToParcelId={flyToParcelId}
        />
      </main>

      <aside className="panel panel-right">
        <ParcelSummaryPanel parcel={selectedParcel} />
        <h2>
          {rankingMode === "rentabilite" ? "Top rentabilite" : "Opportunites"} ({filteredParcels.length})
        </h2>
        <OpportunityList
          opportunities={filteredParcels}
          selectedParcelId={selectedParcelId}
          onSelect={handleSelectParcel}
          showMargin={rankingMode === "rentabilite"}
        />
      </aside>
    </div>
  );
}
