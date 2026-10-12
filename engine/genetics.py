"""M07 - Génome simplifié : traits diploïdes, hérédité mendélienne, mutations."""
from __future__ import annotations

import numpy as np

TRAITS = [
    "size", "resilience", "fertility", "intelligence", "longevity", "speed",
    "metabolism", "cold_tolerance", "heat_tolerance", "drought_tolerance", "aggression",
    "sociality", "camouflage", "senses", "digestion", "immunity",
]
NT = len(TRAITS)
IDX = {t: i for i, t in enumerate(TRAITS)}
I_SIZE, I_RES, I_FERT, I_INT, I_LONG, I_SPEED, I_META, I_COLD, I_HEAT, I_DROUGHT, I_AGGR, I_SOC, I_CAMO, I_SENS, I_DIG, I_IMM = range(NT)


def phenotype(genome: np.ndarray) -> np.ndarray:
    """Génome (2, NT) -> valeurs de traits (NT,) : moyenne des deux allèles."""
    return genome.mean(axis=0)


def make_genome(traits: np.ndarray, g: np.random.Generator, spread: float = 0.03) -> np.ndarray:
    """Génome fondateur autour d'un vecteur de traits."""
    return np.clip(traits[None, :] + g.normal(0, spread, (2, NT)), 0.0, 1.0)


def make_child(a: np.ndarray, b: np.ndarray, g: np.random.Generator, mutation_rate: float,
               mutation_sd: float = 0.06) -> np.ndarray:
    """Un allèle par parent (tirage indépendant par trait) puis mutation aléatoire."""
    pick_a = g.integers(0, 2, NT)
    pick_b = g.integers(0, 2, NT)
    child = np.stack([a[pick_a, np.arange(NT)], b[pick_b, np.arange(NT)]])
    mask = g.random((2, NT)) < mutation_rate * 5   # prob. de mutation par allèle
    child = child + mask * g.normal(0, mutation_sd, (2, NT))
    return np.clip(child, 0.0, 1.0)


def distance(a: np.ndarray, b: np.ndarray) -> float:
    """Distance RMS entre deux vecteurs de traits."""
    return float(np.sqrt(np.mean((a - b) ** 2)))
