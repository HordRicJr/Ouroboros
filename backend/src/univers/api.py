"""API FastAPI pour le simulateur d'univers.

Endpoints disponibles :
- POST /universes : créer un nouvel univers
- GET  /universes/{id} : métadonnées et état courant de l'univers
- POST /universes/{id}/step : avancer le temps de N jours (ticks)
- GET  /universes/{id}/map : état de la carte et du climat
- GET  /universes/{id}/notables : liste des notables actuels avec leurs profils
- POST /universes/{id}/notables/{person_id}/ask : dialoguer avec un notable (immersion totale, consomme le budget IA)
- GET  /universes/{id}/genealogy/{person_id} : arbre généalogique ascendant/descendant
"""
from __future__ import annotations

from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .constants import UniverseConstants
from .engine import Universe
from .llm import HuggingFaceClient, MockLLMClient
from .persistence import MemoryStore, Store


app = FastAPI(
    title="Simulateur d'Univers Récursif",
    version="0.3.0",
    description="Backend de simulation d'univers avec moteur Lotka-Volterra et habitants notables propulsés par LLM.",
)

# Registre local en mémoire (ou connecté à PostgresStore selon environnement)
store: Store = MemoryStore()
universes: dict[str, Universe] = {}


# --- Schémas Pydantic --------------------------------------------------------
class CreateUniverseRequest(BaseModel):
    id: str = Field(..., example="eden-01")
    seed: int = Field(default=42, example=42)
    start_year: int = Field(default=0, example=0)
    parent_id: str | None = Field(default=None, example=None)
    year_length_days: int = Field(default=365)
    gravity: float = Field(default=9.81)
    mutation_rate: float = Field(default=0.01)
    base_temperature: float = Field(default=15.0)


class StepRequest(BaseModel):
    days: int = Field(default=1, ge=1, le=3650, description="Nombre de jours simulés à avancer")


class AskNotableRequest(BaseModel):
    question: str = Field(..., example="Comment vont tes proches et que penses-tu des saisons récentes ?")
    mock: bool = Field(default=True, description="Si True, utilise un mock déterministe pour tester sans token HF")


# --- Endpoints ---------------------------------------------------------------
@app.post("/universes", status_code=201)
def create_universe(req: CreateUniverseRequest) -> dict[str, Any]:
    if req.id in universes or store.exists(req.id):
        raise HTTPException(status_code=400, detail=f"L'univers '{req.id}' existe déjà.")
    
    consts = UniverseConstants(
        year_length_days=req.year_length_days,
        gravity=req.gravity,
        mutation_rate=req.mutation_rate,
        base_temperature=req.base_temperature,
    )
    u = Universe(req.id, req.seed, consts=consts, start_year=req.start_year, parent_id=req.parent_id)
    universes[req.id] = u
    store.save(u)
    return {"message": "Univers créé avec succès", "info": u.info()}


@app.get("/universes/{universe_id}")
def get_universe(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return u.info()


@app.post("/universes/{universe_id}/step")
def step_universe(universe_id: str, req: StepRequest) -> dict[str, Any]:
    u = _get_universe(universe_id)
    events = u.step(req.days)
    store.save(u)
    return {
        "date": str(u.date),
        "tick": u.tick,
        "events_count": len(events),
        "events_sample": [e.to_dict() for e in events[:20]],
    }


@app.get("/universes/{universe_id}/map")
def get_universe_map(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    w = u.world
    return {
        "width": w.width,
        "height": w.height,
        "sea_level": w.sea_level,
        "land_fraction": float(w.is_land.mean()),
        "biomes_present": [int(b) for b in set(w.biome.flatten().tolist())],
        "rivers_cells_count": int(w.river.sum()),
    }


@app.get("/universes/{universe_id}/notables")
def get_notables(universe_id: str) -> list[dict[str, Any]]:
    u = _get_universe(universe_id)
    res = []
    for pid, not_prof in u.notables.items():
        person = u.people.persons.get(pid)
        if person:
            res.append({
                "id": pid,
                "name": person.name,
                "sex": person.sex,
                "age": round(u.people.age_years(person, u.tick), 1),
                "alive": person.alive,
                "cell": person.cell,
                "title": not_prof.title,
                "memories_count": len(not_prof.memories),
            })
    return res


@app.post("/universes/{universe_id}/notables/{person_id}/ask")
def ask_notable_endpoint(universe_id: str, person_id: int, req: AskNotableRequest) -> dict[str, Any]:
    u = _get_universe(universe_id)
    client = MockLLMClient() if req.mock else HuggingFaceClient()
    response = u.ask_notable(person_id, req.question, llm_client=client)
    store.save(u)
    return {
        "person_id": person_id,
        "question": req.question,
        "response": response,
        "ai_budget": u.ai_budget.to_dict(),
    }


@app.get("/universes/{universe_id}/genealogy/{person_id}")
def get_genealogy(universe_id: str, person_id: int, up: int = 3, down: int = 3) -> dict[str, Any]:
    u = _get_universe(universe_id)
    if person_id not in u.people.persons:
        raise HTTPException(status_code=404, detail="Individu introuvable.")
    return u.people.genealogy(person_id, up=up, down=down)


def _get_universe(universe_id: str) -> Universe:
    if universe_id in universes:
        return universes[universe_id]
    if store.exists(universe_id):
        u = store.load(universe_id)
        universes[universe_id] = u
        return u
    raise HTTPException(status_code=404, detail=f"Univers '{universe_id}' introuvable.")
