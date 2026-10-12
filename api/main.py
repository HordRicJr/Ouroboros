"""API FastAPI d'Ouroboros démarrée avec uvicorn api.main:app"""
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine.constants import UniverseConstants
from engine.engine import Universe
from engine.llm import HuggingFaceClient, MockLLMClient
from engine.persistence import MemoryStore, Store

app = FastAPI(
    title="Ouroboros API",
    version="1.0.0",
    description="API FastAPI pour le simulateur récursif d'univers Ouroboros.",
)

# Configuration CORS
cors_origins_env = os.environ.get("CORS_ORIGINS", "*")
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registre local
store: Store = MemoryStore()
universes: dict[str, Universe] = {}

# Initialisation d'un univers par défaut pour /api/universes
_default_u = Universe("main", 42)
universes["main"] = _default_u
store.save(_default_u)


class CreateUniverseRequest(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "eden-01"})
    seed: int = Field(default=42, json_schema_extra={"example": 42})
    start_year: int = Field(default=0, json_schema_extra={"example": 0})
    parent_id: str | None = Field(default=None, json_schema_extra={"example": None})
    year_length_days: int = Field(default=365)
    gravity: float = Field(default=9.81)
    mutation_rate: float = Field(default=0.01)
    base_temperature: float = Field(default=15.0)


class StepRequest(BaseModel):
    days: int = Field(default=1, ge=1, le=3650, description="Nombre de jours simulés à avancer")


class AskNotableRequest(BaseModel):
    question: str = Field(..., json_schema_extra={"example": "Comment vont tes proches et que penses-tu des saisons récentes ?"})
    mock: bool = Field(default=True, description="Si True, utilise un mock déterministe pour tester sans token HF")


# --- Endpoints de base et santé requis par le serveur ---
@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "api": "ok"}


@app.get("/api/universes")
def list_api_universes() -> list[dict[str, Any]]:
    return [u.info() for u in universes.values()]


# --- Endpoints de gestion de l'univers ---
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


@app.get("/universes/{universe_id}/clans")
def list_clans(universe_id: str) -> list[dict[str, Any]]:
    u = _get_universe(universe_id)
    res = []
    for clan in u.society.clans.values():
        leader = u.people.persons.get(clan.leader_id) if clan.leader_id else None
        matriarch = u.people.persons.get(clan.matriarch_id) if clan.matriarch_id else None
        res.append({
            "id": clan.id,
            "name": clan.name,
            "totem": clan.totem,
            "settlement_cell": list(clan.settlement_cell),
            "population": clan.population_size,
            "leader_id": clan.leader_id,
            "leader_name": leader.name if leader else None,
            "matriarch_id": clan.matriarch_id,
            "matriarch_name": matriarch.name if matriarch else None,
            "cosmogony": clan.cosmogony,
            "taboos": clan.taboos,
            "founded_year": clan.founded_year,
        })
    return res


@app.get("/universes/{universe_id}/clans/{clan_id}")
def get_clan(universe_id: str, clan_id: int) -> dict[str, Any]:
    u = _get_universe(universe_id)
    clan = u.society.clans.get(clan_id)
    if not clan:
        raise HTTPException(status_code=404, detail="Clan introuvable.")

    leader = u.people.persons.get(clan.leader_id) if clan.leader_id else None
    matriarch = u.people.persons.get(clan.matriarch_id) if clan.matriarch_id else None

    # Résumé des membres vivants
    members = []
    for pid in clan.member_ids:
        p = u.people.persons.get(pid)
        if p and p.alive:
            members.append({
                "id": p.id,
                "name": p.name,
                "sex": p.sex,
                "age": round(u.people.age_years(p, u.tick), 1),
                "notable": p.notable,
            })

    # Relations avec noms des autres clans
    relations_detailed = {}
    for other_id, score in clan.relations.items():
        other_clan = u.society.clans.get(other_id)
        relations_detailed[str(other_id)] = {
            "clan_name": other_clan.name if other_clan else f"Clan #{other_id}",
            "relation_score": score,
            "status": "allié" if score >= 0.5 else ("rival/hostile" if score <= -0.3 else "neutre"),
        }

    return {
        "id": clan.id,
        "name": clan.name,
        "totem": clan.totem,
        "settlement_cell": list(clan.settlement_cell),
        "territory_cells": [list(c) for c in clan.territory_cells],
        "population": clan.population_size,
        "leader": {"id": leader.id, "name": leader.name} if leader else None,
        "matriarch": {"id": matriarch.id, "name": matriarch.name} if matriarch else None,
        "cosmogony": clan.cosmogony,
        "taboos": clan.taboos,
        "relations": relations_detailed,
        "founded_year": clan.founded_year,
        "members": members,
    }


def _get_universe(universe_id: str) -> Universe:
    if universe_id in universes:
        return universes[universe_id]
    if store.exists(universe_id):
        u = store.load(universe_id)
        universes[universe_id] = u
        return u
    raise HTTPException(status_code=404, detail=f"Univers '{universe_id}' introuvable.")
