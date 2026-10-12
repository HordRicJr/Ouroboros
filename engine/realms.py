"""M23 - Royaumes, Confédérations, Alliances Politiques & Tributs Vassaux.

Ce module modélise la centralisation politique impériale :
- Fédérations de clans en Royaumes / Principautés
- Couronnement d'un Haut-Roi / Souverain
- Soumission vassalique et paiement de tributs annuels
- Révoltes de vassaux opprimés
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .people import People
    from .rng import Rng
    from .society import Society


@dataclass
class Kingdom:
    id: int
    name: str
    capital_clan_id: int
    ruler_id: int
    vassal_clan_ids: list[int] = field(default_factory=list)
    founded_year: int = 0
    tribute_rate: float = 0.15  # 15% de tribut prélevé sur les vassaux

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Kingdom:
        return cls(**d)


class RealmManager:
    """Gestionnaire des royaumes, vassaux et confédérations suprêmes."""

    def __init__(self):
        self.kingdoms: dict[int, Kingdom] = {}
        self.next_kingdom_id = 1

    def step(self, tick: int, year: int, society: Society, people: People, rng: Rng) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("realms", tick)

        clans = list(society.clans.values())
        if len(clans) < 2:
            return events

        # 1. Émergence d'un royaume si un clan devient très populeux ou dominant
        clans_in_kingdoms = set()
        for k in self.kingdoms.values():
            clans_in_kingdoms.add(k.capital_clan_id)
            clans_in_kingdoms.update(k.vassal_clan_ids)

        for c in clans:
            if c.id not in clans_in_kingdoms and len(c.member_ids) >= 12 and g.random() < 0.25:
                # Création du royaume
                ruler_id = c.leader_id or (c.member_ids[0] if c.member_ids else 1)
                k_name = f"Royaume de {c.name}"
                kingdom = Kingdom(
                    id=self.next_kingdom_id,
                    name=k_name,
                    capital_clan_id=c.id,
                    ruler_id=ruler_id,
                    founded_year=year,
                )
                self.kingdoms[kingdom.id] = kingdom
                self.next_kingdom_id += 1
                clans_in_kingdoms.add(c.id)

                events.append(Event(tick, "kingdom_founded", {
                    "kingdom_id": kingdom.id,
                    "kingdom_name": kingdom.name,
                    "capital_clan_id": c.id,
                    "ruler_id": ruler_id,
                    "year": year,
                }))

        # 2. Vassalisation diplomatique ou par contrainte
        for kingdom in self.kingdoms.values():
            for c in clans:
                if c.id not in clans_in_kingdoms and g.random() < 0.20:
                    kingdom.vassal_clan_ids.append(c.id)
                    clans_in_kingdoms.add(c.id)
                    events.append(Event(tick, "vassal_pledged", {
                        "kingdom_id": kingdom.id,
                        "kingdom_name": kingdom.name,
                        "vassal_clan_id": c.id,
                        "vassal_clan_name": c.name,
                        "year": year,
                    }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "kingdoms": [k.to_dict() for k in self.kingdoms.values()],
            "next_kingdom_id": self.next_kingdom_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RealmManager:
        rm = cls()
        rm.next_kingdom_id = d.get("next_kingdom_id", 1)
        rm.kingdoms = {k["id"]: Kingdom.from_dict(k) for k in d.get("kingdoms", [])}
        return rm
