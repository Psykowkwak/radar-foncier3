# Moteur de faisabilité (V2)

Statut : conception documentée maintenant pour cadrer le modèle de données (§41) et l'architecture, implémentation prévue en V2 après consolidation du radar (V1). Ce document fixe les règles pour éviter toute impasse d'architecture plus tard.

## Étapes (§21-§34 du cahier des charges)

1. **Enveloppe constructible** : `gross_buildable_envelope` = polygone cadastral moins reculs voie/limites séparatives/servitudes géométriques (buffers négatifs Shapely). `effective_buildable_envelope` = enveloppe brute moins zones non constructibles identifiées (espaces boisés classés, bandes de retrait supplémentaires). `possible_footprint` = enveloppe effective × emprise au sol maximale réglementaire.
2. **Options pertinentes uniquement** : le moteur ne propose une option (division simple / lotissement / maisons groupées / petit collectif / immeuble collectif / démolition-reconstruction) que si les contraintes structurées de zone l'autorisent ET si la géométrie le permet réellement (ex : pas de "lotissement 8 lots" sur une enveloppe qui ne contient géométriquement que 3 lots plausibles).
3. **Algorithme d'implantation** (§29) : génération de footprints candidats sur plusieurs orientations (alignées sur la façade principale, puis rotations testées), test de plusieurs implantations, ajout circulation/stationnement, contrôle des contraintes (reculs, hauteur, coefficient), scoring des variantes, sélection des meilleures. Implémenté avec Shapely (buffers, `minimum_rotated_rectangle`, tests d'intersection) — jamais par une IA générative de géométrie.
4. **Stationnement intégré spatialement** : les places (dimension standard configurable, ex 2.5m × 5m + voie de manœuvre 5.5m) sont réellement placées dans l'enveloppe restante après implantation du bâti, pas seulement comptées arithmétiquement. Un scénario dont le stationnement réglementaire ne peut pas être placé spatialement est marqué `parking_feasible = false` et rétrogradé.
5. **Trois scénarios systématiques** : PRUDENT (hypothèses basses : emprise réduite, moins de niveaux, ratios de parties communes hauts), CENTRAL (hypothèses réalistes médianes), OPTIMISÉ (exploitation plus complète du règlement, toujours dans les limites structurées — jamais au-delà).

## Bilan promoteur

Recettes = surface vendable × prix/m² paramétrable + parkings + terrains à bâtir. Dépenses = terrain (variable de sortie, pas d'entrée — voir charge foncière) + construction (€/m² par typologie, table `CostAssumption` LOW/CENTRAL/HIGH) + VRD + honoraires + taxes + aléas + frais financiers + commercialisation.

**Charge foncière maximale** : résolution inverse — étant donné recettes, coûts hors foncier, et une marge cible configurable (%), `max_land_price = revenue − costs_excl_land − (revenue × target_margin_pct)`. Calculée pour plusieurs paliers de marge (8 %, 10 %, 12 % typiquement, configurable).

## Score de faisabilité

`DEVELOPMENT_FEASIBILITY_SCORE` (0-100), sous-scores urbanisme/architecture/accès/parking/réseaux/technique/risques/économie/complexité administrative/qualité des données — même logique de transparence que `LAND_OPPORTUNITY_SCORE` (voir SCORING_ENGINE.md). Conclusion textuelle parmi : EXCELLENTE OPPORTUNITÉ / BONNE OPPORTUNITÉ / À APPROFONDIR / OPÉRATION COMPLEXE / PEU PERTINENT / NON RECOMMANDÉ — mapping déterministe depuis le score, pas une appréciation libre du LLM.

## Plan de masse conceptuel

Rendu graphique (SVG ou GeoJSON stylé côté frontend) superposé au contour cadastral réel : bâtiments projetés, lots, voirie interne, accès, parkings, espaces verts, reculs matérialisés, bâtiment existant conservé si pertinent. Toujours étiqueté explicitement "Esquisse algorithmique de faisabilité foncière — non contractuelle, ne remplace pas un plan d'architecte" dans l'UI et tout export PDF.

## Garde-fous non négociables

- Jamais de surface de plancher "mathématiquement maximale" présentée comme un projet réaliste sans le scénario PRUDENT en vis-à-vis.
- Le moteur ne tranche jamais un stationnement infaisable en "faisable quand même".
- Toute hypothèse économique (coût construction, prix de vente, marge cible) est un paramètre modifiable en base (`CostAssumption`), jamais une constante dans le code (§30/§45).
- Le rapport de faisabilité rappelle systématiquement qu'il ne remplace pas certificat d'urbanisme, étude géotechnique, étude réseaux, bornage, architecte, géomètre, ou autorisation d'urbanisme (§60).
