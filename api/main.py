"""API FastAPI d'Ouroboros démarrée avec uvicorn api.main:app"""
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine.constants import UniverseConstants
from engine.engine import Universe
from engine.llm import HuggingFaceClient, MockLLMClient
from engine.multiverse import MultiverseRegistry
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
multiverse: MultiverseRegistry = MultiverseRegistry()
universes: dict[str, Universe] = {}

# Initialisation d'un univers par défaut pour /api/universes
_default_u = Universe("main", 42)
universes["main"] = _default_u
store.save(_default_u)
multiverse.register(_default_u)


class CreateUniverseRequest(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "eden-01"})
    seed: int = Field(default=42, json_schema_extra={"example": 42})
    start_year: int = Field(default=0, json_schema_extra={"example": 0})
    parent_id: str | None = Field(default=None, json_schema_extra={"example": None})
    year_length_days: int = Field(default=365)
    gravity: float = Field(default=9.81)
    mutation_rate: float = Field(default=0.01)
    base_temperature: float = Field(default=15.0)


class SpawnUniverseRequest(BaseModel):
    child_id: str = Field(..., json_schema_extra={"example": "eden-child-01"})
    seed: int | None = Field(default=None, description="Graine aléatoire optionnelle (auto-dérivée si omise)")
    amplitude: float = Field(default=0.05, description="Amplitude de mutation des lois physiques (±%)")


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


