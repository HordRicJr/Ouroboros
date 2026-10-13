"""Moteur de simulation (boucle de ticks, sans IA)."""
from __future__ import annotations

import io
import json

import numpy as np

from .budget import AIBudgetManager
from .chronicles import ChronicleKeeper
from .climate import Climate, Weather
from .clock import Calendar, Date
from .constants import UniverseConstants
from .disasters import DisasterManager
from .ecology import Ecosystem
from .economy import EconomyManager
from .erudition import EruditionManager
from .events import Event
from .justice import JusticeSystem
from .language import LanguageRegistry
from .llm import LLMClient
from .notable import NotableProfile
from .ouroboros_cycle import OuroborosCycleManager
from .people import People
from .realms import RealmManager
from .religion import ReligionRegistry
from .rng import Rng
from .settlement import SettlementManager
from .society import Society
from .species import Species
from .technology import TechnologyRegistry
from .trade import TradeNetwork
from .warfare import WarfareManager
from .worldmap import WorldMap, generate_world

SEASONS_N = ["printemps", "été", "automne", "hiver"]  # hémisphère nord
ECO_DAYS = 7  # l'écosystème de masse avance par pas de 7 jours


class Universe:
    def __init__(self, universe_id: str, seed: int, consts: UniverseConstants | None = None,
                 start_year: int = -4004, parent_id: str | None = None,
                 world: WorldMap | None = None, tick: int = 0,
                 eco: Ecosystem | None = None, people: People | None = None,
                 society: Society | None = None,
                 languages: LanguageRegistry | None = None,
                 technology: TechnologyRegistry | None = None,
                 warfare: WarfareManager | None = None,
                 chronicles: ChronicleKeeper | None = None,
                 disasters: DisasterManager | None = None,
                 religion: ReligionRegistry | None = None,
                 settlements: SettlementManager | None = None,
                 justice: JusticeSystem | None = None,
                 trade: TradeNetwork | None = None,
                 economy: EconomyManager | None = None,
                 realms: RealmManager | None = None,
                 erudition: EruditionManager | None = None,
                 ouroboros: OuroborosCycleManager | None = None,
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
        self.warfare = warfare or WarfareManager()
        self.chronicles = chronicles or ChronicleKeeper()
        self.disasters = disasters or DisasterManager()
        self.religion = religion or ReligionRegistry.genesis(self.rng)
        self.settlements = settlements or SettlementManager.genesis(self.society)
        self.justice = justice or JusticeSystem()
        self.justice.assign_ranks(self.society, self.people)
        self.trade = trade or TradeNetwork()
        self.economy = economy or EconomyManager()
        self.realms = realms or RealmManager()
        self.erudition = erudition or EruditionManager()
        self.ouroboros = ouroboros or OuroborosCycleManager()
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
                if p.id == 1 and p.mother_id is None:
                    title = "Patriarche Fondateur (Lignée d'Adan & Eva)"
                    grade = "Fondateur"
                    inf = 100
                elif p.id == 2 and p.mother_id is None:
                    title = "Matriarche Fondatrice (Lignée d'Adan & Eva)"
                    grade = "Fondatrice"
                    inf = 100
                else:
                    title = f"Chef de clan{clan_name}" if p.sex == "M" else f"Matriarche{clan_name}"
                    grade = "Chef de Clan" if p.sex == "M" else "Matriarche"
                    inf = 70
                prof = NotableProfile(p.id, title=title, rank_grade=grade, influence=inf)
                if clan:
                    prof.beliefs.append(f"Totem sacré du clan : {clan.totem}")
                    prof.beliefs.append(f"Mythe fondateur : {clan.cosmogony}")
                notables[p.id] = prof
        return notables

    def refresh_notables_hierarchy(self):
        """Met à jour dynamiquement la hiérarchie sociale et les grades des notables selon l'évolution du monde."""
        for p in self.people.alive_persons():
            # 1. Rôles fondateurs (Genèse originelle)
            if p.id == 1 and p.mother_id is None:
                p.notable = True
                prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                prof.title = "Patriarche Fondateur (Lignée d'Adan & Eva)"
                prof.rank_grade = "Fondateur"
                prof.influence = 100
                continue
            elif p.id == 2 and p.mother_id is None:
                p.notable = True
                prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                prof.title = "Matriarche Fondatrice (Lignée d'Adan & Eva)"
                prof.rank_grade = "Fondatrice"
                prof.influence = 100
                continue

            # 2. Rôles royaux (M23 - Royaumes & Souverains)
            is_ruler = False
            for k in self.realms.kingdoms.values():
                if k.ruler_id == p.id:
                    p.notable = True
                    prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                    prof.title = f"Haut-Roi du {k.name}" if p.sex == "M" else f"Reine Souveraine du {k.name}"
                    prof.rank_grade = "Souverain"
                    prof.influence = 95
                    is_ruler = True
                    break
            if is_ruler:
                continue

            clan = self.society.get_person_clan(p.id)
            clan_name = f" ({clan.name})" if clan else ""

            # 3. Chefs de clan temporels
            if clan and p.id == clan.leader_id:
                p.notable = True
                prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                prof.title = f"Chef de clan{clan_name}"
                prof.rank_grade = "Chef de Clan"
                prof.influence = 80
                continue

            # 4. Matriarches de clan
            if clan and p.id == clan.matriarch_id:
                p.notable = True
                prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                prof.title = f"Matriarche du clan{clan_name}"
                prof.rank_grade = "Matriarche"
                prof.influence = 75
                continue

            # 5. Rôles spirituels : Gardien de site sacré (M18 - Religion)
            has_sacred_role = False
            if clan:
                for site in self.religion.sacred_sites.values():
                    if site.clan_id == clan.id and self.people.age_years(p, self.tick) >= 18:
                        p.notable = True
                        prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                        prof.title = f"Grand Chamane du {site.name}" if p.sex == "M" else f"Grande Prêtresse du {site.name}"
                        prof.rank_grade = "Grand Chamane"
                        prof.influence = 65
                        has_sacred_role = True
                        break
            if has_sacred_role:
                continue

            # 6. Rôles judiciaires : Juge coutumier (M20 - Justice)
            if clan and clan.id in self.justice.legal_codes and self.people.age_years(p, self.tick) >= 22:
                p.notable = True
                prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                code = self.justice.legal_codes[clan.id]
                prof.title = f"Juge Coutumier ({code.law_name})"
                prof.rank_grade = "Juge Coutumier"
                prof.influence = 60
                continue

            # 7. Rôles militaires : Capitaine de Guerre (M14 - Warfare)
            if (
                clan
                and any(w.active and clan.id in (w.attacker_clan_id, w.defender_clan_id) for w in self.warfare.wars.values())
                and p.sex == "M"
                and self.people.age_years(p, self.tick) >= 18
            ):
                p.notable = True
                prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                prof.title = f"Capitaine de Guerre{clan_name}"
                prof.rank_grade = "Capitaine de Guerre"
                prof.influence = 55
                continue

            # 8. Doyen du Conseil des Anciens (âge >= 40 ans dans la communauté)
            if self.people.age_years(p, self.tick) >= 40 and clan and p.notable:
                prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                prof.title = f"Doyen du Conseil des Anciens{clan_name}"
                prof.rank_grade = "Doyen du Conseil"
                prof.influence = 50
                continue

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
            disaster_evs = self.disasters.step(self.tick, d.year, self.world, self.climate, self.eco, self.society, self.people, self.rng)
            out += disaster_evs
            if d.day_of_year == 0:
                out += self.eco.yearly(self.tick, self.world, self.consts, self.rng, self.climate)
                tech_evs = self.technology.step(self.tick, d.year, self.society, self.world, self.rng)
                out += tech_evs
                lang_evs = self.languages.step(self.tick, d.year, self.rng.gen("lang", self.tick))
                for le in lang_evs:
                    out.append(Event(self.tick, le["type"], le))
                war_evs = self.warfare.step(self.tick, d.year, self.society, self.people, self.technology, self.world, self.rng)
                out += war_evs
                rel_evs = self.religion.step(self.tick, d.year, self.society, self.people, self.rng)
                out += rel_evs
                set_evs = self.settlements.step(self.tick, d.year, self.society, self.people, self.technology, self.rng)
                out += set_evs
                just_evs = self.justice.step(self.tick, d.year, self.society, self.people, self.rng)
                out += just_evs
                trade_evs = self.trade.step(self.tick, d.year, self.society, self.settlements, self.rng)
                out += trade_evs
                econ_evs = self.economy.step(self.tick, d.year, self.society, self.trade, self.rng)
                out += econ_evs
                realm_evs = self.realms.step(self.tick, d.year, self.society, self.people, self.rng)
                out += realm_evs
                erud_evs = self.erudition.step(self.tick, d.year, self.society, self.rng)
                out += erud_evs
                ouro_evs = self.ouroboros.step(self.tick, d.year, self.society, self.realms, self.rng)
                out += ouro_evs
            step_events = self.people.step(self.tick, self.eco, self.rng, self.consts.mutation_rate)
            out += step_events
            soc_events = self.society.step(self.tick, d.year, self.people, self.eco, self.rng, self.world, is_new_year=(d.day_of_year == 0))
            out += soc_events
            yearly_addons = (tech_evs + war_evs + rel_evs + set_evs + just_evs + trade_evs + econ_evs + realm_evs + erud_evs + ouro_evs) if d.day_of_year == 0 else []
            all_step_evs = step_events + soc_events + disaster_evs + yearly_addons
            if d.day_of_year == 0:
                self.chronicles.record_from_events(all_step_evs, d.year, self.tick)
            self._update_notables_memory(all_step_evs, d.year)
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
                if new_leader_id and new_leader_id not in self.notables and new_leader_id in self.people.persons:
                    p = self.people.persons[new_leader_id]
                    p.notable = True
                    clan = self.society.get_person_clan(new_leader_id)
                    title = f"Patriarche ({clan_name})" if p.sex == "M" else f"Matriarche ({clan_name})"
                    prof = NotableProfile(p.id, title=title)
                    if clan:
                        prof.beliefs.append(f"Totem sacré : {clan.totem}")
                        prof.beliefs.append(f"Mythe fondateur : {clan.cosmogony}")
                    self.notables[new_leader_id] = prof
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
                new_clan_id = ev.payload.get("new_clan_id")
                new_clan = self.society.clans.get(new_clan_id)
                if new_clan:
                    for lid in (new_clan.leader_id, new_clan.matriarch_id):
                        if lid and lid not in self.notables and lid in self.people.persons:
                            lp = self.people.persons[lid]
                            lp.notable = True
                            ltitle = f"Fondateur ({new_clan_name})" if lp.sex == "M" else f"Mère fondatrice ({new_clan_name})"
                            nprof = NotableProfile(lp.id, title=ltitle)
                            nprof.beliefs.append(f"Totem sacré : {new_clan.totem}")
                            nprof.beliefs.append(f"Mythe fondateur : {new_clan.cosmogony}")
                            self.notables[lp.id] = nprof
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
            elif ev.type == "war_declared":
                att_id = ev.payload.get("attacker_clan_id")
                def_id = ev.payload.get("defender_clan_id")
                att_name = ev.payload.get("attacker_clan_name")
                def_name = ev.payload.get("defender_clan_name")
                for cid, enemy in [(att_id, def_name), (def_id, att_name)]:
                    c = self.society.clans.get(cid)
                    if c:
                        for mid in c.member_ids:
                            if mid in self.notables:
                                self.notables[mid].add_memory(self.tick, year, f"Guerre déclarée contre le {enemy} !", impact=0.95)
            elif ev.type == "peace_treaty":
                c1_id = ev.payload.get("clan1_id")
                c2_id = ev.payload.get("clan2_id")
                c1_name = ev.payload.get("clan1_name")
                c2_name = ev.payload.get("clan2_name")
                for cid, other in [(c1_id, c2_name), (c2_id, c1_name)]:
                    c = self.society.clans.get(cid)
                    if c:
                        for mid in c.member_ids:
                            if mid in self.notables:
                                self.notables[mid].add_memory(self.tick, year, f"Traité de paix signé avec le {other}", impact=0.85)
            elif ev.type == "disaster_started":
                dis_name = ev.payload.get("name")
                desc = ev.payload.get("description", "")
                for prof in self.notables.values():
                    prof.add_memory(self.tick, year, f"Un cataclysme a frappé notre monde : {dis_name}. {desc}", impact=0.9)
            elif ev.type == "sacred_site_erected":
                site_name = ev.payload.get("site_name")
                clan_id = ev.payload.get("clan_id")
                c = self.society.clans.get(clan_id)
                if c:
                    for mid in c.member_ids:
                        if mid in self.notables:
                            self.notables[mid].add_memory(self.tick, year, f"Érection d'un lieu sacré pour nos dieux : {site_name}", impact=0.8)
            elif ev.type == "settlement_upgraded":
                sname = ev.payload.get("name")
                tname = ev.payload.get("tier_name")
                clan_id = ev.payload.get("clan_id")
                c = self.society.clans.get(clan_id)
                if c:
                    for mid in c.member_ids:
                        if mid in self.notables:
                            self.notables[mid].add_memory(self.tick, year, f"Notre campement {sname} s'élève au rang de {tname} !", impact=0.85)
            elif ev.type == "law_enacted":
                lname = ev.payload.get("law_name")
                clan_id = ev.payload.get("clan_id")
                c = self.society.clans.get(clan_id)
                if c:
                    for mid in c.member_ids:
                        if mid in self.notables:
                            self.notables[mid].add_memory(self.tick, year, f"Notre clan a édicté une grande loi coutumière : {lname}", impact=0.8)
            elif ev.type == "trial_held":
                accused_id = ev.payload.get("accused_id")
                verdict = ev.payload.get("verdict")
                punishment = ev.payload.get("punishment")
                if accused_id in self.notables:
                    self.notables[accused_id].add_memory(self.tick, year, f"J'ai été jugé par les anciens ({verdict}) : {punishment}", impact=0.9)

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
                "warfare": self.warfare.to_dict(),
                "chronicles": self.chronicles.to_dict(),
                "disasters": self.disasters.to_dict(),
                "religion": self.religion.to_dict(),
                "settlements": self.settlements.to_dict(),
                "justice": self.justice.to_dict(),
                "trade": self.trade.to_dict(),
                "economy": self.economy.to_dict(),
                "realms": self.realms.to_dict(),
                "erudition": self.erudition.to_dict(),
                "ouroboros": self.ouroboros.to_dict(),
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
        warfare = WarfareManager.from_dict(meta["warfare"]) if "warfare" in meta else None
        chronicles = ChronicleKeeper.from_dict(meta["chronicles"]) if "chronicles" in meta else None
        disasters = DisasterManager.from_dict(meta["disasters"]) if "disasters" in meta else None
        religion = ReligionRegistry.from_dict(meta["religion"]) if "religion" in meta else None
        settlements = SettlementManager.from_dict(meta["settlements"]) if "settlements" in meta else None
        justice = JusticeSystem.from_dict(meta["justice"]) if "justice" in meta else None
        trade = TradeNetwork.from_dict(meta["trade"]) if "trade" in meta else None
        economy = EconomyManager.from_dict(meta["economy"]) if "economy" in meta else None
        realms = RealmManager.from_dict(meta["realms"]) if "realms" in meta else None
        erudition = EruditionManager.from_dict(meta["erudition"]) if "erudition" in meta else None
        ouroboros = OuroborosCycleManager.from_dict(meta["ouroboros"]) if "ouroboros" in meta else None
        notables = {int(k): NotableProfile.from_dict(v) for k, v in meta.get("notables", {}).items()}
        ai_budget = AIBudgetManager.from_dict(meta.get("ai_budget", {})) if "ai_budget" in meta else None
        return cls(meta["id"], meta["seed"], UniverseConstants.from_dict(meta["consts"]),
                   meta["start_year"], meta["parent_id"], world, meta["tick"], eco, people, society,
                   languages, technology, warfare, chronicles, disasters, religion, settlements,
                   justice, trade, economy, realms, erudition, ouroboros, notables, ai_budget)

    def ask_notable(self, person_id: int, question: str, llm_client: LLMClient | None = None) -> str:
        """Interroge un individu notable sous immersion totale en consommant le budget IA."""
        from .immersion import NotableAgent
        from .llm import MockLLMClient

        if not self.ai_budget.can_call(self.tick):
            return "L'esprit de cet habitant est plongé dans un profond sommeil ou ses devoirs quotidiens l'accaparent."

        self.refresh_notables_hierarchy()

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

        prof = self.notables[person_id]
        p = self.people.persons[person_id]
        client = llm_client or MockLLMClient()
        agent = NotableAgent(person_id, prof, client)
        response = agent.ponder(question, self)

        # Enregistrer l'entretien dans la mémoire de l'habitant
        prof.add_memory(self.tick, self.date.year, f"Entretien avec le Voyageur Céleste : « {question[:50]} »", impact=0.85)
        prof.influence = min(100, prof.influence + 2)

        # Si le joueur prescrit un tabou ou un interdit sacré
        q_lower = question.lower()
        if any(w in q_lower for w in ["tabou", "interdit", "défendu", "ne dois pas", "ne mange pas", "ne touchez pas", "défense de", "ne consomme pas"]):
            taboo_candidate = "Interdit sacré transmis par le Voyageur"
            for obj in ["pomme", "pommes", "fruit", "fruits", "viande", "sang", "arbre", "nuit", "feu", "eau", "chasse"]:
                if obj in q_lower:
                    taboo_candidate = f"Interdit sacré : ne point consommer ou toucher {obj}"
                    break
            clan_obj = self.society.get_person_clan(p.id)
            if clan_obj and taboo_candidate not in clan_obj.taboos:
                clan_obj.taboos.append(taboo_candidate)
            if taboo_candidate not in prof.beliefs:
                prof.beliefs.append(taboo_candidate)
            prof.add_memory(self.tick, self.date.year, f"Le Voyageur céleste nous a ordonné un interdit sacré : « {taboo_candidate} »", impact=0.95)

        # Si le joueur donne un conseil spirituel ou de sagesse, enrichir ses croyances
        if any(w in q_lower for w in ["paix", "harmonie", "dieu", "étoile", "nature", "amour", "veillez", "ensemble"]):
            prof.beliefs.append(f"Inspiration reçue du Voyageur : « {question[:45]}... »")

        # Inscrire l'événement dans les chroniques du monde
        clan = self.society.get_person_clan(p.id)
        self.chronicles.record(
            tick=self.tick,
            year=self.date.year,
            category="communion",
            title=f"Communion du Voyageur avec {p.name}",
            narrative=f"Une présence mystérieuse s'est entretenue avec {p.name} ({prof.title}), marquant à jamais son esprit.",
            clans=[clan.name] if clan else [],
        )

        # Enregistrer l'appel dans le gestionnaire de coût
        self.ai_budget.record_call(self.tick, tokens_used=180)
        return response

    def spawn_child(self, child_id: str, seed: int | None = None, amplitude: float = 0.05) -> Universe:
        """Génère un univers enfant récursif avec dérivation des constantes."""
        child_seed = seed if seed is not None else self.rng.child_seed(f"child-{child_id}")
        child_consts = self.consts.mutate(self.rng, amplitude=amplitude)
        return Universe(
            universe_id=child_id,
            seed=child_seed,
            consts=child_consts,
            start_year=0,
            parent_id=self.id,
        )

    def info(self) -> dict:
        d = self.date
        season_idx = int(d.season_phase * 4) % 4
        season_name = SEASONS_N[season_idx].capitalize()
        alive_people = self.people.alive_persons()
        living_notables = [p for p in self.notables.values() if self.people.persons.get(p.person_id) and self.people.persons[p.person_id].alive]
        h_species = [i for i, s in enumerate(self.eco.species) if s.kind == "human"]
        macro_pop = round(float(self.eco.N[h_species[0]].sum()), 1) if h_species else float(len(alive_people))

        return {
            "id": self.id,
            "seed": self.seed,
            "tick": self.tick,
            "date": str(d),
            "year": d.year,
            "start_year": self.start_year,
            "day_of_year": d.day_of_year,
            "day": d.day_of_year + 1,
            "year_length": d.year_length,
            "season": season_name,
            "season_phase": round(d.season_phase, 3),
            "parent_id": self.parent_id,
            "constants": self.consts.to_dict(),
            "population": len(alive_people),
            "total_born": len(self.people.persons),
            "macro_population": macro_pop,
            "clans_count": len(self.society.clans),
            "languages_count": len(self.languages.languages),
            "technologies_known": sum(len(s.unlocked_techs) for s in self.technology.clan_states.values()),
            "active_wars_count": len(self.warfare.active_wars()),
            "chronicles_count": len(self.chronicles.entries),
            "active_disasters_count": len(self.disasters.active_disasters()),
            "sacred_sites_count": len(self.religion.sacred_sites),
            "settlements_count": len(self.settlements.settlements),
            "legal_codes_count": len(self.justice.legal_codes),
            "trials_count": len(self.justice.trials),
            "trade_routes_count": len(self.trade.routes),
            "expeditions_count": len(self.trade.expeditions),
            "currencies_count": len(self.economy.currencies),
            "kingdoms_count": len(self.realms.kingdoms),
            "wonders_count": len(self.erudition.wonders),
            "civilization_phase": self.ouroboros.cycle.current_phase,
            "ouroboros_cycle": self.ouroboros.cycle.cycle_number,
            "notables_count": len(living_notables),
            "total_notables_count": len(self.notables),
            "ai_budget": self.ai_budget.to_dict(),
        }
