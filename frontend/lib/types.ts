// Types TS miroir des schemas Pydantic backend (app/schemas/*.py).
// Voir docs/DATA_MODEL.md pour la source de verite du modele.

export interface MunicipalitySearchResult {
  insee_code: string;
  name: string;
  postcode: string | null;
  centroid_lon: number | null;
  centroid_lat: number | null;
}

export interface Municipality {
  id: string;
  insee_code: string;
  name: string;
  department_code: string | null;
  region_code: string | null;
  population: number | null;
  last_analyzed_at: string | null;
}

export type AnalysisJobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface AnalysisJob {
  id: string;
  municipality_id: string;
  status: AnalysisJobStatus;
  progress_pct: number;
  current_step: string | null;
  started_at: string | null;
  finished_at: string | null;
  parcels_total: number | null;
  parcels_selected: number | null;
  parcels_excluded: number | null;
  exclusion_reasons: Record<string, number> | null;
  error_log: Record<string, unknown> | null;
}

export interface AnalysisJobLaunched {
  job_id: string;
  municipality_id: string;
  status: AnalysisJobStatus;
}

export type GeoJSONGeometry = {
  type: string;
  coordinates: unknown;
};

export interface Opportunity {
  parcel_id: string;
  reference: string | null;
  geometry: GeoJSONGeometry;
  parcel_area: number | null;
  score_global: number;
  built_category: string | null;
  constructibility_status: string;
  // Bilan promoteur simplifie (voir backend app/services/feasibility.py) -- null
  // tant que non calculable (donnees bati ou prix DVF insuffisants pour cette
  // parcelle/commune), jamais une valeur inventee.
  estimated_margin: number | null;
  margin_ratio: number | null;
  feasibility_computable: boolean;
  feasibility_explanation: string | null;
}

export interface ParcelScore {
  id: string;
  score_urbanisme: number;
  score_geometrie: number;
  score_surface: number;
  score_acces: number;
  score_reseaux: number;
  score_risques: number;
  score_densification: number;
  score_complexite: number;
  score_qualite_donnees: number;
  score_global: number;
  explanation_text: string | null;
}

export interface ParcelAnalysis {
  id: string;
  parcel_area: number | null;
  building_footprint_area: number | null;
  building_coverage_ratio: number | null;
  unbuilt_area: number | null;
  largest_contiguous_unbuilt_area: number | null;
  width_estimated: number | null;
  depth_estimated: number | null;
  road_frontage_length: number | null;
  geometry_quality_score: number | null;
  built_category: string | null;
  constructibility_status: string;
  urbanism_confidence_score: number | null;
  suggested_operations: string[] | null;
}

export interface ParcelDetail {
  id: string;
  municipality_id: string;
  municipality_name: string;
  section: string | null;
  numero: string | null;
  reference: string | null;
  geometry: GeoJSONGeometry;
  area_official: number | null;
  area_computed: number | null;
  typezone: string | null;
  zone_libelle: string | null;
  analysis: ParcelAnalysis | null;
  score: ParcelScore | null;
  sources: string[];
  warnings: string[];
}

export interface Filters {
  min_score: number | null;
  min_area: number | null;
  max_area: number | null;
  operation_type: string | null;
  vacant_only: boolean;
}
