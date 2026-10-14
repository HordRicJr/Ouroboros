"""Module de sociométrie et de déférence émergente pour Ouroboros.

Conformément à la Priorité 1 du plan d'émergence :
- Aucun score d'autorité ni grade social n'est fixé arbitrairement par le code.
- Le statut social, l'influence et la renommée sont calculés à partir des interactions réelles :
  * Qui demande conseil à qui (graphe de déférence)
  * Qui est cité dans les souvenirs des autres (notoriété mémorielle)
  * Qui arbitre ou apaise les tensions (médiation)
  * Qui partage les vivres ou protège le camp (coopération)
- Le statut est une mesure de centralité de réseau (centralité de déférence / PageRank simplifié).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SocialInteraction:
    tick: int
    year: int
    source_id: int
    target_id: int
    kind: str  # "advice", "deference", "mention", "mediation", "sharing", "dispute"
    weight: float = 1.0


class SocialGraph:
    """Graphe social décentralisé traquant la déférence, les mentions et la coopération."""

    def __init__(self):
        # target_id -> {source_id: poids cumulé}
        self.deference_edges: dict[int, dict[int, float]] = {}
        # target_id -> nombre de citations dans la mémoire d'autrui
        self.memory_mentions: dict[int, int] = {}
        # target_id -> nombre d'arbitrages ou médiations réussis
        self.mediation_count: dict[int, int] = {}
        # Historique récent des interactions pour calcul des dynamiques
        self.recent_interactions: list[SocialInteraction] = []
        self.max_recent_history: int = 500

    def record_interaction(
        self,
        tick: int,
        year: int,
        source_id: int,
        target_id: int,
        kind: str,
        weight: float = 1.0,
    ) -> None:
        """Enregistre un fait d'interaction sociale réel entre deux agents."""
        if source_id == target_id:
            return

        interaction = SocialInteraction(tick, year, source_id, target_id, kind, weight)
        self.recent_interactions.append(interaction)
        if len(self.recent_interactions) > self.max_recent_history:
            self.recent_interactions.pop(0)

        if kind in ("advice", "deference", "obedience"):
            sources = self.deference_edges.setdefault(target_id, {})
            sources[source_id] = sources.get(source_id, 0.0) + weight
        elif kind == "mention":
            self.memory_mentions[target_id] = self.memory_mentions.get(target_id, 0) + 1
        elif kind == "mediation":
            self.mediation_count[target_id] = self.mediation_count.get(target_id, 0) + 1

    def calculate_deference_centrality(self, alive_person_ids: list[int]) -> dict[int, float]:
        """Calcule la centralité de déférence normalisée (0 à 100) pour chaque habitant vivant.
        
        S'appuie sur le degré entrant pondéré (combien d'agents différents s'en remettent à cet individu),
        les citations dans les souvenirs des autres et le rôle effectif de médiateur.
        """
        if not alive_person_ids:
            return {}

        raw_scores: dict[int, float] = {}
        for pid in alive_person_ids:
            # 1. Déférence entrante (qui vient demander conseil)
            in_sources = self.deference_edges.get(pid, {})
            in_weight = sum(w for sid, w in in_sources.items() if sid in alive_person_ids)
            unique_followers = len([sid for sid in in_sources if sid in alive_person_ids])

            # 2. Notoriété mémorielle (être cité dans les souvenirs d'autrui)
            mentions = float(self.memory_mentions.get(pid, 0))

            # 3. Médiation active
            mediations = float(self.mediation_count.get(pid, 0))

            # Score composite émergent
            # On valorise la diversité des fidèles (large consensus) plutôt que le spam d'un seul individu
            score = (unique_followers * 3.0) + (in_weight * 0.5) + (mentions * 1.5) + (mediations * 2.5)
            raw_scores[pid] = score

        max_score = max(raw_scores.values()) if raw_scores else 0.0

        normalized: dict[int, float] = {}
        for pid in alive_person_ids:
            score = raw_scores.get(pid, 0.0)
            if max_score > 0.0:
                # Échelle 5 à 100 (5 de base pour tout être vivant avec un entourage minimal)
                norm = 5.0 + (score / max_score) * 95.0
            else:
                # Au tout début du monde sans interactions préalables : égalité naturelle
                norm = 20.0
            normalized[pid] = round(norm, 1)

        return normalized

    def deduce_emergent_title(
        self,
        pid: int,
        age: float,
        centrality: float,
        has_spouse: bool,
        children_count: int,
        clan_name: str | None = None,
    ) -> tuple[str, str]:
        """Qualificatif descriptif empirique (pas un grade imposé).

        Critères documentés (préenregistrement) :
        - centralité ≥ 75 → souvent consulté
        - centralité ≥ 45 → voix entendue
        - âge ≥ 40 → aîné
        Les libellés sont des descriptions, pas des institutions.
        """
        suffix = f" ({clan_name})" if clan_name else ""

        if centrality >= 75.0:
            if age >= 35:
                return f"Souvent consulté{suffix}", "écoute"
            return f"Voix souvent entendue{suffix}", "écoute"
        elif centrality >= 45.0:
            if children_count >= 3:
                return f"Pilier de maisonnée{suffix}", "maison"
            return f"Voix consultée{suffix}", "écoute"
        elif age >= 40:
            return f"Aîné du camp{suffix}", "âge"
        elif children_count > 0:
            return f"Parent{suffix}", "maison"
        else:
            return f"Habitant{suffix}", "membre"

    def to_dict(self) -> dict[str, Any]:
        return {
            "deference_edges": {str(k): v for k, v in self.deference_edges.items()},
            "memory_mentions": {str(k): v for k, v in self.memory_mentions.items()},
            "mediation_count": {str(k): v for k, v in self.mediation_count.items()},
            "recent_count": len(self.recent_interactions),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SocialGraph:
        g = cls()
        g.deference_edges = {int(k): {int(sk): float(sv) for sk, sv in v.items()} for k, v in d.get("deference_edges", {}).items()}
        g.memory_mentions = {int(k): int(v) for k, v in d.get("memory_mentions", {}).items()}
        g.mediation_count = {int(k): int(v) for k, v in d.get("mediation_count", {}).items()}
        return g