@app.post("/universes/{universe_id}/reset")
def reset_universe(universe_id: str) -> dict[str, Any]:
    u_old = _get_universe(universe_id)
    # Réinitialisation à neuf avec la même graine (même monde et lois)
    u_new = Universe(u_old.id, u_old.seed, consts=u_old.consts, start_year=u_old.start_year, parent_id=u_old.parent_id)
    universes[universe_id] = u_new
    store.save(u_new)
    return {
        "message": f"Univers '{universe_id}' réinitialisé au commencement.",
        "info": u_new.info(),
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

    # Langue et technologies maîtrisées
    lang = u.languages.languages.get(clan.language_id) if hasattr(u, "languages") else None
    tech_state = u.technology.clan_states.get(clan.id) if hasattr(u, "technology") else None
    from engine.technology import TECH_CATALOG
    techs_detailed = [
        {"id": tid, "name": TECH_CATALOG[tid].name, "description": TECH_CATALOG[tid].description}
        for tid in (tech_state.unlocked_techs if tech_state else [])
        if tid in TECH_CATALOG
    ]

    return {
        "id": clan.id,
        "name": clan.name,
        "totem": clan.totem,
        "settlement_name": clan.settlement_name,
        "settlement_cell": list(clan.settlement_cell),
        "territory_cells": [list(c) for c in clan.territory_cells],
        "population": clan.population_size,
        "leader": {"id": leader.id, "name": leader.name} if leader else None,
        "matriarch": {"id": matriarch.id, "name": matriarch.name} if matriarch else None,
        "cosmogony": clan.cosmogony,
        "taboos": clan.taboos,
        "language": {"id": lang.id, "name": lang.name, "family": lang.family_name} if lang else None,
        "technologies": techs_detailed,
        "relations": relations_detailed,
        "founded_year": clan.founded_year,
        "members": members,
    }


@app.get("/universes/{universe_id}/languages")
def list_languages(universe_id: str) -> list[dict[str, Any]]:
    u = _get_universe(universe_id)
    res = []
    for lang in u.languages.languages.values():
        res.append({
            "id": lang.id,
            "name": lang.name,
            "family_name": lang.family_name,
            "parent_lang_id": lang.parent_lang_id,
            "drift_count": lang.drift_count,
            "lexicon_sample": {k: lang.lexicon[k] for k in list(lang.lexicon.keys())[:8]},
            "consonants": lang.consonants,
            "vowels": lang.vowels,
        })
    return res


@app.get("/universes/{universe_id}/languages/{lang_id}")
def get_language(universe_id: str, lang_id: int) -> dict[str, Any]:
    u = _get_universe(universe_id)
    lang = u.languages.languages.get(lang_id)
    if not lang:
        raise HTTPException(status_code=404, detail="Langue introuvable.")
    return lang.to_dict()


@app.get("/universes/{universe_id}/technology")
def get_technology(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    from engine.technology import TECH_CATALOG
    catalog = [
        {
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "prerequisites": t.prerequisites,
            "food_bonus": t.food_bonus,
            "health_bonus": t.health_bonus,
        }
        for t in TECH_CATALOG.values()
    ]
    clans_tech = []
    for clan in u.society.clans.values():
        cstate = u.technology.clan_states.get(clan.id)
        clans_tech.append({
            "clan_id": clan.id,
            "clan_name": clan.name,
            "unlocked_techs": cstate.unlocked_techs if cstate else [],
            "total_food_bonus": round(cstate.total_food_bonus(), 2) if cstate else 0.0,
            "total_health_bonus": round(cstate.total_health_bonus(), 2) if cstate else 0.0,
            "inventory": cstate.inventory if cstate else {},
        })
    return {
        "catalog": catalog,
        "clans_technology": clans_tech,
    }


@app.get("/universes/{universe_id}/chronicles")
def get_chronicles(universe_id: str, limit: int = 25) -> list[dict[str, Any]]:
    u = _get_universe(universe_id)
    return [e.to_dict() for e in u.chronicles.recent_tales(limit)]


@app.get("/universes/{universe_id}/wars")
def list_wars(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    active = [w.to_dict() for w in u.warfare.active_wars()]
    all_wars = [w.to_dict() for w in u.warfare.wars.values()]
    return {
        "active_wars": active,
        "all_wars": all_wars,
        "peace_treaties": u.warfare.peace_treaties,
    }


@app.post("/universes/{universe_id}/spawn", status_code=201)
def spawn_child_universe(universe_id: str, req: SpawnUniverseRequest) -> dict[str, Any]:
    parent = _get_universe(universe_id)
    if req.child_id in universes or store.exists(req.child_id):
        raise HTTPException(status_code=400, detail=f"L'univers '{req.child_id}' existe déjà.")

    child = parent.spawn_child(req.child_id, seed=req.seed, amplitude=req.amplitude)
    universes[child.id] = child
    store.save(child)
    multiverse.register(child)

    return {
        "message": "Univers enfant engendré avec succès",
        "parent_id": parent.id,
        "child_id": child.id,
        "constants": child.consts.to_dict(),
        "info": child.info(),
    }


@app.get("/universes/{universe_id}/lineage")
def get_lineage(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    multiverse.register(u)
    return multiverse.get_lineage(universe_id)


@app.get("/universes/{universe_id}/disasters")
def get_disasters(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    active = [d.to_dict() for d in u.disasters.active_disasters()]
    all_d = [d.to_dict() for d in u.disasters.disasters.values()]
    return {
        "active_disasters": active,
        "climate_cooling_offset": u.disasters.climate_temp_offset,
        "all_disasters": all_d,
    }


@app.get("/universes/{universe_id}/pantheon")
def get_pantheon(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return {
        "deities": [d.to_dict() for d in u.religion.deities.values()],
        "sacred_sites": [s.to_dict() for s in u.religion.sacred_sites.values()],
    }


@app.get("/universes/{universe_id}/settlements")
def get_settlements(universe_id: str) -> list[dict[str, Any]]:
    u = _get_universe(universe_id)
    return [s.to_dict() for s in u.settlements.settlements.values()]


@app.get("/universes/{universe_id}/justice")
def get_justice(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return {
        "legal_codes": [c.to_dict() for c in u.justice.legal_codes.values()],
        "trials": [t.to_dict() for t in u.justice.trials],
        "person_ranks": {str(k): v for k, v in u.justice.person_ranks.items()},
    }


@app.get("/universes/{universe_id}/trade")
def get_trade(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return {
        "routes": [r.to_dict() for r in u.trade.routes.values()],
        "expeditions": [e.to_dict() for e in u.trade.expeditions[-30:]],
        "clan_wealth": {str(k): v for k, v in u.trade.clan_wealth.items()},
    }


@app.get("/universes/{universe_id}/economy")
def get_economy(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return {
        "currencies": [c.to_dict() for c in u.economy.currencies.values()],
        "total_minted": u.economy.total_minted,
    }


@app.get("/universes/{universe_id}/realms")
def get_realms(universe_id: str) -> list[dict[str, Any]]:
    u = _get_universe(universe_id)
    return [k.to_dict() for k in u.realms.kingdoms.values()]


@app.get("/universes/{universe_id}/erudition")
def get_erudition(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return {
        "wonders": [w.to_dict() for w in u.erudition.wonders.values()],
        "golden_ages": {str(k): v for k, v in u.erudition.golden_ages.items()},
    }


@app.get("/universes/{universe_id}/cycle")
def get_cycle(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return u.ouroboros.cycle.to_dict()


def _get_universe(universe_id: str) -> Universe:
    if universe_id in universes:
        return universes[universe_id]
    if store.exists(universe_id):
        u = store.load(universe_id)
        universes[universe_id] = u
        return u
    raise HTTPException(status_code=404, detail=f"Univers '{universe_id}' introuvable.")
