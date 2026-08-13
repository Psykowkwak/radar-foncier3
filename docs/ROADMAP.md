# Roadmap

## MVP (en cours — ce dépôt)

- [x] Docs d'architecture
- [x] Squelette repo (backend FastAPI, frontend Next.js, docker-compose, PostGIS)
- [ ] `CadastreProvider` réel (API Carto IGN)
- [ ] `UrbanismProvider` réel (zone-urba, API Carto IGN)
- [ ] `RiskProvider` partiel (Géorisques : RGA, cavités)
- [ ] Bâti (Etalab cadastre, couche `batiments`)
- [ ] Calculs géométriques (surface, bâti, compacité, largeur/profondeur approx.)
- [ ] Score MVP (5 sous-scores réels, 4 marqués données insuffisantes)
- [ ] Job d'analyse commune avec progression
- [ ] API : recherche commune, lancement analyse, liste opportunités, fiche parcelle
- [ ] Frontend : sélection commune, carte MapLibre (plan/cadastre/orthophoto), liste triée, sync liste↔carte, fiche parcelle avec sources affichées
- [ ] Tests unitaires géométrie + connecteurs (fixtures)

Explicitement HORS MVP : texte réglementaire PLU structuré, réseaux eau/électricité réels, servitudes/OAP, regroupements fonciers, favoris/historique, faisabilité, rapport PDF.

## V1

- Analyse complète du règlement écrit (extraction PDF + IA d'interprétation avec traçabilité et cache `UrbanismRuleSet`)
- Risques complets (tous les endpoints Géorisques pertinents)
- Réseaux : validation réelle du connecteur Enedis (pattern OpenDataSoft à confirmer manuellement), mécanisme d'import manuel eau/assainissement (GeoJSON/SHP/GPKG)
- Prescriptions, servitudes (SUP), OAP
- Regroupements fonciers (`LandAssembly`), limités par contiguïté/zonage/seuils
- Scoring avancé (tous les sous-scores alimentés par données réelles)
- Favoris, notes, statuts personnels, page "Mes opportunités"
- Historique des analyses

## V2

- Enveloppe constructible + moteur de faisabilité complet (division, lotissement, collectif)
- Algorithme d'implantation géométrique + stationnement spatialisé
- Plan de masse conceptuel (rendu graphique)
- Bilan promoteur + charge foncière maximale
- Rapport PDF

## V3+ (non planifié en détail)

- Sélection par zone dessinée manuellement / département entier
- DVF (analyse de marché), données INSEE, foncier public, ABF/monuments historiques
- Multi-fournisseur LLM (OpenAI en complément de Claude)
- File de tâches dédiée (Celery/RQ) si le volume d'une analyse départementale l'exige

## Décisions techniques prises sans blocage (documentées ici, pas de retour en arrière sans raison)

- PostGIS pour tout calcul spatial, jamais approximé côté application.
- Jobs d'analyse en `BackgroundTasks` FastAPI + table de progression au MVP (pas de Celery tant que le volume ne l'exige pas).
- LLM = Claude (Anthropic) en implémentation initiale de `LLMProvider`, interface prête pour un second fournisseur.
- Pas de clé API IGN/Géoplateforme disponible au démarrage du projet → les connecteurs qui en auraient besoin sont documentés mais les endpoints publics sans authentification (Cadastre, GPU, Géorisques) sont priorisés pour le MVP afin de livrer un produit fonctionnel avec de vraies données dès maintenant.
