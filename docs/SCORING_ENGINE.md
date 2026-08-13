# Moteur de scoring

## Principe

`LAND_OPPORTUNITY_SCORE` (0-100) n'est jamais une boîte noire : il résulte de 9 sous-scores visibles, combinés par une somme pondérée configurable, puis ajusté par des pénalités/exclusions explicites. Chaque sous-score expose les valeurs brutes qui l'ont produit (traçabilité, §37).

## Sous-scores (0-100 chacun)

| Sous-score | Entrées (MVP) | Entrées (V1+) |
|---|---|---|
| `score_urbanisme` | zone PLU présente/absente (zone-urba), type de zone (U/AU/A/N heuristique sur le préfixe) | règlement structuré complet, OAP |
| `score_geometrie` | surface, compacité (ratio surface/périmètre²), largeur/profondeur estimées | détection drapeau, étranglements, orientation |
| `score_surface` | surface libre (parcelle − emprise bâtie) vs seuils configurables | surface constructible après retraits réels |
| `score_acces` | contact avec voie détecté géométriquement (intersection avec couche voirie si dispo) | largeur de voie, nombre d'accès possibles |
| `score_reseaux` | UNKNOWN par défaut → score neutre (50) documenté comme non fiable | distance réseaux électrique/eau réels |
| `score_risques` | RGA + cavités (Géorisques) | ensemble des risques Géorisques |
| `score_densification` | ratio bâti/parcelle (built_category) | simulation de détachement réel |
| `score_complexite` | nombre de contraintes textuelles non résolues | complexité réglementaire réelle |
| `score_qualite_donnees` | proportion de champs `CONFIRMED`/`CALCULATED` vs `UNKNOWN` sur la parcelle | idem, plus fin |

## Combinaison

```
score_global = Σ (sous_score_i × poids_i) / Σ poids_i
```

Poids par défaut (modifiables dans `ScoringWeights`, exposés en UI Paramètres) :

```json
{
  "urbanisme": 0.20, "geometrie": 0.15, "surface": 0.15, "acces": 0.10,
  "reseaux": 0.05, "risques": 0.10, "densification": 0.15,
  "complexite": 0.05, "qualite_donnees": 0.05
}
```

## Pénalités et exclusions (appliquées après le calcul du score pondéré)

| Condition | Effet |
|---|---|
| Zone A (agricole) ou N (naturelle) sans indice de secteur constructible | Exclusion par défaut (configurable en "forte pénalité" au lieu d'exclusion) |
| Risque réglementaire incompatible confirmé (ex : zone rouge PPR) | Exclusion |
| Aucun contact avec voie détecté ET aucune servitude de passage connue | Pénalité majeure (-40) |
| Largeur estimée < 4 m | Pénalité forte (-25), signalée "parcelle en drapeau probable" |
| `building_coverage_ratio` > 0.85 sans indice de renouvellement urbain | Pénalité forte (-30) |
| `constructibility_status = A_PRIORI_NON_CONSTRUCTIBLE` | Exclusion |
| `constructibility_status = DONNEES_INSUFFISANTES` | Score plafonné à 50, jamais classé "fort potentiel" |

Les seuils numériques ci-dessus sont des valeurs par défaut, stockées dans `ScoringWeights.penalties` et modifiables sans redéploiement.

## Constructibilité (jamais binaire)

`constructibility_status ∈ {FAVORABLE, FAVORABLE_SOUS_CONDITIONS, COMPLEXE, DEFAVORABLE, A_PRIORI_NON_CONSTRUCTIBLE, DONNEES_INSUFFISANTES}`, accompagné de `urbanism_confidence_score` (0-100). Déterminé par une matrice de règles explicite (zone, présence de document, présence de risque bloquant, qualité des données), jamais par le LLM.

## Explication humaine du score

Générée en deux temps :
1. **Déterministe** : un template Python assemble les points positifs/négatifs à partir des sous-scores et des `AnalysisWarning` réellement produits (aucune improvisation).
2. **Rédactionnel (optionnel, V1)** : le LLM reformule ce texte en langage naturel fluide, à partir STRICTEMENT du texte déterministe fourni en entrée — il ne reçoit jamais les données brutes et ne peut donc pas halluciner de nouveaux faits.

## Ce que le MVP implémente réellement

Au MVP : `score_urbanisme` (présence/type de zone), `score_geometrie`, `score_surface`, `score_densification`, `score_qualite_donnees` sont calculés à partir de données réelles. `score_acces`, `score_reseaux`, `score_risques`, `score_complexite` sont calculés en version simplifiée ou retournent une valeur neutre documentée `DONNEES_INSUFFISANTES` tant que les connecteurs correspondants ne sont pas complets (voir ROADMAP.md). Le score global MVP est donc explicitement marqué comme provisoire dans l'UI tant que tous les sous-scores ne sont pas alimentés par des données réelles.
