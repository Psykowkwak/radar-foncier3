# Radar Foncier Intelligent

Logiciel web d'analyse de parcelles cadastrales francaises (MVP). Voir `docs/`
pour le cahier des charges et les decisions d'architecture deja prises
(`ARCHITECTURE.md`, `DATA_SOURCES.md`, `DATA_MODEL.md`, `SCORING_ENGINE.md`,
`URBANISM_ENGINE.md`, `FEASIBILITY_ENGINE.md`, `ROADMAP.md`).

## Ce que fait le MVP

- Recherche une commune, lance une analyse complete (cadastre, zonage PLU/GPU,
  bati, risques RGA/cavites) via des connecteurs reels sur les sources
  publiques (IGN API Carto, Georisques, Etalab).
- Calcule surface, compacite, largeur/profondeur estimees, taux d'emprise
  batie, categorie de bati, statut de constructibilite (heuristique de zone),
  et un score global provisoire sur 9 sous-scores (5 reels, 4 neutres
  documentes tant que les connecteurs correspondants ne sont pas complets --
  voir `docs/SCORING_ENGINE.md`).
- Affiche une carte (fond OSM + overlay cadastral colore par score), une liste
  d'opportunites filtrable et triee, et une fiche parcelle detaillee avec
  sources tracees.

Explicitement HORS MVP (voir `docs/ROADMAP.md`) : reglement PLU structure
(texte), reseaux eau/electricite reels, servitudes/OAP, regroupements
fonciers, favoris/historique, moteur de faisabilite (V2), rapport PDF.

## Demarrage rapide (moins de 10 commandes)

Prerequis : Docker et Docker Compose.

```bash
git clone <ce-depot> radar-foncier   # ou utilisez le dossier deja present
cd radar-foncier
cp .env.example .env
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Ouvrez ensuite :
- Frontend : http://localhost:3000
- API (docs interactives OpenAPI) : http://localhost:8000/docs

Pour arreter :

```bash
docker compose down
```

Pour tout remettre a zero (y compris les donnees) :

```bash
docker compose down -v
```

## Lancer les tests

Avec Docker (recommande, pas besoin d'environnement Python local) :

```bash
docker compose exec backend pytest
```

En local avec un environnement virtuel Python :

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Les tests `test_geometry.py`, `test_built_category.py`, `test_scoring.py` et
`test_connectors.py` ne necessitent ni base de donnees ni acces reseau (les
appels HTTP sont mockes avec `respx`).

## Structure du depot

```
backend/    API FastAPI, connecteurs, services (geometrie/scoring/urbanisme),
            modeles SQLAlchemy, migrations Alembic, tests
frontend/   Next.js (App Router) + MapLibre GL
docs/       Cahier des charges et architecture (deja rediges, source de verite)
docker-compose.yml
```

Voir `backend/app/connectors/README.md` pour le statut precis (reel / defensif
/ stub) de chaque connecteur de donnees externes, et ce qui reste a verifier
avant un usage intensif.

## Variables d'environnement

Voir `.env.example`. `ANTHROPIC_API_KEY` est optionnelle au MVP : aucune
fonctionnalite MVP n'appelle de LLM (voir `docs/ARCHITECTURE.md` §7 et
`docs/SCORING_ENGINE.md` -- l'explication de score est un texte deterministe,
pas une generation IA, au MVP).

## Limites connues du MVP (a lire avant de faire confiance aux resultats)

- Le score global est explicitement provisoire : `score_acces`,
  `score_reseaux` et `score_complexite` sont des valeurs neutres (50,
  documentees `DONNEES_INSUFFISANTES`), pas des mesures reelles.
- Le statut de constructibilite est une heuristique sur le prefixe de zone
  (U/AU/A/N), plafonnee a une confiance de 60/100 -- le reglement ecrit du PLU
  n'est pas analyse au MVP (voir `docs/URBANISM_ENGINE.md`).
- Le connecteur bati (Etalab) et le connecteur risques (Georisques) sont
  ecrits en mode defensif : leur comportement exact n'a pas ete valide par un
  appel reseau reel depuis l'environnement de developpement de cet agent (pas
  d'acces reseau sortant verifie en sandbox). Un echec de ces connecteurs ne
  bloque jamais l'analyse -- il degrade les sous-scores concernes et ajoute un
  avertissement visible sur la fiche parcelle.
