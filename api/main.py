"""API FastAPI d'Ouroboros démarrée avec uvicorn api.main:app"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine.constants import UniverseConstants
from engine.engine import Universe
from engine.experiment import fork_universe_state
from engine.llm import HuggingFaceClient, MockLLMClient
from engine.multiverse import MultiverseRegistry
from engine.persistence import PostgresStore, SQLiteStore, Store

logger = logging.getLogger("ouroboros.api")

# Registre local et persistance (Postgres si configuré, sinon SQLite durable sur disque)
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres"):
    store: Store = PostgresStore(database_url)
    try:
        store.init()
    except (RuntimeError, ValueError, OSError) as exc:
        logger.warning("Impossible d'initialiser Postgres, repli sur SQLite: %s", exc)
        store = SQLiteStore("data/ouroboros.db")
else:
    store = SQLiteStore("data/ouroboros.db")

multiverse: MultiverseRegistry = MultiverseRegistry()
universes: dict[str, Universe] = {}

# Tâches asynchrones de simulation continue H24
_running_tasks: dict[str, asyncio.Task[None]] = {}
_running_speeds: dict[str, float] = {"main": 1.0}


_main_event_loop: asyncio.AbstractEventLoop | None = None


async def _universe_step_loop(universe_id: str):
    logger.info("Boucle de simulation continue H24 démarrée pour '%s'", universe_id)
    step_count = 0
    try:
        while True:
            speed = _running_speeds.get(universe_id, 1.0)
            delay = max(0.05, 1.0 / max(speed, 0.1))
            await asyncio.sleep(delay)
            u = universes.get(universe_id)
            if u:
                u.step(1)
                step_count += 1
                if step_count % 10 == 0:
                    try:
                        store.save(u)
                    except (RuntimeError, ValueError, OSError) as s_err:
                        logger.error("Erreur de sauvegarde périodique de '%s': %s", universe_id, s_err)
    except asyncio.CancelledError:
        logger.info("Boucle de simulation continue stoppée pour '%s'", universe_id)
        u = universes.get(universe_id)
        if u:
            try:
                store.save(u)
            except (RuntimeError, ValueError, OSError):
                pass
    except Exception:
        logger.exception("Erreur durant la simulation continue de '%s'", universe_id)


def _start_universe_loop(universe_id: str, speed: float = 1.0):
    _running_speeds[universe_id] = speed
    task = _running_tasks.get(universe_id)
    if task is None or task.done():
        loop = _main_event_loop
        if loop is None or loop.is_closed():
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
        if loop and not loop.is_closed():
            _running_tasks[universe_id] = loop.create_task(_universe_step_loop(universe_id))
        else:
            logger.error("Impossible de démarrer la simulation continue '%s': aucune boucle asyncio disponible", universe_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_event_loop
    _main_event_loop = asyncio.get_running_loop()
    # Démarrage automatique H24 de l'univers principal dès le lancement du serveur
    logger.info("Démarrage du service Ouroboros API - Lancement de la simulation H24 pour 'main'...")
    _start_universe_loop("main", speed=1.0)
    yield
    # Arrêt propre lors de l'arrêt du serveur
    logger.info("Arrêt du service Ouroboros API...")
    for uid, task in list(_running_tasks.items()):
        if not task.done():
            task.cancel()
    _running_tasks.clear()


app = FastAPI(
    title="Ouroboros API",
    version="1.0.0",
    description="API FastAPI pour le simulateur récursif d'univers Ouroboros.",
    lifespan=lifespan,
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

# Initialisation ou chargement persistant de l'univers 'main'
if store.exists("main"):
    try:
        _default_u = store.load("main")
        logger.info("Univers 'main' chargé depuis la persistance (Tick: %d, Date: %s)", _default_u.tick, _default_u.date)
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        logger.warning("Erreur chargement 'main': %s - réinitialisation", exc)
        _default_u = Universe("main", 42, start_year=-4004)
        store.save(_default_u)
else:
    _default_u = Universe("main", 42, start_year=-4004)
    store.save(_default_u)

universes["main"] = _default_u
multiverse.register(_default_u)


class CreateUniverseRequest(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "eden-01"})
    seed: int = Field(default=42, json_schema_extra={"example": 42})
    start_year: int = Field(default=-4004, json_schema_extra={"example": -4004})
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


class ForkUniverseRequest(BaseModel):
    child_id: str = Field(..., description="Identifiant unique du nouvel univers branché")
    description: str = Field(default="", description="Objectif scientifique ou intervention de la branche")


# --- Endpoints de base et santé requis par le serveur ---
@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "api": "ok"}


@app.get("/api/diagnostic/system")
def get_system_diagnostic() -> dict[str, Any]:
    import subprocess

    import httpx

    llama_health = "unknown"
    try:
        with httpx.Client(timeout=2.0) as client:
            r = client.get("http://127.0.0.1:8080/health")
            llama_health = f"ok ({r.status_code})" if r.status_code == 200 else f"error ({r.status_code})"
    except (httpx.HTTPError, OSError) as e:
        llama_health = f"failed ({type(e).__name__}: {e})"

    svc_status = ""
    try:
        res = subprocess.run(["systemctl", "status", "ouroboros-llm"], check=False, capture_output=True, text=True, timeout=4)
        svc_status = res.stdout[:500] if res.stdout else res.stderr[:500]
    except (subprocess.SubprocessError, OSError) as e:
        svc_status = str(e)

    models_files: list[str] = []
    models_dir = os.path.expanduser("~/ouroboros/models")
    if os.path.exists(models_dir):
        try:
            models_files = os.listdir(models_dir)
        except OSError:
            pass

    log_tail = ""
    log_file = os.path.expanduser("~/ouroboros/logs/models.log")
    if os.path.exists(log_file):
        try:
            with open(log_file, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                log_tail = "".join(lines[-25:])
        except OSError:
            pass

    ram_info = ""
    try:
        res = subprocess.run(["free", "-h"], check=False, capture_output=True, text=True, timeout=4)
        ram_info = res.stdout if res.stdout else res.stderr
    except (subprocess.SubprocessError, OSError) as e:
        ram_info = str(e)

    return {
        "llama_health": llama_health,
        "service_status": svc_status,
        "models_files": models_files,
        "models_log_tail": log_tail,
        "ram": ram_info,
        "env_hf_token": bool(os.environ.get("HF_TOKEN")),
        "env_llm_endpoint": os.environ.get("LLM_ENDPOINT", ""),
    }


@app.get("/api/diagnostic/llm_test")
def test_local_llm(prompt: str = "Dis bonjour en une phrase.") -> dict[str, Any]:
    import time

    import httpx

    t0 = time.time()
    result = ""
    error = None
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "http://127.0.0.1:8080/v1/chat/completions",
                json={
                    "model": "local",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.7,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    result = data["choices"][0]["message"]["content"]
            else:
                error = f"HTTP {resp.status_code}: {resp.text[:200]}"
    except (httpx.HTTPError, OSError) as e:
        error = f"{type(e).__name__}: {e}"

    duration = round(time.time() - t0, 2)
    return {
        "result": result,
        "duration_sec": duration,
        "error": error,
    }


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
async def get_universe(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    info = u.info()
    task = _running_tasks.get(universe_id)
    info["is_running"] = task is not None and not task.done()
    info["speed"] = _running_speeds.get(universe_id, 1.0)
    return info


@app.post("/universes/{universe_id}/play")
async def play_universe(universe_id: str, speed: float = 1.0) -> dict[str, Any]:
    u = _get_universe(universe_id)
    _start_universe_loop(universe_id, speed)
    return {
        "message": f"Simulation de l'univers '{universe_id}' active H24",
        "running": True,
        "speed": speed,
        "tick": u.tick,
        "date": str(u.date),
    }


@app.post("/universes/{universe_id}/pause")
async def pause_universe(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    task = _running_tasks.pop(universe_id, None)
    if task and not task.done():
        task.cancel()
    store.save(u)
    return {
        "message": f"Simulation de l'univers '{universe_id}' mise en pause",
        "running": False,
        "tick": u.tick,
        "date": str(u.date),
    }


@app.post("/universes/{universe_id}/speed")
async def speed_universe(universe_id: str, speed: float = 1.0) -> dict[str, Any]:
    u = _get_universe(universe_id)
    _running_speeds[universe_id] = speed
    task = _running_tasks.get(universe_id)
    is_running = task is not None and not task.done()
    return {
        "id": universe_id,
        "speed": speed,
        "running": is_running,
        "tick": u.tick,
    }


@app.get("/universes/{universe_id}/status")
async def status_universe(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    task = _running_tasks.get(universe_id)
    is_running = task is not None and not task.done()
    return {
        "id": universe_id,
        "running": is_running,
        "speed": _running_speeds.get(universe_id, 1.0),
        "tick": u.tick,
        "date": str(u.date),
    }


@app.post("/universes/{universe_id}/step")
async def step_universe(universe_id: str, req: StepRequest) -> dict[str, Any]:
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
async def reset_universe(universe_id: str) -> dict[str, Any]:
    u_old = _get_universe(universe_id)
    task = _running_tasks.pop(universe_id, None)
    if task and not task.done():
        task.cancel()
    # Réinitialisation à neuf avec la même graine (commencement biblique en 4004 av. J.-C.)
    target_start_year = -4004 if (universe_id == "main" or u_old.start_year == 0) else u_old.start_year
    u_new = Universe(u_old.id, u_old.seed, consts=u_old.consts, start_year=target_start_year, parent_id=u_old.parent_id)
    universes[universe_id] = u_new
    store.save(u_new)
    # Relancer immédiatement la simulation H24 au jour 0
    _start_universe_loop(universe_id, _running_speeds.get(universe_id, 1.0))
    return {
        "message": f"Univers '{universe_id}' réinitialisé au commencement (bande pionnière de chasseurs-cueilleurs).",
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
    u.refresh_notables_hierarchy()
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
                "rank_grade": not_prof.rank_grade,
                "influence": not_prof.influence,
                "beliefs": list(not_prof.beliefs),
                "memories_count": len(not_prof.memories),
            })
    return res


@app.get("/universes/{universe_id}/people")
def get_people(universe_id: str) -> list[dict[str, Any]]:
    u = _get_universe(universe_id)
    res = []
    for p in u.people.persons.values():
        clan = u.society.get_person_clan(p.id)
        age = u.people.age_years(p, u.tick)
        if p.id in u.notables and u.notables[p.id].rank_grade:
            role = u.notables[p.id].rank_grade
        elif age < 3:
            role = "Nourrisson" if p.sex == "M" else "Nourrissonne"
        elif age < 14:
            role = "Enfant (Garçon)" if p.sex == "M" else "Enfant (Fille)"
        elif age >= 48:
            role = "Doyen du clan" if p.sex == "M" else "Doyenne du clan"
        else:
            role = "Chasseur-pêcheur" if p.sex == "M" else "Collectrice"

        res.append({
            "id": p.id,
            "name": p.name,
            "sex": p.sex,
            "age": round(age, 1),
            "alive": p.alive,
            "cell": p.cell,
            "notable": p.notable,
            "role": role,
            "clan_name": clan.name if clan else None,
            "mother_id": p.mother_id,
            "father_id": p.father_id,
        })
    return res


@app.post("/universes/{universe_id}/notables/{person_id}/ask")
def ask_notable_endpoint(universe_id: str, person_id: int, req: AskNotableRequest) -> dict[str, Any]:
    u = _get_universe(universe_id)
    client = MockLLMClient() if req.mock else HuggingFaceClient()
    response = u.ask_notable(person_id, req.question, llm_client=client)
    prof = u.notables.get(person_id)
    store.save(u)
    return {
        "person_id": person_id,
        "question": req.question,
        "response": response,
        "title": prof.title if prof else "",
        "rank_grade": prof.rank_grade if prof else "Dirigeant",
        "influence": prof.influence if prof else 20,
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


# --- Endpoints de Recherche, Mesures Émergentes & Reproductibilité (PIMMUR) ---
@app.get("/universes/{universe_id}/metrics")
def get_metrics(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return {
        "summary": u.metrics_history.get_summary(),
        "latest": u.metrics_history.get_latest(),
        "history": u.metrics_history.to_dict()[-50:],
        "social_graph": u.social_graph.to_dict(),
        "branch": u.branch_metadata.to_dict(),
    }


@app.get("/universes/{universe_id}/metrics/export")
def export_metrics(universe_id: str, format: str = Query("csv", description="Format d'exportation: csv ou json")) -> Any:
    u = _get_universe(universe_id)
    if format.lower() == "csv":
        csv_data = u.metrics_history.export_csv()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=ouroboros_metrics_{universe_id}.csv"},
        )
    return u.metrics_history.to_dict()


@app.post("/universes/{universe_id}/fork")
def fork_universe_endpoint(universe_id: str, req: ForkUniverseRequest) -> dict[str, Any]:
    if req.child_id in universes or store.exists(req.child_id):
        raise HTTPException(status_code=400, detail=f"L'univers '{req.child_id}' existe déjà.")
    parent_u = _get_universe(universe_id)
    child_u = fork_universe_state(parent_u, req.child_id, "observer_intervention", req.description)
    universes[req.child_id] = child_u
    multiverse.register(child_u)
    store.save(child_u)
    return {
        "message": f"Branche expérimentale '{req.child_id}' créée à partir de '{universe_id}'",
        "parent_id": universe_id,
        "child_id": req.child_id,
        "info": child_u.info(),
    }


@app.get("/universes/{universe_id}/ai_logs")
def get_ai_logs(universe_id: str, limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return {
        "total_calls": u.ai_logger.counter,
        "logs": u.ai_logger.get_recent(limit=limit),
    }


@app.get("/universes/{universe_id}/research_protocol")
def get_research_protocol(universe_id: str) -> dict[str, Any]:
    u = _get_universe(universe_id)
    return {
        "universe_id": universe_id,
        "branch_type": u.branch_metadata.branch_type,
        "parent_universe_id": u.branch_metadata.parent_universe_id,
        "principles_compliance": {
            "profile": "Profils différenciés Big Five avec héritabilité génétique partielle",
            "interaction": "Perception locale stricte sans résumés statistiques dans les prompts",
            "memory": "Flux de mémoire épisodique avec oubli exponentiel et réflexion périodique",
            "minimal_control": "Prompts purement descriptifs, aucune consigne prescriptive de comportement",
            "unawareness": "Aucune mention de la simulation ou d'hypothèses dans les échanges",
            "realism": "Calibration démographique (mortalité, longévité, fertilité)",
        },
        "model_architecture": {
            "engine": "Ouroboros Pure Emergent Engine",
            "llm_model": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "ai_budget_mode": "Décisionnel sélectif (pas d'appel systématique par tick)",
        },
    }


def _get_universe(universe_id: str) -> Universe:
    if universe_id in universes:
        return universes[universe_id]
    if store.exists(universe_id):
        u = store.load(universe_id)
        universes[universe_id] = u
        return u
    raise HTTPException(status_code=404, detail=f"Univers '{universe_id}' introuvable.")
