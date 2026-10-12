"""M22 - Monnaies, Standards de Valeur & Trésors Métalliques.

Ce module modélise le passage du troc à l'économie monétaire :
- Émergence des devises (Cauris Marins, Lingots de Cuivre, Sicles d'Argent, Pièces Frappées)
- Évaluation standardisée des richesses claniques
- Thésaurisation, trésors royaux et dévaluation monétaire
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .rng import Rng
    from .society import Society
    from .trade import TradeNetwork

CURRENCY_TIERS = [
    ("Coquillages Cauris", "Devise primitive marine utilisée pour les menus échanges", 1.0),
    ("Haches de Cuivre Votif", "Lingots de métal fondu à valeur standardisée", 5.0),
    ("Sicles d'Argent Massif", "Poids d'argent pur scellé par les chefs de clan", 20.0),
    ("Drachmes Frappées à l'Effigie Royale", "Monnaie officielle garantie par le souverain", 100.0),
]


@dataclass
class Currency:
    clan_id: int
    name: str
    description: str
    unit_multiplier: float
    introduced_year: int
    treasury_reserve: float = 500.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Currency:
        return cls(**d)


class EconomyManager:
    """Gestionnaire des systèmes monétaires et trésoreries des clans."""

    def __init__(self):
        self.currencies: dict[int, Currency] = {}  # clan_id -> Currency
        self.total_minted: float = 0.0

    def step(self, tick: int, year: int, society: Society, trade: TradeNetwork, rng: Rng) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("economy", tick)

        for clan_id, clan in society.clans.items():
            wealth = trade.clan_wealth.get(clan_id, 0.0)

            # 1. Émergence ou transition de monnaie si richesse suffisante
            if clan_id not in self.currencies:
                tier_idx = 0 if wealth < 300 else 1
                c_name, c_desc, c_mult = CURRENCY_TIERS[tier_idx]
                curr = Currency(
                    clan_id=clan_id,
                    name=c_name,
                    description=c_desc,
                    unit_multiplier=c_mult,
                    introduced_year=year,
                    treasury_reserve=max(100.0, wealth * c_mult),
                )
                self.currencies[clan_id] = curr
                events.append(Event(tick, "currency_adopted", {
                    "clan_id": clan_id,
                    "clan_name": clan.name,
                    "currency_name": curr.name,
                    "multiplier": curr.unit_multiplier,
                    "year": year,
                }))
            else:
                curr = self.currencies[clan_id]
                # Progression vers des monnaies plus sophistiquées
                if wealth > 800 and curr.unit_multiplier < 20.0 and g.random() < 0.2:
                    curr.name, curr.description, curr.unit_multiplier = CURRENCY_TIERS[2]
                    events.append(Event(tick, "currency_reformed", {
                        "clan_id": clan_id,
                        "currency_name": curr.name,
                        "year": year,
                    }))
                elif wealth > 2000 and curr.unit_multiplier < 100.0 and g.random() < 0.15:
                    curr.name, curr.description, curr.unit_multiplier = CURRENCY_TIERS[3]
                    events.append(Event(tick, "currency_reformed", {
                        "clan_id": clan_id,
                        "currency_name": curr.name,
                        "year": year,
                    }))

                # Évolution du trésor clanique annuel
                delta = float(g.uniform(-20.0, 50.0)) * curr.unit_multiplier
                curr.treasury_reserve = max(0.0, curr.treasury_reserve + delta)

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "currencies": [c.to_dict() for c in self.currencies.values()],
            "total_minted": self.total_minted,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EconomyManager:
        em = cls()
        em.total_minted = d.get("total_minted", 0.0)
        em.currencies = {c["clan_id"]: Currency.from_dict(c) for c in d.get("currencies", [])}
        return em
