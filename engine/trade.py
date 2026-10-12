"""M21 - Caravanes Commerciales, Routes Trans-Territoriales & Marchés Régionaux.

Ce module modélise les échanges économiques avancés entre clans et cités :
- Création dynamique de routes commerciales reliant deux campements/villages
- Envoi annuel d'expéditions et caravanes marchandes (terrestres ou fluviales)
- Négociation de denrées rares (obsidienne, sel, ambre, céréales, peaux ouvragées)
- Enrichissement mutuel, hausse de prospérité et transmission culturelle
- Risque d'embuscades de brigands ou de pertes en route
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .rng import Rng
    from .settlement import SettlementManager
    from .society import Society

EXCHANGE_COMMODITIES = [
    ("Obsidienne Noire", "Lames tranchantes et parures rituelles"),
    ("Sel Gemme", "Conservation des viandes et assaisonnement précieux"),
    ("Ambre du Nord", "Résine fossilisée échangée contre des vivres"),
    ("Peaux Tannées à l'Ocre", "Vêtements robustes et toiles de tentes"),
    ("Grains de Céréales Anciennes", "Semences et surplus de récolte"),
    ("Poteries Décorées", "Vases étanches pour stocker huile et miel"),
]


@dataclass
class TradeRoute:
    id: int
    name: str
    from_settlement_id: int
    to_settlement_id: int
    from_clan_id: int
    to_clan_id: int
    distance: float
    volume_traded: float
    established_year: int
    primary_good: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TradeRoute:
        return cls(**d)


@dataclass
class CaravanExpedition:
    id: int
    route_id: int
    year: int
    from_clan_id: int
    to_clan_id: int
    good: str
    profit: float
    success: bool
    incident: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CaravanExpedition:
        return cls(**d)


class TradeNetwork:
    """Gestionnaire des routes commerciales, des caravanes et des foires d'échange."""

    def __init__(self):
        self.routes: dict[int, TradeRoute] = {}
        self.expeditions: list[CaravanExpedition] = []
        self.clan_wealth: dict[int, float] = {}  # clan_id -> richesse/prospérité accumulée
        self.next_route_id = 1
        self.next_expedition_id = 1

    def step(self, tick: int, year: int, society: Society, settlements: SettlementManager, rng: Rng) -> list[Event]:
        """Évolution annuelle des routes commerciales et voyages de caravanes."""
        events: list[Event] = []
        g = rng.gen("trade", tick)

        active_settlements = list(settlements.settlements.values())
        if len(active_settlements) < 2:
            return events

        # Initialisation de la richesse si absente
        for cid in society.clans:
            if cid not in self.clan_wealth:
                self.clan_wealth[cid] = 100.0

        # 1. Établissement de nouvelles routes commerciales entre cités de clans distincts
        if len(self.routes) < 10 and g.random() < 0.35:
            # Choisir 2 campements/villages distincts de clans différents
            s1 = active_settlements[int(g.integers(0, len(active_settlements)))]
            s2 = active_settlements[int(g.integers(0, len(active_settlements)))]

            if s1.id != s2.id and s1.clan_id != s2.clan_id:
                # Vérifier si la route existe déjà
                route_exists = any(
                    (r.from_settlement_id == s1.id and r.to_settlement_id == s2.id) or
                    (r.from_settlement_id == s2.id and r.to_settlement_id == s1.id)
                    for r in self.routes.values()
                )
                if not route_exists:
                    dx = s1.cell[0] - s2.cell[0]
                    dy = s1.cell[1] - s2.cell[1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    good_name, _ = EXCHANGE_COMMODITIES[int(g.integers(0, len(EXCHANGE_COMMODITIES)))]
                    route_name = f"Piste de {good_name.split()[0]} ({s1.name} ↔ {s2.name})"

                    new_route = TradeRoute(
                        id=self.next_route_id,
                        name=route_name,
                        from_settlement_id=s1.id,
                        to_settlement_id=s2.id,
                        from_clan_id=s1.clan_id,
                        to_clan_id=s2.clan_id,
                        distance=round(dist, 1),
                        volume_traded=0.0,
                        established_year=year,
                        primary_good=good_name,
                    )
                    self.routes[new_route.id] = new_route
                    self.next_route_id += 1

                    events.append(Event(tick, "trade_route_opened", {
                        "route_id": new_route.id,
                        "route_name": new_route.name,
                        "from_settlement": s1.name,
                        "to_settlement": s2.name,
                        "primary_good": good_name,
                        "year": year,
                    }))

        # 2. Voyage des caravanes sur les routes existantes
        for route in list(self.routes.values()):
            if g.random() < 0.60:
                # Risque d'incident (brigandage / intempéries)
                incident = None
                success = True
                profit = round(float(g.uniform(15.0, 45.0)), 1)

                if g.random() < 0.15:
                    success = False
                    profit = 0.0
                    incident = str(g.choice([
                        "Attaque de pillards nomades sur les défilés rocheux",
                        "Caravane surprise par une crue soudaine de rivière",
                        "Animaux de bât affamés et perte du chargement précieux",
                    ]))

                if success:
                    route.volume_traded += profit
                    self.clan_wealth[route.from_clan_id] = self.clan_wealth.get(route.from_clan_id, 0.0) + profit
                    self.clan_wealth[route.to_clan_id] = self.clan_wealth.get(route.to_clan_id, 0.0) + (profit * 0.7)

                expedition = CaravanExpedition(
                    id=self.next_expedition_id,
                    route_id=route.id,
                    year=year,
                    from_clan_id=route.from_clan_id,
                    to_clan_id=route.to_clan_id,
                    good=route.primary_good,
                    profit=profit,
                    success=success,
                    incident=incident,
                )
                self.expeditions.append(expedition)
                self.next_expedition_id += 1

                events.append(Event(tick, "caravan_arrival", {
                    "expedition_id": expedition.id,
                    "route_name": route.name,
                    "good": route.primary_good,
                    "profit": profit,
                    "success": success,
                    "incident": incident,
                    "year": year,
                }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "routes": [r.to_dict() for r in self.routes.values()],
            "expeditions": [e.to_dict() for e in self.expeditions[-50:]],  # garder les 50 dernières
            "clan_wealth": {str(k): round(v, 1) for k, v in self.clan_wealth.items()},
            "next_route_id": self.next_route_id,
            "next_expedition_id": self.next_expedition_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TradeNetwork:
        tn = cls()
        tn.next_route_id = d.get("next_route_id", 1)
        tn.next_expedition_id = d.get("next_expedition_id", 1)
        tn.routes = {r["id"]: TradeRoute.from_dict(r) for r in d.get("routes", [])}
        tn.expeditions = [CaravanExpedition.from_dict(e) for e in d.get("expeditions", [])]
        tn.clan_wealth = {int(k): float(v) for k, v in d.get("clan_wealth", {}).items()}
        return tn
