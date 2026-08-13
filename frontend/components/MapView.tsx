"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoJSONGeometry, Opportunity } from "@/lib/types";
import { scoreColor } from "./ScoreBadge";

interface Props {
  parcels: Opportunity[];
  selectedParcelId: string | null;
  onSelectParcel: (parcelId: string) => void;
  flyToParcelId: string | null;
}

type BaseLayer = "plan" | "cadastre";

// Fond de carte "Plan" : tuiles raster OpenStreetMap standard, usage personnel
// faible volume (pas de cle necessaire). Voir docs/ARCHITECTURE.md (MapLibre GL,
// licence BSD, pas de dependance a une cle commerciale).
const OSM_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm-layer", type: "raster", source: "osm" }],
};

// NOTE V1 (non implemente ici) : couche Orthophoto IGN Geoplateforme.
// Endpoint WMTS de base confirme dans docs/DATA_SOURCES.md section C :
//   https://data.geopf.fr/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetCapabilities
// Le nom exact de la couche (probablement "ORTHOIMAGERY.ORTHOPHOTOS", NON verifie
// directement -- voir DATA_SOURCES.md) doit etre confirme via un vrai GetCapabilities
// avant integration. Ne pas cabler ce nom en dur tant que ce n'est pas confirme.

const EMPTY_FEATURE_COLLECTION: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

function toFeatureCollection(parcels: Opportunity[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: parcels.map((p) => ({
      type: "Feature",
      id: p.parcel_id,
      properties: { score_global: p.score_global, reference: p.reference },
      geometry: p.geometry as GeoJSON.Geometry,
    })),
  };
}

export default function MapView({ parcels, selectedParcelId, onSelectParcel, flyToParcelId }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [baseLayer, setBaseLayer] = useState<BaseLayer>("cadastre");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: OSM_STYLE,
      center: [2.3522, 48.8566], // Paris par defaut, avant selection commune
      zoom: 12,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      map.addSource("parcels", { type: "geojson", data: EMPTY_FEATURE_COLLECTION });

      map.addLayer({
        id: "parcels-fill",
        type: "fill",
        source: "parcels",
        paint: {
          "fill-color": [
            "case",
            [">=", ["get", "score_global"], 90],
            "#14532d",
            [">=", ["get", "score_global"], 75],
            "#4d9a5b",
            [">=", ["get", "score_global"], 60],
            "#d97706",
            "#6b7280",
          ],
          "fill-opacity": 0.55,
        },
      });
      map.addLayer({
        id: "parcels-outline",
        type: "line",
        source: "parcels",
        paint: { "line-color": "#1c1f24", "line-width": 1 },
      });
      map.addLayer({
        id: "parcels-selected-outline",
        type: "line",
        source: "parcels",
        filter: ["==", ["get", "parcel_id_unused"], ""],
        paint: { "line-color": "#0b3d63", "line-width": 3 },
      });

      map.on("click", "parcels-fill", (e) => {
        const feature = e.features?.[0];
        if (feature?.id) onSelectParcel(String(feature.id));
      });
      map.on("mouseenter", "parcels-fill", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "parcels-fill", () => {
        map.getCanvas().style.cursor = "";
      });

      setReady(true);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onSelectParcel]);

  // Bascule Plan / Cadastre : au MVP, "Plan" = fond OSM seul, "Cadastre" = fond OSM +
  // overlay parcelles colore par score. Le fond de carte lui-meme reste OSM dans les
  // deux modes (pas de couche "plan IGN" separee au MVP, voir docs/DATA_SOURCES.md C).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const visibility = baseLayer === "cadastre" ? "visible" : "none";
    map.setLayoutProperty("parcels-fill", "visibility", visibility);
    map.setLayoutProperty("parcels-outline", "visibility", visibility);
  }, [baseLayer, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const source = map.getSource("parcels") as maplibregl.GeoJSONSource | undefined;
    source?.setData(toFeatureCollection(parcels));

    if (parcels.length > 0) {
      const bounds = new maplibregl.LngLatBounds();
      let hasCoords = false;
      for (const p of parcels) {
        try {
          const coords = flattenCoordinates(p.geometry);
          coords.forEach((c) => {
            bounds.extend(c as [number, number]);
            hasCoords = true;
          });
        } catch {
          // geometrie invalide, ignoree pour le calcul des bounds
        }
      }
      if (hasCoords) map.fitBounds(bounds, { padding: 40, maxZoom: 17, duration: 0 });
    }
  }, [parcels, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.setFilter("parcels-selected-outline", ["==", ["id"], selectedParcelId ?? "__none__"]);
  }, [selectedParcelId, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !flyToParcelId) return;
    const target = parcels.find((p) => p.parcel_id === flyToParcelId);
    if (!target) return;
    try {
      const coords = flattenCoordinates(target.geometry);
      const bounds = new maplibregl.LngLatBounds();
      coords.forEach((c) => bounds.extend(c as [number, number]));
      map.fitBounds(bounds, { padding: 120, maxZoom: 19, duration: 500 });
    } catch {
      // geometrie invalide, pas de zoom
    }
  }, [flyToParcelId, ready, parcels]);

  return (
    <div className="map-container">
      <div ref={containerRef} style={{ height: "100%", width: "100%" }} />
      <div
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius)",
          padding: 6,
          display: "flex",
          gap: 4,
        }}
      >
        <button
          className="btn-primary"
          style={{ background: baseLayer === "plan" ? "var(--color-accent)" : "var(--color-text-muted)" }}
          onClick={() => setBaseLayer("plan")}
        >
          Plan
        </button>
        <button
          className="btn-primary"
          style={{ background: baseLayer === "cadastre" ? "var(--color-accent)" : "var(--color-text-muted)" }}
          onClick={() => setBaseLayer("cadastre")}
        >
          Cadastre
        </button>
      </div>
      <div
        className="legend"
        style={{
          position: "absolute",
          bottom: 24,
          left: 12,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius)",
          padding: 10,
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: 4, color: "var(--color-text)" }}>Score global</div>
        <div className="legend-item">
          <span className="legend-swatch" style={{ background: scoreColor(95) }} /> &ge; 90 (excellent)
        </div>
        <div className="legend-item">
          <span className="legend-swatch" style={{ background: scoreColor(80) }} /> 75-89 (bon)
        </div>
        <div className="legend-item">
          <span className="legend-swatch" style={{ background: scoreColor(65) }} /> 60-74 (moyen)
        </div>
        <div className="legend-item">
          <span className="legend-swatch" style={{ background: scoreColor(30) }} /> &lt; 60 (faible)
        </div>
      </div>
    </div>
  );
}

function flattenCoordinates(geometry: GeoJSONGeometry | undefined): number[][] {
  if (!geometry) return [];
  const coords: number[][] = [];
  const walk = (value: unknown) => {
    if (Array.isArray(value)) {
      if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
        coords.push(value as number[]);
      } else {
        value.forEach(walk);
      }
    }
  };
  walk((geometry as { coordinates?: unknown }).coordinates);
  return coords;
}
