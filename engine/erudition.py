"""M24 - Érudition, Grandes Merveilles & Âge d'Or.

Ce module modélise l'éclosion intellectuelle et architecturale des civilisations :
- Érection de Merveilles du Monde (Ziggourat du Soleil, Grande Nécropole, Observatoire Céleste)
- Bibliothèques de tablettes d'argile et transmission des savoirs ancestraux
- Âge d'Or civilisationnel conférant des bonus de cohésion et d'apprentissage
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .rng import Rng
    from .society import Society

WONDER_TYPES = [
    ("Ziggourat du Soleil d'Or", "Élévation pyramidale dédiée aux dieux du ciel et de la lumière"),
    ("Grande Nécropole des Rois", "Tombeaux sculptés dans la falaise perpétuant la mémoire dynastique"),
    ("Observatoire des Équinoxes", "Cercle de colonnes mégalithiques prédisant les solstices et éclipses"),
    ("Bibliothèque des Tablettes de Terre", "Archives d'argile consignant lois, généalogies et chants épiques"),
]


@dataclass
class Wonder:
    id: int
    name: str
    description: str
    built_by_clan_id: int
    completion_year: int
    cultural_prestige: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Wonder:
        return cls(**d)


class EruditionManager:
    """Gestionnaire des merveilles, académies d'anciens et âges d'or."""

    def __init__(self):
        self.wonders: dict[int, Wonder] = {}
        self.golden_ages: dict[int, int] = {}  # clan_id -> golden_age_end_year
        self.next_wonder_id = 1

    def step(self, tick: int, year: int, society: Society, rng: Rng) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("erudition", tick)

        for clan_id, clan in society.clans.items():
            # 1. Construction d'une grande merveille (rare : 10% par clan de plus de 10 membres)
            if len(self.wonders) < 8 and len(clan.member_ids) >= 10 and g.random() < 0.10:
                w_type_idx = int(g.integers(0, len(WONDER_TYPES)))
                w_name, w_desc = WONDER_TYPES[w_type_idx]
                wonder_full_name = f"{w_name} de {clan.name}"

                wonder = Wonder(
                    id=self.next_wonder_id,
                    name=wonder_full_name,
                    description=w_desc,
                    built_by_clan_id=clan_id,
                    completion_year=year,
                    cultural_prestige=float(g.uniform(80.0, 150.0)),
                )
                self.wonders[wonder.id] = wonder
                self.next_wonder_id += 1

                # Déclenche un Âge d'Or pour 5 ans
                self.golden_ages[clan_id] = year + 5

                events.append(Event(tick, "wonder_completed", {
                    "wonder_id": wonder.id,
                    "wonder_name": wonder.name,
                    "clan_id": clan_id,
                    "clan_name": clan.name,
                    "prestige": wonder.cultural_prestige,
                    "year": year,
                }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "wonders": [w.to_dict() for w in self.wonders.values()],
            "golden_ages": {str(k): v for k, v in self.golden_ages.items()},
            "next_wonder_id": self.next_wonder_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EruditionManager:
        em = cls()
        em.next_wonder_id = d.get("next_wonder_id", 1)
        em.wonders = {w["id"]: Wonder.from_dict(w) for w in d.get("wonders", [])}
        em.golden_ages = {int(k): v for k, v in d.get("golden_ages", {}).items()}
        return em
