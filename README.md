# Ouroboros — Simulateur Récursif d'Univers

Simulateur d'univers autonome avec physique réaliste, dynamique des populations à deux niveaux (Lotka-Volterra matriciel + notables conscients), persistance reproductible et habitants notables animés par LLM (Qwen2.5-7B) en immersion totale.

## Architecture

- **Backend** : Python 3.12+ / FastAPI / NumPy
- **Base de données & Persistance** : PostgreSQL 16 (Snapshots compressés + Event Sourcing)
- **Écosystème & Biologie** :
  - Dynamique Lotka-Volterra avec dispersion spatiale conservative
  - Génétique diploïde (recombinaison mendélienne, mutations)
  - Arbre de parenté, tabous culturels et règles matrimoniales
- **Intelligence Artificielle & Immersion** :
  - Agents notables incarnés via Hugging Face Inference ou vLLM AWS
  - Système de mémoire épisodique consolidée et court-terme
  - Filtre anti-anachronisme (`ImmersionFilter`) : interdiction totale de briser le 4e mur (simulation, code, IA)
  - Contrôleur de budget et quotas stricts (adapté pour enveloppe de 100$)

## Installation & Lancement

```bash
cd backend
python -m venv .venv
# Sur Windows:
.\.venv\Scripts\activate
# Sur Linux/Mac:
source .venv/bin/activate

pip install -e .
pytest -q
uvicorn univers.api:app --reload
```

## Endpoints API

- `POST /universes` : Initialiser un univers avec ses constantes
- `GET /universes/{id}` : État courant et date simulée
- `POST /universes/{id}/step` : Avancer le temps de $N$ jours
- `GET /universes/{id}/map` : Données de la carte et des biomes
- `GET /universes/{id}/notables` : Liste des notables vivants et de leurs mémoires
- `POST /universes/{id}/notables/{person_id}/ask` : Dialoguer avec un notable en immersion totale
- `GET /universes/{id}/genealogy/{person_id}` : Explorer l'arbre généalogique
