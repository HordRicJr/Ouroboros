# Ouroboros – Plan d'amélioration pour une simulation vraiment émergente

Document de travail – 13 octobre 2026 – versionné dans le dépôt le 14 octobre 2026.

## Objectif

Séparation nette : le code définit ce qui est **physiquement possible**, les agents décident de ce qu'ils font, et tout ce qui en résulte est **mesuré**, pas programmé.

## Feuille de route (état)

| Étape | Contenu | État |
|-------|---------|------|
| 1 | Retirer grades fixes, titres à seuil, +2 influence, tabous auto ; statut sociométrique | En cours |
| 2 | Prompts minimal-control, test de fuite, profils, perception locale | En cours |
| 3 | Mémoire, réflexion, oubli, inventaire de connaissances | Partiel |
| 4 | Journal IA, graines, empreintes, forks | Partiel |
| 5 | Module de mesures | Partiel |
| 6 | Calibration démographique | À faire |
| 7 | ODD + préenregistrement | Fait (stubs) |
| 8–9 | Runs expérimentaux + analyse | Après checklist |

## Décisions figées (14 oct. 2026)

- Cadre de départ du run de référence : **neutre** (noms inventés, pas de Genèse / Adan / Eva).
- Observation pure = règle ; dialogues sur branches forked uniquement.
- Vitesse cible : **0,5 s réelle = 1 jour simulé**.
- Un second modèle (autre famille) est prévu dans `infra/models.json` pour réduire l'homogénéité.

## Sources

Voir `docs/preregistration-2026-10-14.md` et le document source du 13 octobre 2026.
