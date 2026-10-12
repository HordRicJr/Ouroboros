"""M14 - Guerres, Raids, Traités de Paix & Frontières Politiques.

Ce module modélise les dynamiques conflictuelles et la diplomatie formelle :
- Raids et escarmouches de pillage (lorsque relations < -0.4)
- Guerres de conquête territoriale pour les terres fertiles ou les ressources
- Résolution des combats tactiques basée sur la démographie, les armes et le moral
- Traités de paix, tributs et trêves négociées
- Délimitation de frontières politiques et zones tampons
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .people import People
    from .rng import Rng
    from .society import Society
    from .technology import TechnologyRegistry
    from .worldmap import WorldMap


@dataclass
class WarState:
    id: int
    attacker_clan_id: int
    defender_clan_id: int
    start_tick: int
    start_year: int
    reason: str
    active: bool = True
    skirmishes_count: int = 0
    casualties_attacker: int = 0
    casualties_defender: int = 0
    captured_territory: list[tuple[int, int]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["captured_territory"] = [list(c) for c in self.captured_territory]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WarState:
        d = dict(d)
        d["captured_territory"] = [tuple(c) for c in d.get("captured_territory", [])]
        return cls(**d)


class WarfareManager:
    """Gestionnaire des guerres, des raids et des traités de paix."""

    def __init__(self):
        self.wars: dict[int, WarState] = {}
        self.next_war_id = 1
        self.peace_treaties: list[dict[str, Any]] = []

    def active_wars(self) -> list[WarState]:
        return [w for w in self.wars.values() if w.active]

    def is_at_war(self, clan_id_1: int, clan_id_2: int) -> WarState | None:
        for w in self.wars.values():
            if not w.active:
                continue
            if (w.attacker_clan_id == clan_id_1 and w.defender_clan_id == clan_id_2) or \
               (w.attacker_clan_id == clan_id_2 and w.defender_clan_id == clan_id_1):
                return w
        return None

    def declare_war(self, c1_id: int, c2_id: int, tick: int, year: int, reason: str) -> WarState:
        war = WarState(
            id=self.next_war_id,
            attacker_clan_id=c1_id,
            defender_clan_id=c2_id,
            start_tick=tick,
            start_year=year,
            reason=reason,
        )
        self.wars[war.id] = war
        self.next_war_id += 1
        return war

    def step(self, tick: int, year: int, society: Society, people: People,
             technology: TechnologyRegistry, world: WorldMap, rng: Rng) -> list[Event]:
        """Évolution annuelle des conflits et de la diplomatie martiale."""
        events: list[Event] = []
        g = rng.gen("warfare", tick)

        # 1. Éclatement de nouveaux conflits si hostilité extrême
        clan_ids = [cid for cid, c in society.clans.items() if c.member_ids]
        for i in range(len(clan_ids)):
            c1 = society.clans[clan_ids[i]]
            for j in range(i + 1, len(clan_ids)):
                c2 = society.clans[clan_ids[j]]
                rel = c1.relations.get(c2.id, 0.0)

                # Si hostilité inférieure à -0.55 et pas déjà en guerre
                if rel < -0.55 and self.is_at_war(c1.id, c2.id) is None and g.random() < 0.35:
                    war = self.declare_war(c1.id, c2.id, tick, year, "Rivalité territoriale et pillage des récoltes")
                    events.append(Event(tick, "war_declared", {
                        "war_id": war.id,
                        "attacker_clan_id": c1.id,
                        "attacker_clan_name": c1.name,
                        "defender_clan_id": c2.id,
                        "defender_clan_name": c2.name,
                        "year": year,
                        "reason": war.reason,
                    }))

        # 2. Résolution des batailles et escarmouches pour chaque guerre active
        for war in self.active_wars():
            c_att = society.clans.get(war.attacker_clan_id)
            c_def = society.clans.get(war.defender_clan_id)

            if not c_att or not c_def or not c_att.member_ids or not c_def.member_ids:
                # Clan anéanti ou disparu : fin de guerre automatique
                war.active = False
                continue

            war.skirmishes_count += 1

            # Calcul de la puissance de combat
            # Effectifs de guerriers (adultes 16-50 ans)
            att_warriors = [pid for pid in c_att.member_ids if pid in people.persons and 16 <= people.age_years(people.persons[pid], tick) <= 50]
            def_warriors = [pid for pid in c_def.member_ids if pid in people.persons and 16 <= people.age_years(people.persons[pid], tick) <= 50]

            att_tech = technology.get_or_create(c_att.id)
            def_tech = technology.get_or_create(c_def.id)

            # Bonus d'armes (arc et flèches = +40% force, taille du silex = +10%)
            att_mult = 1.0 + (0.4 if att_tech.has("bow_and_arrow") else 0.0) + (0.1 if att_tech.has("flint_knapping") else 0.0)
            def_mult = 1.0 + (0.4 if def_tech.has("bow_and_arrow") else 0.0) + (0.1 if def_tech.has("flint_knapping") else 0.0)

            att_power = (len(att_warriors) + 1) * att_mult * float(g.uniform(0.7, 1.3))
            def_power = (len(def_warriors) + 1) * def_mult * float(g.uniform(0.7, 1.3))

            # Résolution de l'affrontement
            winner, loser = (c_att, c_def) if att_power >= def_power else (c_def, c_att)
            loser_warriors = def_warriors if winner == c_att else att_warriors

            # Pertes humaines limitées mais réelles
            casualty_loser = None
            if loser_warriors and g.random() < 0.60:
                victim_id = int(g.choice(loser_warriors))
                victim = people.persons.get(victim_id)
                if victim and victim.alive:
                    victim.death_tick = tick
                    victim.cause_of_death = f"tué au combat contre le {winner.name}"
                    casualty_loser = victim.name
                    if loser == c_att:
                        war.casualties_attacker += 1
                    else:
                        war.casualties_defender += 1

            # Transfert d'une case de territoire si victoire nette
            conquest_cell = None
            if loser.territory_cells and len(loser.territory_cells) > 1 and g.random() < 0.40:
                stolen_cell = loser.territory_cells.pop()
                if stolen_cell != loser.settlement_cell and stolen_cell not in winner.territory_cells:
                    winner.territory_cells.append(stolen_cell)
                    conquest_cell = stolen_cell
                    war.captured_territory.append(stolen_cell)

            events.append(Event(tick, "skirmish_result", {
                "war_id": war.id,
                "winner_clan_id": winner.id,
                "winner_clan_name": winner.name,
                "loser_clan_id": loser.id,
                "loser_clan_name": loser.name,
                "casualty": casualty_loser,
                "conquest_cell": list(conquest_cell) if conquest_cell else None,
                "year": year,
            }))

            # 3. Négociation de paix (épuisement ou après 2-3 escarmouches)
            if war.skirmishes_count >= 2 and g.random() < 0.50:
                war.active = False
                c_att.relations[c_def.id] = -0.15  # Paix précaire rétablie
                c_def.relations[c_att.id] = -0.15
                treaty = {
                    "war_id": war.id,
                    "clan1_id": c_att.id,
                    "clan1_name": c_att.name,
                    "clan2_id": c_def.id,
                    "clan2_name": c_def.name,
                    "year": year,
                    "total_casualties": war.casualties_attacker + war.casualties_defender,
                    "terms": "Cessation des hostilités et reconnaissance des territoires actuels",
                }
                self.peace_treaties.append(treaty)
                events.append(Event(tick, "peace_treaty", treaty))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "wars": [w.to_dict() for w in self.wars.values()],
            "next_war_id": self.next_war_id,
            "peace_treaties": self.peace_treaties,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WarfareManager:
        mgr = cls()
        mgr.next_war_id = d.get("next_war_id", 1)
        mgr.wars = {w["id"]: WarState.from_dict(w) for w in d.get("wars", [])}
        mgr.peace_treaties = d.get("peace_treaties", [])
        return mgr
