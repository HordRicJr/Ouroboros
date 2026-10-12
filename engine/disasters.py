"""M17 - Événements Cataclysmiques, Désastres Naturels & Résilience Écologique.

Ce module modélise les aléas majeurs affectant la planète simulée :
- Éruptions volcaniques et hivers de cendres (baisse temporaire de la température globale)
- Méga-sécheresses et vagues de chaleur (assèchement, feux de brousse, famine)
- Séismes et inondations côtières (destruction d'infrastructures et pertes locales)
- Épidémies primitives (propagation par proximité spatiale et troc)
- Impact psychologique profond : traumatismes consignés dans la mémoire des notables
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .climate import Climate
    from .ecology import Ecosystem
    from .people import People
    from .rng import Rng
    from .society import Society
    from .worldmap import WorldMap


@dataclass
class Disaster:
    id: int
    kind: str           # "volcano", "drought", "flood", "plague", "earthquake"
    name: str
    start_tick: int
    duration_days: int
    center_cell: tuple[int, int]
    radius: int
    severity: float     # 0.0 à 1.0
    active: bool = True
    casualties_count: int = 0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["center_cell"] = list(self.center_cell)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Disaster:
        d = dict(d)
        d["center_cell"] = tuple(d["center_cell"])
        return cls(**d)


class DisasterManager:
    """Gestionnaire mondial des cataclysmes et crises environnementales."""

    def __init__(self):
        self.disasters: dict[int, Disaster] = {}
        self.next_disaster_id = 1
        self.climate_temp_offset: float = 0.0  # Refroidissement temporaire (ex: cendres volcaniques)

    def active_disasters(self) -> list[Disaster]:
        return [d for d in self.disasters.values() if d.active]

    def trigger_disaster(self, kind: str, name: str, center: tuple[int, int],
                         radius: int, severity: float, duration: int, tick: int, description: str = "") -> Disaster:
        d = Disaster(
            id=self.next_disaster_id,
            kind=kind,
            name=name,
            start_tick=tick,
            duration_days=duration,
            center_cell=center,
            radius=radius,
            severity=severity,
            description=description,
        )
        self.disasters[d.id] = d
        self.next_disaster_id += 1
        return d

    def step(self, tick: int, year: int, world: WorldMap, climate: Climate,
             eco: Ecosystem, society: Society, people: People, rng: Rng) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("disasters", tick)

        # 1. Mise à jour et dissipation des désastres actifs
        self.climate_temp_offset = 0.0
        for dis in list(self.disasters.values()):
            if not dis.active:
                continue

            elapsed = tick - dis.start_tick
            if elapsed >= dis.duration_days:
                dis.active = False
                events.append(Event(tick, "disaster_ended", {
                    "disaster_id": dis.id,
                    "name": dis.name,
                    "kind": dis.kind,
                    "year": year,
                    "total_casualties": dis.casualties_count,
                }))
                continue

            # Effets continus
            if dis.kind == "volcano":
                # Panache de cendres obscurcissant : refroidissement mondial
                self.climate_temp_offset -= 3.5 * dis.severity

            # Dégâts humains locaux
            cy, cx = dis.center_cell
            for p in people.alive_persons():
                py, px = p.cell
                dist_sq = (py - cy)**2 + (px - cx)**2
                if dist_sq <= dis.radius**2:
                    # Risque de mortalité ou blessure
                    risk = (0.005 * dis.severity) / max(1, dist_sq**0.5)
                    if g.random() < risk:
                        p.death_tick = tick
                        p.cause_of_death = f"victime de la catastrophe ({dis.name})"
                        dis.casualties_count += 1
                        events.append(Event(tick, "disaster_casualty", {
                            "disaster_id": dis.id,
                            "disaster_name": dis.name,
                            "person_id": p.id,
                            "person_name": p.name,
                            "year": year,
                        }))

        # 2. Déclenchement probabiliste de nouveaux désastres (tirage rare tous les ans)
        if tick % 365 == 0:
            roll = float(g.random())
            if roll < 0.08:  # 8% par an d'événement cataclysmique
                # Choisir un type de catastrophe
                kind = str(g.choice(["volcano", "drought", "flood", "plague"]))
                rand_y = int(g.integers(10, world.height - 10))
                rand_x = int(g.integers(10, world.width - 10))
                center = (rand_y, rand_x)

                if kind == "volcano":
                    d = self.trigger_disaster(
                        kind="volcano",
                        name="La Colère du Mont de Feu",
                        center=center,
                        radius=25,
                        severity=float(g.uniform(0.6, 1.0)),
                        duration=365 * 2,  # 2 ans d'hiver volcanique
                        tick=tick,
                        description="Une explosion titanesque projette un épais voile de cendres masquant le soleil.",
                    )
                elif kind == "drought":
                    d = self.trigger_disaster(
                        kind="drought",
                        name="La Grande Sécheresse des Terres Arides",
                        center=center,
                        radius=15,
                        severity=float(g.uniform(0.5, 0.9)),
                        duration=180,
                        tick=tick,
                        description="Une chaleur implacable assèche les sources et flétrit les pâturages.",
                    )
                elif kind == "flood":
                    d = self.trigger_disaster(
                        kind="flood",
                        name="Le Débordement des Eaux Sauvages",
                        center=center,
                        radius=12,
                        severity=float(g.uniform(0.4, 0.8)),
                        duration=90,
                        tick=tick,
                        description="Des pluies torrentielles submergent les vallées fluviales et emportent les berges.",
                    )
                else:  # plague
                    d = self.trigger_disaster(
                        kind="plague",
                        name="Le Fléau des Fièvres Noires",
                        center=center,
                        radius=18,
                        severity=float(g.uniform(0.5, 0.85)),
                        duration=150,
                        tick=tick,
                        description="Une contagion pernicieuse se répand à travers les campements de la région.",
                    )

                events.append(Event(tick, "disaster_started", {
                    "disaster_id": d.id,
                    "name": d.name,
                    "kind": d.kind,
                    "year": year,
                    "center": list(center),
                    "radius": d.radius,
                    "description": d.description,
                }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "disasters": [d.to_dict() for d in self.disasters.values()],
            "next_disaster_id": self.next_disaster_id,
            "climate_temp_offset": self.climate_temp_offset,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DisasterManager:
        mgr = cls()
        mgr.next_disaster_id = d.get("next_disaster_id", 1)
        mgr.climate_temp_offset = d.get("climate_temp_offset", 0.0)
        mgr.disasters = {x["id"]: Disaster.from_dict(x) for x in d.get("disasters", [])}
        return mgr
