"""Coalitions politiques émergentes — sans titre « Royaume » / « Souverain » imposé.

Le moteur enregistre seulement qu'un campement étendu rassemble d'autres groupes.
Les habitants (ou l'analyse) nomment ces structures ; le code n'impose aucun grade.
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
    """Coalition politique (nom historique conservé pour snapshots)."""
    id: int
    name: str
    capital_clan_id: int
    ruler_id: int
    vassal_clan_ids: list[int] = field(default_factory=list)
    founded_year: int = 0
    tribute_rate: float = 0.15

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Kingdom:
        return cls(**d)


class RealmManager:
    """Enregistre les coalitions sans inventer de titres royaux."""

    def __init__(self):
        self.kingdoms: dict[int, Kingdom] = {}
        self.next_kingdom_id = 1

    def step(self, tick: int, year: int, society: Society, people: People, rng: Rng) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("realms", tick)

        clans = list(society.clans.values())
        if len(clans) < 2:
            return events

        clans_in_coalition = set()
        for k in self.kingdoms.values():
            clans_in_coalition.add(k.capital_clan_id)
            clans_in_coalition.update(k.vassal_clan_ids)

        # Coalitions uniquement si plusieurs camps existent et qu'un lien social dense apparaît
        for c in clans:
            if c.id not in clans_in_coalition and len(c.member_ids) >= 12 and g.random() < 0.15:
                ruler_id = c.leader_id or (c.member_ids[0] if c.member_ids else 1)
                # Nom descriptif neutre — pas « Royaume de … »
                k_name = f"Coalition autour de {c.name}"
                kingdom = Kingdom(
                    id=self.next_kingdom_id,
                    name=k_name,
                    capital_clan_id=c.id,
                    ruler_id=ruler_id,
                    founded_year=year,
                )
                self.kingdoms[kingdom.id] = kingdom
                self.next_kingdom_id += 1
                clans_in_coalition.add(c.id)

                events.append(Event(tick, "coalition_formed", {
                    "coalition_id": kingdom.id,
                    "coalition_name": kingdom.name,
                    "capital_clan_id": c.id,
                    "focal_person_id": ruler_id,
                    "year": year,
                }))
                # Compat événements anciens
                events.append(Event(tick, "kingdom_founded", {
                    "kingdom_id": kingdom.id,
                    "kingdom_name": kingdom.name,
                    "capital_clan_id": c.id,
                    "ruler_id": ruler_id,
                    "year": year,
                }))

        for kingdom in self.kingdoms.values():
            for c in clans:
                if c.id not in clans_in_coalition and g.random() < 0.12:
                    kingdom.vassal_clan_ids.append(c.id)
                    clans_in_coalition.add(c.id)
                    events.append(Event(tick, "camp_joined_coalition", {
                        "coalition_id": kingdom.id,
                        "coalition_name": kingdom.name,
                        "clan_id": c.id,
                        "clan_name": c.name,
                        "year": year,
                    }))
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
