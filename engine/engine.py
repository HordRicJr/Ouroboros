"""Moteur de simulation (boucle de ticks, sans IA)."""
from __future__ import annotations

import io
import json

import numpy as np

from .agent_cognition import AgentCognition
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
from .experiment import AICallLogger, BranchMetadata
from .justice import JusticeSystem
from .language import LanguageRegistry
from .llm import LLMClient
from .metrics import (
    SeasonalMetricsSnapshot,
    SimulationMetricsHistory,
    calculate_gini,
    calculate_shannon_entropy,
)
from .notable import NotableProfile
from .ouroboros_cycle import OuroborosCycleManager
from .people import People
from .realms import RealmManager
from .religion import ReligionRegistry
from .rng import Rng
from .settlement import SettlementManager
from .social_graph import SocialGraph
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
                 ai_budget: AIBudgetManager | None = None,
                 social_graph: SocialGraph | None = None,
                 agent_cognitions: dict[int, AgentCognition] | None = None,
                 metrics_history: SimulationMetricsHistory | None = None,
                 ai_logger: AICallLogger | None = None,
                 branch_metadata: BranchMetadata | None = None):
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

        # Architecture cognitive émergente PIMMUR & Sociométrie
        self.social_graph = social_graph or SocialGraph()
        self.agent_cognitions = agent_cognitions if agent_cognitions is not None else self._init_agent_cognitions()
        self.metrics_history = metrics_history or SimulationMetricsHistory()
        self.ai_logger = ai_logger or AICallLogger()
        self.branch_metadata = branch_metadata or BranchMetadata(universe_id=universe_id)

        self.notables = notables if notables is not None else self._init_notables()
        self.ai_budget = ai_budget or AIBudgetManager()
        self.last_weather: Weather | None = None
        self.pending_events: list[Event] = []

    def _init_agent_cognitions(self) -> dict[int, AgentCognition]:
        cogs: dict[int, AgentCognition] = {}
        for p in self.people.persons.values():
            cog = AgentCognition.create_random(p.id, seed=self.seed + p.id)
            biome = self.world.biome_name(*p.cell)
            cog.known_facts.add(f"Vit dans les contrées de {biome}")
            if p.spouse_ids:
                sp_names = [self.people.persons[sid].name for sid in p.spouse_ids if sid in self.people.persons]
                if sp_names:
                    cog.known_facts.add(f"Lié à {', '.join(sp_names)}")
            cogs[p.id] = cog
        return cogs

    def _init_notables(self) -> dict[int, NotableProfile]:
        notables: dict[int, NotableProfile] = {}
        alive = self.people.alive_persons()
        alive_ids = [p.id for p in alive]
        centralities = self.social_graph.calculate_deference_centrality(alive_ids)

        for p in alive:
            clan = self.society.get_person_clan(p.id)
            clan_name = clan.name if clan else None
            age = self.people.age_years(p, self.tick)
            cent = centralities.get(p.id, 20.0)
            title, role = self.social_graph.deduce_emergent_title(
                p.id, age, cent, bool(p.spouse_ids), len(p.children_ids), clan_name
            )
            prof = NotableProfile(p.id, title=title, rank_grade=role, influence=round(cent))
            if clan:
                prof.beliefs.append(f"Totem sacré du clan : {clan.totem}")
                prof.beliefs.append(f"Mythe fondateur : {clan.cosmogony}")
            notables[p.id] = prof
            p.notable = True
        return notables

    def refresh_notables_hierarchy(self):
        """Met à jour dynamiquement la hiérarchie sociale et les statuts des notables de manière purement émergente.

        Conforme à la Priorité 1 du plan d'émergence :
        - Aucun grade fixe (ex: Patriarche 100, Souverain 95).
        - Le rang est déduit de la sociométrie réelle (centralité de déférence, médiations, citations mémorielles).
        - Les qualificatifs sociaux sont dérivés des faits observés.
        """
        alive = self.people.alive_persons()
        if not alive:
            return

        alive_ids = [p.id for p in alive]
        centralities = self.social_graph.calculate_deference_centrality(alive_ids)

        for p in alive:
            age = self.people.age_years(p, self.tick)
            cent = centralities.get(p.id, 20.0)
            clan = self.society.get_person_clan(p.id)
            clan_name = clan.name if clan else None

            # Un individu est notable si ses pairs s'en remettent à lui (haute centralité),
            # s'il est aîné respecté, chef reconnu par le clan, ou au début quand la communauté est réduite.
            is_emergent_notable = (
                cent >= 35.0
                or len(alive) <= 5
                or (clan and p.id in (clan.leader_id, clan.matriarch_id))
                or age >= 40.0
            )

            if is_emergent_notable or p.notable:
                p.notable = True
                prof = self.notables.setdefault(p.id, NotableProfile(p.id))
                title, role = self.social_graph.deduce_emergent_title(
                    p.id, age, cent, bool(p.spouse_ids), len(p.children_ids), clan_name
                )
                prof.title = title
                prof.rank_grade = role
                prof.influence = round(cent)

                if p.id not in self.agent_cognitions:
                    self.agent_cognitions[p.id] = AgentCognition.create_random(p.id, seed=self.seed + p.id)

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
                season_str = SEASONS_N[d.day_of_year // q]
                out.append(Event(self.tick, "season_start", {"season": season_str, "year": d.year}))
                self._record_seasonal_metrics(season_str, d.year)
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

    def _record_seasonal_metrics(self, season_name: str, year: int):
        """Enregistre un instantané scientifique des dynamiques émergentes à chaque saison."""
        alive = self.people.alive_persons()
        pop = len(alive)
        if pop == 0:
            return

        alive_ids = [p.id for p in alive]
        centralities = self.social_graph.calculate_deference_centrality(alive_ids)

        inf_values = [centralities.get(pid, 0.0) for pid in alive_ids]
        gini_inf = calculate_gini(inf_values)

        food_per_person = []
        for p in alive:
            y, x = p.cell
            f = float(self.eco.feff[p.species_id, y, x]) if p.species_id < len(self.eco.feff) else 1.0
            food_per_person.append(f)
        gini_res = calculate_gini(food_per_person)

        activity_counts = {"cueillette": 0, "chasse": 0, "conseil": 0, "soin": 0}
        for p in alive:
            c = centralities.get(p.id, 20.0)
            if c >= 45.0:
                activity_counts["conseil"] += 1
            elif p.sex == "M":
                activity_counts["chasse"] += 1
            else:
                activity_counts["cueillette"] += 1
        behav_entropy = calculate_shannon_entropy(activity_counts)

        n_edges = sum(len(sources) for sources in self.social_graph.deference_edges.values())
        max_possible_edges = max(1, pop * (pop - 1))
        density = round(min(1.0, n_edges / max_possible_edges), 4)

        recent_deaths = [p for p in self.people.persons.values() if p.death_tick and p.death_tick > self.tick - 365]
        infant_deaths = [p for p in recent_deaths if self.people.age_years(p, p.death_tick) < 5.0]
        infant_mort_rate = round(len(infant_deaths) / max(1, len(recent_deaths)), 3) if recent_deaths else 0.05

        snap = SeasonalMetricsSnapshot(
            tick=self.tick,
            year=year,
            season=season_name,
            population=pop,
            births_this_year=len([p for p in self.people.persons.values() if p.birth_tick > self.tick - 365]),
            deaths_this_year=len(recent_deaths),
            infant_mortality_rate=infant_mort_rate,
            gini_resources=gini_res,
            gini_influence=gini_inf,
            behavioral_entropy=behav_entropy,
            network_density=density,
            avg_deference=round(sum(inf_values) / max(1, len(inf_values)), 1),
            max_deference=round(max(inf_values) if inf_values else 0.0, 1),
            active_social_ties=n_edges,
            active_taboos_count=sum(len(c.taboos) for c in self.society.clans.values()),
            active_customs_count=len(self.justice.legal_codes),
            beliefs_count=sum(len(prof.beliefs) for prof in self.notables.values()),
        )
        self.metrics_history.record_snapshot(snap)

    def _update_notables_memory(self, events: list[Event], year: int):
        for ev in events:
            if ev.type == "birth":
                m_id = ev.payload.get("mother_id")
                f_id = ev.payload.get("father_id")
                name = ev.payload.get("name")
                for parent in (m_id, f_id):
                    if parent in self.notables:
                        self.notables[parent].add_memory(self.tick, year, f"Naissance de mon enfant {name}", impact=0.8)
                    if parent in self.agent_cognitions:
                        self.agent_cognitions[parent].add_memory(self.tick, year, f"Naissance de mon enfant {name}", importance=0.8)
                if m_id and f_id:
                    self.social_graph.record_interaction(self.tick, year, m_id, f_id, "mention", 1.0)
                    self.social_graph.record_interaction(self.tick, year, f_id, m_id, "mention", 1.0)
            elif ev.type == "marriage":
                hid = ev.payload.get("husband_id")
                wid = ev.payload.get("wife_id")
                hname = ev.payload.get("husband")
                wname = ev.payload.get("wife")
                if hid in self.notables:
                    self.notables[hid].add_memory(self.tick, year, f"Mon union sacrée avec {wname}", impact=0.7)
                if wid in self.notables:
                    self.notables[wid].add_memory(self.tick, year, f"Mon union sacrée avec {hname}", impact=0.7)
                for pid, partner_name in [(hid, wname), (wid, hname)]:
                    if pid in self.agent_cognitions:
                        self.agent_cognitions[pid].add_memory(self.tick, year, f"Mon union avec {partner_name}", importance=0.7)
                if hid and wid:
                    self.social_graph.record_interaction(self.tick, year, hid, wid, "deference", 1.0)
                    self.social_graph.record_interaction(self.tick, year, wid, hid, "deference", 1.0)
            elif ev.type == "death":
                pid = ev.payload.get("person_id")
                name = ev.payload.get("name")
                cause = ev.payload.get("cause")
                if pid in self.notables:
                    self.notables[pid].add_memory(self.tick, year, f"Dernier soupir emporté par {cause}", impact=1.0)
                for not_id, profile in self.notables.items():
                    if not_id != pid and self.people.are_kin(not_id, pid, 1):
                        profile.add_memory(self.tick, year, f"Deuil tragique de {name} ({cause})", impact=0.75)
                        if not_id in self.agent_cognitions:
                            self.agent_cognitions[not_id].add_memory(self.tick, year, f"Deuil tragique de {name} ({cause})", importance=0.75)
                        self.social_graph.record_interaction(self.tick, year, not_id, pid, "mention", 1.0)
            elif ev.type == "clan_leadership":
                new_leader_id = ev.payload.get("new_leader_id")
                clan_name = ev.payload.get("clan_name")
                clan_id = ev.payload.get("clan_id")
                if new_leader_id and new_leader_id not in self.notables and new_leader_id in self.people.persons:
                    p = self.people.persons[new_leader_id]
                    p.notable = True
                    clan = self.society.get_person_clan(new_leader_id)
                    title, role = self.social_graph.deduce_emergent_title(
                        p.id, self.people.age_years(p, self.tick), 60.0, bool(p.spouse_ids), len(p.children_ids), clan_name
                    )
                    prof = NotableProfile(p.id, title=title, rank_grade=role)
                    if clan:
                        prof.beliefs.append(f"Totem sacré : {clan.totem}")
                        prof.beliefs.append(f"Mythe fondateur : {clan.cosmogony}")
                    self.notables[new_leader_id] = prof
                if new_leader_id in self.notables:
                    self.notables[new_leader_id].add_memory(self.tick, year, f"Reconnu comme guide du clan ({clan_name})", impact=0.9)
                if new_leader_id in self.agent_cognitions:
                    self.agent_cognitions[new_leader_id].add_memory(self.tick, year, f"Reconnu comme guide du clan ({clan_name})", importance=0.9)
                clan_obj = self.society.clans.get(clan_id)
                if clan_obj and new_leader_id:
                    for mid in clan_obj.member_ids:
                        if mid != new_leader_id:
                            self.social_graph.record_interaction(self.tick, year, mid, new_leader_id, "deference", 1.5)
            elif ev.type == "cultural_drift":
                clan_id = ev.payload.get("clan_id")
                taboo = ev.payload.get("taboo_adopted")
                clan = self.society.clans.get(clan_id)
                if clan:
                    for mid in clan.member_ids:
                        if mid in self.notables:
                            self.notables[mid].add_memory(self.tick, year, f"Notre clan a adopté un nouvel interdit sacré : « {taboo} »", impact=0.6)
                        if mid in self.agent_cognitions:
                            self.agent_cognitions[mid].add_memory(self.tick, year, f"Coutume adoptée : {taboo}", importance=0.6)
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
                            ltitle, lrole = self.social_graph.deduce_emergent_title(
                                lp.id, self.people.age_years(lp, self.tick), 50.0, bool(lp.spouse_ids), len(lp.children_ids), new_clan_name
                            )
                            nprof = NotableProfile(lp.id, title=ltitle, rank_grade=lrole)
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
                judge_id = ev.payload.get("judge_id")
                verdict = ev.payload.get("verdict")
                punishment = ev.payload.get("punishment")
                if accused_id in self.notables:
                    self.notables[accused_id].add_memory(self.tick, year, f"J'ai été jugé par les anciens ({verdict}) : {punishment}", impact=0.9)
                if judge_id and accused_id:
                    self.social_graph.record_interaction(self.tick, year, accused_id, judge_id, "mediation", 2.0)

        # Déclenchement périodique de la réflexion cognitive (Generative Agents Park et al. 2023)
        if self.tick % 60 == 0:
            for cog in self.agent_cognitions.values():
                cog.trigger_reflection_if_needed(self.tick)

    def drain_events(self) -> list[Event]:
        ev, self.pending_events = self.pending_events, []
        return ev

    # --- sérialisation (M05) -------------------------------------------------
    def snapshot(self) -> bytes:
        buf = io.BytesIO()
        meta = {
            "id": self.id, "seed": self.seed, "consts": self.consts.to_dict(),
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
            "ai_budget": self.ai_budget.to_dict(),
            "social_graph": self.social_graph.to_dict(),
            "agent_cognitions": {str(k): v.to_dict() for k, v in self.agent_cognitions.items()},
            "metrics_history": self.metrics_history.to_dict(),
            "ai_logger": self.ai_logger.to_dict(),
            "branch_metadata": self.branch_metadata.to_dict(),
        }
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
        social_graph = SocialGraph.from_dict(meta["social_graph"]) if "social_graph" in meta else None
        agent_cognitions = {int(k): AgentCognition.from_dict(v) for k, v in meta.get("agent_cognitions", {}).items()} if "agent_cognitions" in meta else None
        metrics_history = SimulationMetricsHistory.from_dict(meta["metrics_history"]) if "metrics_history" in meta else None
        ai_logger = AICallLogger.from_dict(meta["ai_logger"]) if "ai_logger" in meta else None
        branch_metadata = BranchMetadata.from_dict(meta["branch_metadata"]) if "branch_metadata" in meta else None

        return cls(meta["id"], meta["seed"], UniverseConstants.from_dict(meta["consts"]),
                   meta["start_year"], meta["parent_id"], world, meta["tick"], eco, people, society,
                   languages, technology, warfare, chronicles, disasters, religion, settlements,
                   justice, trade, economy, realms, erudition, ouroboros, notables, ai_budget,
                   social_graph=social_graph, agent_cognitions=agent_cognitions,
                   metrics_history=metrics_history, ai_logger=ai_logger, branch_metadata=branch_metadata)

    def ask_notable(self, person_id: int, question: str, llm_client: LLMClient | None = None) -> str:
        """Interroge un individu notable sous immersion totale en respectant l'autonomie cognitive émergente."""
        from .immersion import NotableAgent
        from .llm import MockLLMClient

        if not self.ai_budget.can_call(self.tick):
            return "L'esprit de cet habitant est plongé dans un profond sommeil ou ses devoirs quotidiens l'accaparent."

        self.refresh_notables_hierarchy()

        if person_id not in self.notables:
            if person_id in self.people.persons:
                p = self.people.persons[person_id]
                p.notable = True
                clan = self.society.get_person_clan(person_id)
                clan_name = clan.name if clan else None
                age = self.people.age_years(p, self.tick)
                title, role = self.social_graph.deduce_emergent_title(
                    p.id, age, 20.0, bool(p.spouse_ids), len(p.children_ids), clan_name
                )
                self.notables[person_id] = NotableProfile(person_id, title=title, rank_grade=role)
            else:
                return "Cet individu n'existe pas ou a disparu des mémoires."

        prof = self.notables[person_id]
        p = self.people.persons[person_id]
        client = llm_client or MockLLMClient()
        agent = NotableAgent(person_id, prof, client)
        response = agent.ponder(question, self)

        # Toute intervention observatrice marque la branche comme intervention expérimentale
        self.branch_metadata.branch_type = "observer_intervention"

        # Traitement cognitif autonome (PIMMUR #4 & #5 : délibération interne, pas d'injection aveugle)
        cognition = self.agent_cognitions.setdefault(
            person_id,
            AgentCognition.create_random(person_id, seed=self.seed + person_id)
        )
        decision_info = cognition.decide_on_proposal(question, self.tick)

        # Enregistrement dans les souvenirs (comme une perception externe ou un songe marquant)
        mem_text = f"Perception d'une présence venue d'au-delà : « {question[:50]} »"
        prof.add_memory(self.tick, self.date.year, mem_text, impact=0.8)
        cognition.add_memory(self.tick, self.date.year, mem_text, importance=0.8)

        # Si l'habitant a évalué une suggestion ou un interdit
        if decision_info.get("proposal_detected"):
            prop_text = decision_info.get("proposal_text", "")
            decision = decision_info.get("decision")
            if decision == "accept":
                belief_text = f"Parole reçue d'une voix mystérieuse : {prop_text}"
                if belief_text not in prof.beliefs:
                    prof.beliefs.append(belief_text)
                cognition.known_facts.add(f"Croît en : {prop_text}")
            elif decision == "doubt":
                prof.add_memory(self.tick, self.date.year, f"Doute face à une injonction mystérieuse : « {prop_text} »", impact=0.6)
            elif decision == "reject":
                prof.add_memory(self.tick, self.date.year, f"A repoussé une parole étrangère contraire aux coutumes : « {prop_text} »", impact=0.5)

        # Enregistrer l'interaction dans le graphe social
        self.social_graph.record_interaction(self.tick, self.date.year, person_id, person_id, "mention", 0.5)

        clan = self.society.get_person_clan(p.id)
        self.chronicles.record(
            tick=self.tick,
            year=self.date.year,
            category="communion",
            title=f"Communion du Voyageur avec {p.name}",
            narrative=f"Une présence mystérieuse s'est entretenue avec {p.name} ({prof.title}), marquant son esprit.",
            clans=[clan.name] if clan else [],
        )

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
            "branch_metadata": self.branch_metadata.to_dict(),
            "metrics_summary": self.metrics_history.get_summary(),
            "ai_calls_count": self.ai_logger.counter,
        }
