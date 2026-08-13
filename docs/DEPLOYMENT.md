# Déploiement en ligne (hébergement gratuit)

## Choix retenu

- **Backend (FastAPI)** : Render, service web gratuit.
- **Frontend (Next.js)** : Render, service web gratuit (pas Vercel : le connecteur MCP Vercel disponible dans cette session n'expose que des outils de lecture/analyse de déploiements existants, pas de création — donc pas utilisable pour un déploiement automatisé depuis ici. Rien n'empêche de migrer vers Vercel plus tard manuellement, le frontend est un Next.js standard).
- **Base de données** : Supabase, PostgreSQL gratuit avec extension PostGIS. Choisi plutôt que le Postgres gratuit de Render car ce dernier expire après un nombre de jours limité sur le plan gratuit ; Supabase reste disponible indéfiniment (il se met en pause après une semaine d'inactivité et reprend automatiquement à la connexion suivante).

## Sécurité (usage personnel, application publique)

Deux couches indépendantes, ajoutées spécifiquement pour le déploiement public (absentes par défaut en local) :

1. **Basic Auth sur tout le site** (`frontend/middleware.ts`) : identifiant/mot de passe définis par `BASIC_AUTH_USER`/`BASIC_AUTH_PASSWORD`. Bloque l'accès à toutes les pages ET à la route proxy `/api/backend/*` tant qu'on n'est pas authentifié.
2. **Clé interne partagée** (`backend/app/core/security.py`, `INTERNAL_API_KEY`) : le frontend (uniquement côté serveur, jamais exposée au navigateur) ajoute cette clé à chaque requête vers le backend. Le backend refuse toute requête sans cette clé dès qu'elle est configurée. Le navigateur n'appelle donc jamais le backend directement -- uniquement `/api/backend/*` en même origine que le frontend, elle-même protégée par (1).

Sans ces deux variables définies, l'application se comporte comme en local : ouverte, pas de mot de passe (c'est le comportement par défaut de `docker-compose.yml`).

## Variables d'environnement à définir sur Render

**Backend** :
- `DATABASE_URL` (fournie par Supabase, driver `postgresql+psycopg`, en général au format `postgresql+psycopg://postgres:[password]@[host]:5432/postgres`)
- `FRONTEND_ORIGIN` (URL Render du frontend, ex `https://radar-foncier-frontend.onrender.com`)
- `INTERNAL_API_KEY` (valeur aléatoire forte, générée une fois)

**Frontend** :
- `BACKEND_URL` (URL Render du backend, ex `https://radar-foncier-backend.onrender.com`)
- `INTERNAL_API_KEY` (**la même valeur** que côté backend)
- `BASIC_AUTH_USER`, `BASIC_AUTH_PASSWORD` (identifiants de connexion au site)

## Limites connues de l'hébergement gratuit

- Le service web gratuit Render se met en veille après une période d'inactivité : le premier chargement après une pause peut prendre 30-60 secondes (cold start). Comportement normal, pas un bug.
- La base Supabase gratuite se met en pause après 7 jours sans requête ; la première requête après une pause peut échouer une fois puis fonctionner (reprise automatique). Documenté ici pour ne pas confondre avec une panne du connecteur.
- Pas de nom de domaine personnalisé sur les plans gratuits (URL en `*.onrender.com`).
