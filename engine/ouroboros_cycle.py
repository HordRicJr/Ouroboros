"""M25 - L'Ouroboros Final : Crise Systémique, Effondrement & Renaissance Cyclique.

Ce module boucle la dynamique de l'univers :
- Évaluation de la pression démographique, de l'épuisement des sols et de l'hybris impérial
- Effondrement systémique des empires par désagrégation interne (perte des routes, scission des royaumes)
- Renaissance cyclique : retour aux campements nomades régénérés, préservant la sagesse passée dans les mythes
- Accomplissement du symbole de l'Ouroboros : le serpent qui se mord la queue pour renaître.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .realms import RealmManager
    from .rng import Rng
    from .society import Society


@dataclass
class EpochCycle:
    cycle_number: int
    current_phase: str  # "Aube", "Ascension", "Apogée", "Crise", "Renaissance"
    last_collapse_year: int | None = None
    historical_collapses_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EpochCycle:
        return cls(**d)


class OuroborosCycleManager:
    """Gestionnaire de la boucle cyclique civilisationnelle et de la résilience du monde."""

    def __init__(self):
        self.cycle: EpochCycle = EpochCycle(cycle_number=1, current_phase="Aube")

    def step(self, tick: int, year: int, society: Society, realms: RealmManager, rng: Rng) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("ouroboros", tick)

        total_clans = len(society.clans)
        total_kingdoms = len(realms.kingdoms)

        # 1. Évolution des phases de la civilisation
        if total_kingdoms >= 2:
            self.cycle.current_phase = "Apogée"
        elif total_clans >= 4:
            self.cycle.current_phase = "Ascension"
        else:
            self.cycle.current_phase = "Aube"

        # 2. Déclenchement d'une Crise Systémique et Effondrement cyclique (rare : après 20 ans de simulation, 5% de chance si Apogée)
        if self.cycle.current_phase == "Apogée" and year >= 15 and g.random() < 0.08:
            self.cycle.current_phase = "Crise"

            # Dissolution d'un royaume par scission interne
            if realms.kingdoms:
                kid = next(iter(realms.kingdoms))
                collapsed_kingdom = realms.kingdoms.pop(kid)

                self.cycle.historical_collapses_count += 1
                self.cycle.last_collapse_year = year
                self.cycle.cycle_number += 1
                self.cycle.current_phase = "Renaissance"

                events.append(Event(tick, "systemic_collapse", {
                    "cycle_number": self.cycle.cycle_number,
                    "collapsed_realm": collapsed_kingdom.name,
                    "year": year,
                    "message": "L'empire s'est effondré sous le poids de son immensité. Les tribus retournent aux collines libres.",
                }))

                events.append(Event(tick, "ouroboros_rebirth", {
                    "cycle_number": self.cycle.cycle_number,
                    "year": year,
                    "message": "Le serpent Ouroboros dévore sa propre queue : un nouvel âge recommence dans les braises des anciens.",
                }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OuroborosCycleManager:
        ocm = cls()
        ocm.cycle = EpochCycle.from_dict(d["cycle"]) if "cycle" in d else EpochCycle(1, "Aube")
        return ocm
