"""Module de mesures scientifiques et d'indicateurs d'émergence pour Ouroboros.

Conforme à la Priorité 3 de la feuille de route :
- Coefficient de Gini pour les ressources et l'influence (inégalités)
- Entropie de Shannon pour la diversité comportementale et la spécialisation
- Métriques de réseau social (densité, centralité de déférence)
- Dynamique des normes (adoption, transgression des tabous et coutumes)
- Démographie calibrée et espérance de vie
- Export au format JSON et CSV pour analyse scientifique reproductible
"""
from __future__ import annotations

import csv
import io
import math
from dataclasses import asdict, dataclass
from typing import Any


def calculate_gini(values: list[float]) -> float:
    """Calcule le coefficient de Gini (0.0 = égalité parfaite, 1.0 = inégalité maximale)."""
    if not values or len(values) < 2:
        return 0.0
    cleaned = [max(0.0, float(v)) for v in values]
    total = sum(cleaned)
    if total <= 0:
        return 0.0

    sorted_vals = sorted(cleaned)
    n = len(sorted_vals)
    cum_sum = 0.0
    sum_diff = 0.0
    for i, v in enumerate(sorted_vals):
        cum_sum += v
        sum_diff += (2 * (i + 1) - n - 1) * v

    gini = sum_diff / (n * total)
    return max(0.0, min(1.0, round(gini, 4)))


def calculate_shannon_entropy(counts: list[int] | dict[str, int]) -> float:
    """Calcule l'entropie de Shannon normalisée (0.0 à 1.0) d'une distribution discrète."""
    raw_counts = counts.values() if isinstance(counts, dict) else counts
    positive_counts = [c for c in raw_counts if c > 0]
    total = sum(positive_counts)
    if total <= 0 or len(positive_counts) <= 1:
        return 0.0

    h = 0.0
    for c in positive_counts:
        p = c / total
        h -= p * math.log2(p)

    h_max = math.log2(len(positive_counts))
    if h_max <= 0:
        return 0.0
    return round(h / h_max, 4)


@dataclass
class SeasonalMetricsSnapshot:
    tick: int
    year: int
    season: str
    population: int
    births_this_year: int = 0
    deaths_this_year: int = 0
    infant_mortality_rate: float = 0.0
    life_expectancy_est: float = 35.0

    # Inégalités
    gini_resources: float = 0.0
    gini_influence: float = 0.0

    # Diversité & Spécialisation
    behavioral_entropy: float = 0.0
    job_specialization_entropy: float = 0.0

    # Réseau social & Déférence
    network_density: float = 0.0
    avg_deference: float = 0.0
    max_deference: float = 0.0
    active_social_ties: int = 0

    # Culture, Normes & Institutions
    active_taboos_count: int = 0
    taboo_violation_rate: float = 0.0
    active_customs_count: int = 0
    beliefs_count: int = 0

    # Écologie
    biomass_ratio: float = 1.0
    food_reserve_ratio: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SeasonalMetricsSnapshot:
        return cls(**d)


class SimulationMetricsHistory:
    """Enregistre et analyse la série temporelle des métriques de la simulation."""

    def __init__(self):
        self.snapshots: list[SeasonalMetricsSnapshot] = []

    def record_snapshot(self, snapshot: SeasonalMetricsSnapshot) -> None:
        self.snapshots.append(snapshot)
        # Garder un historique complet ou borné si mémoire restreinte (ex: 1000 snapshots)
        if len(self.snapshots) > 1200:
            self.snapshots.pop(0)

    def get_latest(self) -> dict[str, Any] | None:
        if not self.snapshots:
            return None
        return self.snapshots[-1].to_dict()

    def get_summary(self) -> dict[str, Any]:
        """Résumé synthétique pour le tableau de bord de recherche."""
        if not self.snapshots:
            return {
                "total_snapshots": 0,
                "latest": None,
                "trends": {},
            }

        latest = self.snapshots[-1]
        first = self.snapshots[0]

        return {
            "total_snapshots": len(self.snapshots),
            "start_year": first.year,
            "current_year": latest.year,
            "latest": latest.to_dict(),
            "averages": {
                "gini_resources": round(sum(s.gini_resources for s in self.snapshots) / len(self.snapshots), 3),
                "gini_influence": round(sum(s.gini_influence for s in self.snapshots) / len(self.snapshots), 3),
                "behavioral_entropy": round(sum(s.behavioral_entropy for s in self.snapshots) / len(self.snapshots), 3),
                "network_density": round(sum(s.network_density for s in self.snapshots) / len(self.snapshots), 3),
            },
        }

    def export_csv(self) -> str:
        """Exporte l'historique complet en chaîne CSV pour l'analyse externe."""
        output = io.StringIO()
        if not self.snapshots:
            return ""

        fieldnames = list(asdict(self.snapshots[0]).keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for snap in self.snapshots:
            writer.writerow(snap.to_dict())

        return output.getvalue()

    def to_dict(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.snapshots]

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> SimulationMetricsHistory:
        hist = cls()
        hist.snapshots = [SeasonalMetricsSnapshot.from_dict(d) for d in data]
        return hist
