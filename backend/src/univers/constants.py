"""Constantes d'un univers (héritables avec variations par les univers enfants)."""
from __future__ import annotations

from dataclasses import dataclass, asdict, fields

from .rng import Rng


@dataclass(frozen=True)
class UniverseConstants:
    year_length_days: int = 365
    gravity: float = 9.81
    soil_richness: float = 1.0
    mutation_rate: float = 0.01
    sea_level: float = 0.45          # fraction de l'élévation normalisée sous laquelle c'est l'océan
    map_width: int = 100
    map_height: int = 100
    base_temperature: float = 15.0   # °C moyen à l'équateur - ajusté par la latitude
    climate_drift_per_century: float = 0.0  # °C / siècle (changement lent)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "UniverseConstants":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    def mutate(self, rng: Rng, amplitude: float = 0.05) -> "UniverseConstants":
        """Constantes d'un univers enfant : héritage + petites variations (±amplitude)."""
        g = rng.gen("constants-mutation")
        d = self.to_dict()
        for k in ("gravity", "soil_richness", "mutation_rate", "base_temperature"):
            d[k] = d[k] * (1.0 + float(g.uniform(-amplitude, amplitude)))
        d["sea_level"] = min(0.8, max(0.2, d["sea_level"] + float(g.uniform(-amplitude, amplitude)) * 0.5))
        return UniverseConstants(**d)
