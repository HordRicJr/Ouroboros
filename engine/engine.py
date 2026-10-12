"""Moteur de simulation (boucle de ticks, sans IA)."""
from __future__ import annotations

import io
import json

import numpy as np

from .budget import AIBudgetManager
from .climate import Climate, Weather
from .clock import Calendar, Date
from .constants import UniverseConstants
from .ecology import Ecosystem
from .events import Event
from .language import LanguageRegistry
from .llm import LLMClient
from .notable import NotableProfile
from .people import People
from .rng import Rng
from .society import Society
from .species import Species
from .technology import TechnologyRegistry
from .worldmap import WorldMap, generate_world

SEASONS_N = ["printemps", "été", "automne", "hiver"]  # hémisphère nord
ECO_DAYS = 7  # l'écosystème de masse avance par pas de 7 jours


class Universe:
    def __init__(self, universe_id: str, seed: int, consts: UniverseConstants | None = None,
                 start_year: int = 0, parent_id: str | None = None,
                 world: WorldMap | None = None, tick: int = 0,
                 eco: Ecosystem | None = None, people: People | None = None,
                 society: Society | None = None,
                 languages: LanguageRegistry | None = None,
                 technology: TechnologyRegistry | None = None,
                 notables: dict[int, NotableProfile] | None = None,
                 ai_budget: AIBudgetManager | None = None):
        self.id = universe_id
        self.seed = seed
        self.consts = consts or UniverseConstants()
        self.start_year = start_year
        self.parent_id = parent_id
        self.rng = Rng(seed)
        self.calendar = Calendar(self.consts.year_length_days, start_year)
        self.world = world or generate_world(self.consts, self.rng)
        self.climate = Climate(self.world, self.consts, self.rng)
        self.tick = tick
        self.eco = eco or Ecosystem.genesis(self.world, self.consts, self.rng, tick)
        self.people = people or People.genesis(self.eco, self.rng, tick)
        self.society = society or Society.genesis(self.people, self.eco, self.rng, self.world, tick)
        self.languages = languages or LanguageRegistry.genesis(self.rng)
        self.technology = technology or TechnologyRegistry.genesis(self.society)
        self.notables = notables if notables is not None else self._init_notables()
        self.ai_budget = ai_budget or AIBudgetManager()
        self.last_weather: Weather | None = None
        self.pending_events: list[Event] = []

    def _init_notables(self) -> dict[int, NotableProfile]:
        notables: dict[int, NotableProfile] = {}
        for p in self.people.persons.values():
            if p.notable:
                clan = self.society.get_person_clan(p.id)
                clan_name = f" ({clan.name})" if clan else ""
                title = f"Chef de clan{clan_name}" if p.sex == "M" else f"Matriarche{clan_name}"
                prof = NotableProfile(p.id, title=title)
                if clan:
                    prof.beliefs.append(f"Totem sacré du clan : {clan.totem}")
                    prof.beliefs.append(f"Mythe fondateur : {clan.cosmogony}")
                notables[p.id] = prof
        return notables

    @property
    def date(self) -> Date:
        return self.calendar.date_at(self.tick)

    def step(self, n: int = 1) -> list[Event]:
        """Avance de n jours simulés. Retourne les événements produits."""
        out: list[Event] = []
        for _ in range(n):
            d = self.calendar.date_at(self.tick)
            eco_tick = self.tick % ECO_DAYS == 0
            if eco_tick or d.day_of_year == 0:   # la météo n'est calculée que si nécessaire
                self.last_weather = self.climate.weather(self.tick, d.season_phase, d.year)
            if d.day_of_year == 0:
                out.append(Event(self.tick, "new_year", {"year": d.year, "leap": self.calendar.is_leap(d.year),
                                                         **self.last_weather.summary(self.world.is_land)}))
            q = d.year_length // 4
            if d.day_of_year % q == 0 and d.day_of_year // q < 4:
                out.append(Event(self.tick, "season_start", {"season": SEASONS_N[d.day_of_year // q], "year": d.year}))
            if eco_tick:
                out += self.eco.step(self.tick, self.last_weather, self.world, self.consts, self.rng,
                                     self.climate, ECO_DAYS)
            if d.day_of_year == 0:
                out += self.eco.yearly(self.tick, self.world, self.consts, self.rng, self.climate)
                tech_evs = self.technology.step(self.tick, d.year, self.society, self.world, self.rng)
                out += tech_evs
                lang_evs = self.languages.step(self.tick, d.year, self.rng.gen("lang", self.tick))
                for le in lang_evs:
                    out.append(Event(self.tick, le["type"], le))
            step_events = self.people.step(self.tick, self.eco, self.rng, self.consts.mutation_rate)
            out += step_events
            soc_events = self.society.step(self.tick, d.year, self.people, self.eco, self.rng, self.world, is_new_year=(d.day_of_year == 0))
            out += soc_events
            self._update_notables_memory(step_events + soc_events, d.year)
            self.tick += 1
        self.pending_events.extend(out)
        return out

    def _update_notables_memory(self, events: list[Event], year: int):
        for ev in events:
            if ev.type == "birth":
                m_id = ev.payload.get("mother_id")
                f_id = ev.payload.get("father_id")
                name = ev.payload.get("name")
                for parent in (m_id, f_id):
                    if parent in self.notables:
                        self.notables[parent].add_memory(self.tick, year, f"Naissance de mon enfant {name}", impact=0.8)
            elif ev.type == "marriage":
                hid = ev.payload.get("husband_id")
                wid = ev.payload.get("wife_id")
                hname = ev.payload.get("husband")
                wname = ev.payload.get("wife")
                if hid in self.notables:
                    self.notables[hid].add_memory(self.tick, year, f"Mon union sacrée avec {wname}", impact=0.7)
                if wid in self.notables:
                    self.notables[wid].add_memory(self.tick, year, f"Mon union sacrée avec {hname}", impact=0.7)
            elif ev.type == "death":
                pid = ev.payload.get("person_id")
                name = ev.payload.get("name")
                cause = ev.payload.get("cause")
                if pid in self.notables:
                    self.notables[pid].add_memory(self.tick, year, f"Dernier soupir emporté par {cause}", impact=1.0)
                for not_id, profile in self.notables.items():
                    if not_id != pid and self.people.are_kin(not_id, pid, 1):
                        profile.add_memory(self.tick, year, f"Deuil tragique de {name} ({cause})", impact=0.75)
            elif ev.type == "clan_leadership":
                new_leader_id = ev.payload.get("new_leader_id")
                clan_name = ev.payload.get("clan_name")
                if new_leader_id in self.notables:
                    self.notables[new_leader_id].add_memory(self.tick, year, f"Je suis devenu le chef de mon clan ({clan_name})", impact=0.9)
            elif ev.type == "cultural_drift":
                clan_id = ev.payload.get("clan_id")
                taboo = ev.payload.get("taboo_adopted")
                clan = self.society.clans.get(clan_id)
                if clan:
                    for mid in clan.member_ids:
                        if mid in self.notables:
                            self.notables[mid].add_memory(self.tick, year, f"Notre clan a adopté un nouvel interdit sacré : « {taboo} »", impact=0.6)
            elif ev.type == "clan_split":
                parent_clan_id = ev.payload.get("parent_clan_id")
                new_clan_name = ev.payload.get("new_clan_name")
                parent_clan = self.society.clans.get(parent_clan_id)
                if parent_clan:
                    for mid in parent_clan.member_ids:
                        if mid in self.notables:
                            self.notables[mid].add_memory(self.tick, year, f"Grande scission de notre peuple : départ des pionniers pour former {new_clan_name}", impact=0.85)
            elif ev.type == "clan_friction":
                c1_name = ev.payload.get("clan1_name")
                c2_name = ev.payload.get("clan2_name")
                c1_id = ev.payload.get("clan1_id")
                c2_id = ev.payload.get("clan2_id")
                for cid, other_name in [(c1_id, c2_name), (c2_id, c1_name)]:
                    c = self.society.clans.get(cid)
                    if c:
                        for mid in c.member_ids:
                            if mid in self.notables:
                                self.notables[mid].add_memory(self.tick, year, f"Tensions et rivalités frontalières avec le clan {other_name}", impact=0.7)
            elif ev.type == "clan_alliance":
                c1_name = ev.payload.get("clan1_name")
                c2_name = ev.payload.get("clan2_name")
                c1_id = ev.payload.get("clan1_id")
                c2_id = ev.payload.get("clan2_id")
                for cid, other_name in [(c1_id, c2_name), (c2_id, c1_name)]:
                    c = self.society.clans.get(cid)
                    if c:
                        for mid in c.member_ids:
                            if mid in self.notables:
                                self.notables[mid].add_memory(self.tick, year, f"Pacte de fraternité et d'amitié scellé avec le clan {other_name}", impact=0.7)
            elif ev.type == "tech_discovered":
                clan_id = ev.payload.get("clan_id")
                tech_name = ev.payload.get("tech_name")
                c = self.society.clans.get(clan_id)
                if c:
                    for mid in c.member_ids:
                        if mid in self.notables:
                            self.notables[mid].add_memory(self.tick, year, f"Notre peuple a découvert un nouveau savoir sacré : {tech_name}", impact=0.8)
            elif ev.type == "tech_shared":
                learner_id = ev.payload.get("learner_clan_id")
                tech_name = ev.payload.get("tech_name")
                teacher_name = ev.payload.get("teacher_clan_name")
                c = self.society.clans.get(learner_id)
                if c:
                    for mid in c.member_ids:
                        if mid in self.notables:
                            self.notables[mid].add_memory(self.tick, year, f"Nos amis du {teacher_name} nous ont enseigné : {tech_name}", impact=0.7)

    def drain_events(self) -> list[Event]:
        ev, self.pending_events = self.pending_events, []
        return ev

    # --- sérialisation (M05) -------------------------------------------------
    def snapshot(self) -> bytes:
        buf = io.BytesIO()
        meta = {"id": self.id, "seed": self.seed, "consts": self.consts.to_dict(),
                "start_year": self.start_year, "parent_id": self.parent_id, "tick": self.tick,
                "species": [s.to_dict() for s in self.eco.species],
                "human_cells": [list(c) for c in self.eco.human_cells],
                "people": self.people.to_dict(),
                "society": self.society.to_dict(),
                "languages": self.languages.to_dict(),
                "technology": self.technology.to_dict(),
                "notables": {str(k): v.to_dict() for k, v in self.notables.items()},
                "ai_budget": self.ai_budget.to_dict()}
        np.savez_compressed(buf, _meta=np.frombuffer(json.dumps(meta).encode(), dtype=np.uint8),
                            eco_N=self.eco.N, eco_T=self.eco.T, eco_feff=self.eco.feff, **self.world.to_arrays())
        return buf.getvalue()

    @classmethod
    def from_snapshot(cls, data: bytes) -> Universe:
        z = np.load(io.BytesIO(data))
        meta = json.loads(bytes(z["_meta"]).decode())
        world = WorldMap.from_arrays({k: z[k] for k in z.files if k not in ("_meta", "eco_N", "eco_T", "eco_feff")})
        eco = Ecosystem([Species.from_dict(s) for s in meta["species"]], z["eco_N"], z["eco_T"])
        eco.feff = z["eco_feff"]
        eco.human_cells = [tuple(c) for c in meta["human_cells"]]
        people = People.from_dict(meta["people"])
        society = Society.from_dict(meta["society"]) if "society" in meta else None
        languages = LanguageRegistry.from_dict(meta["languages"]) if "languages" in meta else None
        technology = TechnologyRegistry.from_dict(meta["technology"]) if "technology" in meta else None
        notables = {int(k): NotableProfile.from_dict(v) for k, v in meta.get("notables", {}).items()}
        ai_budget = AIBudgetManager.from_dict(meta.get("ai_budget", {})) if "ai_budget" in meta else None
        return cls(meta["id"], meta["seed"], UniverseConstants.from_dict(meta["consts"]),
                   meta["start_year"], meta["parent_id"], world, meta["tick"], eco, people, society,
                   languages, technology, notables, ai_budget)

    def ask_notable(self, person_id: int, question: str, llm_client: LLMClient | None = None) -> str:
        """Interroge un individu notable sous immersion totale en consommant le budget IA."""
        from .immersion import NotableAgent
        from .llm import MockLLMClient

        if not self.ai_budget.can_call(self.tick):
            return "L'esprit de cet habitant est plongé dans un profond sommeil ou ses devoirs quotidiens l'accaparent."

        if person_id not in self.notables:
            # S'il existe dans people mais pas encore notable, on l'élève
            if person_id in self.people.persons:
                p = self.people.persons[person_id]
                p.notable = True
                clan = self.society.get_person_clan(person_id)
                clan_name = f" ({clan.name})" if clan else ""
                self.notables[person_id] = NotableProfile(person_id, title=f"Habitant remarquable{clan_name}")
            else:
                return "Cet individu n'existe pas ou a disparu des mémoires."

        client = llm_client or MockLLMClient()
        agent = NotableAgent(person_id, self.notables[person_id], client)
        response = agent.ponder(question, self)
        # Enregistrer l'appel dans le gestionnaire de coût
        self.ai_budget.record_call(self.tick, tokens_used=180)
        return response

    def info(self) -> dict:
        d = self.date
        return {"id": self.id, "seed": self.seed, "tick": self.tick, "date": str(d), "year": d.year,
                "day_of_year": d.day_of_year, "parent_id": self.parent_id, "constants": self.consts.to_dict(),
                "clans_count": len(self.society.clans),
                "languages_count": len(self.languages.languages),
                "technologies_known": sum(len(s.unlocked_techs) for s in self.technology.clan_states.values()),
                "notables_count": len(self.notables), "ai_budget": self.ai_budget.to_dict()}
