"""M08 - Espèces : registre, archétypes de départ, noms."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .genetics import IDX, NT

PLANT, HERBIVORE, PREDATOR, HUMAN = "plant", "herbivore", "predator", "human"
KINDS = [PLANT, HERBIVORE, PREDATOR, HUMAN]

# paramètres démographiques par type (biomasse relative, besoin quotidien en fraction de biomasse,
# natalité annuelle par adulte, durée de vie en années, âge de maturité en années)
KIND_PARAMS = {
    PLANT:     {"bio": 1.0,   "need": 0.0,   "birth": 3.0,  "life": 20.0, "mat": 1.0,  "half": 3000.0},
    HERBIVORE: {"bio": 50.0,  "need": 0.04,  "birth": 1.2,  "life": 12.0, "mat": 1.5,  "half": 15.0},
    PREDATOR:  {"bio": 120.0, "need": 0.015, "birth": 0.8,  "life": 15.0, "mat": 2.0,  "half": 5.0},
    HUMAN:     {"bio": 70.0,  "need": 0.025, "birth": 0.3,  "life": 60.0, "mat": 15.0, "half": 30.0},
}
# régime alimentaire : type consommé -> poids (somme = 1)
DIET = {
    HERBIVORE: {PLANT: 1.0},
    PREDATOR: {HERBIVORE: 1.0},
    HUMAN: {PLANT: 0.6, HERBIVORE: 0.4},
}


@dataclass
class Species:
    id: int
    name: str
    kind: str
    parent_id: int | None
    born_tick: int
    extinct_tick: int | None = None
    traits: list[float] | None = None   # centroïde à la naissance de l'espèce

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Species:
        return cls(**d)


def _t(**kw) -> np.ndarray:
    v = np.full(NT, 0.5)
    for k, x in kw.items():
        v[IDX[k]] = x
    return v


ARCHETYPES: list[tuple[str, str, np.ndarray]] = [
    ("Herbe", PLANT, _t(size=0.2, fertility=0.7, longevity=0.2, cold_tolerance=0.55, heat_tolerance=0.55, drought_tolerance=0.45, intelligence=0.0, speed=0.0)),
    ("Arbre", PLANT, _t(size=0.8, fertility=0.4, longevity=0.9, cold_tolerance=0.5, heat_tolerance=0.5, drought_tolerance=0.5, intelligence=0.0, speed=0.0)),
    ("Petit herbivore", HERBIVORE, _t(size=0.3, fertility=0.7, longevity=0.3, speed=0.6, camouflage=0.6, cold_tolerance=0.5, heat_tolerance=0.5, intelligence=0.3)),
    ("Grand herbivore", HERBIVORE, _t(size=0.8, fertility=0.35, longevity=0.7, speed=0.4, resilience=0.6, cold_tolerance=0.55, heat_tolerance=0.45, intelligence=0.35)),
    ("Prédateur", PREDATOR, _t(size=0.6, aggression=0.8, speed=0.7, senses=0.7, fertility=0.4, longevity=0.5, intelligence=0.5, cold_tolerance=0.5, heat_tolerance=0.5)),
    ("Humain", HUMAN, _t(size=0.5, intelligence=0.8, sociality=0.9, longevity=0.5, fertility=0.45, speed=0.4, cold_tolerance=0.5, heat_tolerance=0.5, drought_tolerance=0.4, aggression=0.4)),
]

_SYL = ["ar", "ben", "cor", "dal", "el", "fen", "gor", "hal", "ik", "jor", "kal", "lum", "mor", "nes", "or", "pel", "qui", "rav", "sol", "tur", "ul", "vel", "wyr", "zan"]


def new_species_name(parent_name: str, g: np.random.Generator) -> str:
    base = parent_name.split(" ")[0]
    suffix = "".join(g.choice(_SYL, 2))
    return f"{base} {suffix}"
