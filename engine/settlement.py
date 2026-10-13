"""M19 - Sédentarisation, Villages Fortifiés & Urbanisme Naissant.

Ce module gère l'évolution de l'habitat humain :
- Transition du campement nomade vers le hameau sédentaire, le village palissadé et le bourg fortifié
- Construction d'infrastructures défensives (palissades de pieux, fossés) et de stockage (greniers)
- Réduction des pertes en cas de raid ennemi grâce aux fortifications
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


TIER_NAMES = {
    1: "Campement de Chasse",
    2: "Hameau Permanent",
    3: "Village Palissadé",
    4: "Bourg Fortifié",
}


@dataclass
class Settlement:
    id: int
    name: str
    cell: tuple[int, int]
    clan_id: int
    tier: int = 1
    buildings: list[str] = field(default_factory=list)
    food_stores: float = 100.0
    defense_bonus: float = 0.0

    @property
    def tier_title(self) -> str:
        return TIER_NAMES.get(self.tier, "Campement")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cell"] = list(self.cell)
        d["tier_title"] = self.tier_title
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Settlement:
        d = dict(d)
        d["cell"] = tuple(d["cell"])
        d.pop("tier_title", None)
        return cls(**d)


class SettlementManager:
    """Gestionnaire de l'urbanisme et des infrastructures des clans."""

    def __init__(self):
        self.settlements: dict[int, Settlement] = {}
        self.next_settlement_id = 1

    @classmethod
    def genesis(cls, society: Society) -> SettlementManager:
        mgr = cls()
        for clan in society.clans.values():
            st = Settlement(
                id=mgr.next_settlement_id,
                name=clan.settlement_name,
                cell=clan.settlement_cell,
                clan_id=clan.id,
                tier=1,
                buildings=["Foyers collectifs", "Abris de peaux"],
            )
            mgr.settlements[st.id] = st
            mgr.next_settlement_id += 1
        return mgr

    def step(self, tick: int, year: int, society: Society, people: People,
             technology: TechnologyRegistry, rng: Rng) -> list[Event]:
        """Évolution annuelle des infrastructures selon l'essor démographique."""
        events: list[Event] = []
        g = rng.gen("settlement", tick)

        for s in self.settlements.values():
            clan = society.clans.get(s.clan_id)
            if not clan:
                continue

            pop = clan.population_size
            tech_state = technology.get_or_create(clan.id)

            # Évolution vers Tier 2 (Hameau) : pop >= 6
            if s.tier == 1 and pop >= 6:
                s.tier = 2
                s.buildings.append("Grenier sur pilotis")
                events.append(Event(tick, "settlement_upgraded", {
                    "settlement_id": s.id,
                    "name": s.name,
                    "clan_id": s.clan_id,
                    "new_tier": s.tier,
                    "tier_name": s.tier_title,
                    "year": year,
                }))

            # Évolution vers Tier 3 (Village Palissadé) : pop >= 12
            elif s.tier == 2 and pop >= 12 and g.random() < 0.35:
                s.tier = 3
                s.defense_bonus = 0.35
                s.buildings.append("Palissade de pieux")
                s.buildings.append("Fossé d'enceinte")
                events.append(Event(tick, "settlement_upgraded", {
                    "settlement_id": s.id,
                    "name": s.name,
                    "clan_id": s.clan_id,
                    "new_tier": s.tier,
                    "tier_name": s.tier_title,
                    "year": year,
                }))

            # Évolution vers Tier 4 (Bourg Fortifié) : pop >= 20
            elif s.tier == 3 and pop >= 20 and tech_state.has("early_horticulture"):
                s.tier = 4
                s.defense_bonus = 0.65
                s.buildings.append("Tour de guet en rondins")
                s.buildings.append("Rempart renforcé")
                events.append(Event(tick, "settlement_upgraded", {
                    "settlement_id": s.id,
                    "name": s.name,
                    "clan_id": s.clan_id,
                    "new_tier": s.tier,
                    "tier_name": s.tier_title,
                    "year": year,
                }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "settlements": [s.to_dict() for s in self.settlements.values()],
            "next_settlement_id": self.next_settlement_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SettlementManager:
        mgr = cls()
        mgr.next_settlement_id = d.get("next_settlement_id", 1)
        mgr.settlements = {x["id"]: Settlement.from_dict(x) for x in d.get("settlements", [])}
        return mgr
