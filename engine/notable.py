"""Mémoire épisodique, croyances et biographie des individus notables.

Chaque notable conserve :
- Une mémoire à court terme (événements récents vécus directement)
- Une mémoire consolidée (faits majeurs marquants : deuil, mariage, famine, naissance, découverte)
- Un système de croyances subjectives (interprétation mythologique du monde, dieux, nature)
- Un rôle social (chef de camp, guérisseur, chasseur, conteur, aîné)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryItem:
    tick: int
    year: int
    text: str
    impact: float = 0.5  # 0.0 à 1.0 (gravité émotionnelle/mémorable)

    def to_dict(self) -> dict[str, Any]:
        return {"tick": self.tick, "year": self.year, "text": self.text, "impact": self.impact}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemoryItem:
        return cls(**d)


@dataclass
class NotableProfile:
    person_id: int
    title: str = "Habitant"                 # Ex: Chef de clan, Chamane, Chasseur émérite, Patriarche
    beliefs: list[str] = field(default_factory=lambda: [
        "Les esprits de la terre veillent sur nos pas",
        "Les saisons sont guidées par le souffle des ancêtres"
    ])
    memories: list[MemoryItem] = field(default_factory=list)
    short_term_log: list[str] = field(default_factory=list)
    max_memories: int = 20

    def add_memory(self, tick: int, year: int, text: str, impact: float = 0.5):
        self.memories.append(MemoryItem(tick, year, text, impact))
        # Consolidation : trier par impact et récence si dépassement
        if len(self.memories) > self.max_memories:
            # Conserver les plus marquants et les plus récents
            self.memories.sort(key=lambda m: (m.impact, m.tick), reverse=True)
            self.memories = self.memories[:self.max_memories]

    def log_short_term(self, text: str):
        self.short_term_log.append(text)
        if len(self.short_term_log) > 5:
            self.short_term_log.pop(0)

    def summary_context(self) -> str:
        """Produit le résumé de la mémoire pour injection dans le prompt."""
        lines = []
        if self.beliefs:
            lines.append("Croyances et vision du monde : " + "; ".join(self.beliefs))
        if self.memories:
            sorted_m = sorted(self.memories, key=lambda m: m.tick)
            lines.append("Souvenirs marquants : " + " | ".join(f"An {m.year}: {m.text}" for m in sorted_m[-6:]))
        if self.short_term_log:
            lines.append("Événements récents : " + " ; ".join(self.short_term_log))
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "title": self.title,
            "beliefs": list(self.beliefs),
            "memories": [m.to_dict() for m in self.memories],
            "short_term_log": list(self.short_term_log),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NotableProfile:
        p = cls(
            person_id=d["person_id"],
            title=d.get("title", "Habitant"),
            beliefs=d.get("beliefs", []),
            short_term_log=d.get("short_term_log", []),
        )
        p.memories = [MemoryItem.from_dict(m) for m in d.get("memories", [])]
        return p
