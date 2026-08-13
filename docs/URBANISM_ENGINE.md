# Moteur d'analyse PLU/PLUi

## Pipeline

```
Parcelle → intersection spatiale avec zone-urba (GPU) → UrbanismZone(s) associée(s)
        → résolution UrbanismDocument (si disponible)
        → UrbanismRuleSet en cache (zone, version) ?
              existant → réutiliser
              absent   → extraction texte réglementaire (PDF, urlfic) → IA → RuleSet → cache
        → application du RuleSet à la parcelle
```

Une parcelle peut chevaucher plusieurs zones (rare mais possible en bord de zonage) : le moteur associe la zone majoritaire par surface d'intersection et signale un `AnalysisWarning` INFORMATION si le partage est significatif (> 15 % dans une seconde zone).

## Contrainte structurée vs textuelle

**Structurée** : extraite directement des attributs GeoJSON de `zone-urba` quand ils suffisent (`typezone`, `destdomi`) ou d'un `UrbanismConstraint` déjà interprété par l'IA avec un schéma numérique (`max_height_m`, `setback_from_road_m`, `max_ground_coverage_pct`, `min_green_space_pct`, `min_parking_per_unit`).

**Textuelle** : conservée telle quelle avec `{rule, extract, source_document, article, page, interpretation, confidence}` quand la règle est trop complexe pour être réduite sans ambiguïté à un nombre (ex : règles de toiture conditionnelles, exceptions).

## Rôle de l'IA — strictement encadré

L'IA n'intervient jamais sur la géométrie. Son rôle unique : lire un extrait de règlement (texte déjà extrait du PDF par un parseur classique, pas par l'IA elle-même quand c'est possible) et produire une règle structurée + une confiance, avec citation exacte de la source.

Format de sortie imposé (schéma validé, pas de texte libre non structuré) :

```json
{
  "rule_key": "max_height_m",
  "value": 9,
  "unit": "m",
  "source_document": "PLU commune X, zone UB",
  "article": "Article UB 10",
  "page": 14,
  "extract": "La hauteur maximale des constructions est fixée à 9 mètres...",
  "confidence": 0.95
}
```

Si le texte est ambigu ou contradictoire (deux règles applicables, exceptions non résolues) : `confidence < 0.6` déclenche automatiquement `needs_human_review = true` sur le `UrbanismRuleSet`, jamais un arbitrage automatique. L'UI affiche alors "Vérification humaine nécessaire" au lieu d'une valeur.

## Constructibilité — matrice de décision (déterministe, pas de LLM)

```
SI zone A/N sans secteur constructible ET aucune exception connue → A_PRIORI_NON_CONSTRUCTIBLE
SINON SI document GPU absent pour la commune → DONNEES_INSUFFISANTES (jamais FAVORABLE par défaut)
SINON SI zone U/AU ET aucun risque bloquant ET géométrie exploitable → FAVORABLE ou FAVORABLE_SOUS_CONDITIONS
      (SOUS_CONDITIONS si des UrbanismConstraint ont confidence < 0.8 ou needs_human_review)
SINON SI contraintes contradictoires non résolues → COMPLEXE
SINON SI risque réglementaire confirmé incompatible → DEFAVORABLE ou exclusion (voir SCORING_ENGINE.md)
```

## MVP réel

Au MVP, seule la classification par zone (`typezone`/préfixe de libellé : U*, AU*, A*, N*) est utilisée pour un `constructibility_status` de premier niveau, marqué `urbanism_confidence_score` plafonné à 60 tant que le règlement écrit n'est pas analysé. L'extraction PDF + interprétation IA est V1 (voir ROADMAP.md) — elle n'est PAS simulée ni approximée par des valeurs par défaut au MVP.
