# Protocole ODD – Ouroboros (Overview, Design concepts, Details)

Version stub – 2026-10-14. À enrichir avant publication.

## 1. Overview

### 1.1 Purpose
Simuler une société d'agents humains (règles + LLM optionnel) pour observer si des asymétries sociales, normes et institutions émergent sans être assignées par le code.

### 1.2 Entities
- Mondes (grille, biomes, climat)
- Espèces / écologie (Lotka–Volterra)
- Personnes (génome, kin, cognition Big Five)
- Clans, graphe social, modules (tech, langue, justice factuelle)

### 1.3 Process overview and scheduling
Tick = 1 jour simulé. Écologie hebdomadaire ; modules sociaux annuels ; métriques saisonnières ; réflexions cognitives périodiques ; LLM seulement sur décisions / dialogues (branches).

## 2. Design concepts

- **Émergence :** statut = centralité de déférence, pas table de grades.
- **Stochasticité :** graines monde + journal des appels IA.
- **Observation :** intervention = branche forkée.
- **Adaptation :** mémoire, réflexion, oubli ; pas de consigne comportementale dans les prompts.

## 3. Details

- **Initialisation :** genèse bande chasseurs-cueilleurs ; cadre `neutral` ou `biblical` (variable expérimentale).
- **Entrées :** constantes (`UniverseConstants`), seed, vitesse `SECONDS_PER_DAY`.
- **Sorties :** événements, chroniques, snapshots métriques, logs IA, exports CSV/JSON.
