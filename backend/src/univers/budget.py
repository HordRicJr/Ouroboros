"""Contrôleur de budget et quotas d'appels LLM.

Permet de respecter scrupuleusement l'enveloppe budgétaire (ex: 100$) :
- Plafonnement quotidien / par tick simulé
- Coût estimé par token / appel
- Priorisation des notables majeurs (chefs, inventeurs, doyens)
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class AIBudgetManager:
    max_total_calls: int = 10_000
    max_calls_per_tick: int = 5
    max_cost_usd: float = 100.0
    cost_per_1k_tokens: float = 0.0002   # estimation Qwen2.5-7B ou équivalent petit modèle
    total_calls: int = 0
    total_tokens_used: int = 0
    tick_calls: dict[int, int] = field(default_factory=dict)

    @property
    def estimated_cost_usd(self) -> float:
        return (self.total_tokens_used / 1000.0) * self.cost_per_1k_tokens

    def can_call(self, tick: int, priority: int = 1) -> bool:
        """Vérifie si un appel IA est autorisé pour ce tick et selon les plafonds."""
        if self.total_calls >= self.max_total_calls:
            return False
        if self.estimated_cost_usd >= self.max_cost_usd:
            return False
        
        current_tick_count = self.tick_calls.get(tick, 0)
        # Priorité plus haute autorise un dépassement modéré par tick
        effective_limit = self.max_calls_per_tick * priority
        if current_tick_count >= effective_limit:
            return False
        
        return True

    def record_call(self, tick: int, tokens_used: int = 150):
        self.total_calls += 1
        self.total_tokens_used += tokens_used
        self.tick_calls[tick] = self.tick_calls.get(tick, 0) + 1

    def to_dict(self) -> dict:
        return {
            "max_total_calls": self.max_total_calls,
            "max_calls_per_tick": self.max_calls_per_tick,
            "max_cost_usd": self.max_cost_usd,
            "total_calls": self.total_calls,
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AIBudgetManager":
        bm = cls(
            max_total_calls=d.get("max_total_calls", 10_000),
            max_calls_per_tick=d.get("max_calls_per_tick", 5),
            max_cost_usd=d.get("max_cost_usd", 100.0),
        )
        bm.total_calls = d.get("total_calls", 0)
        bm.total_tokens_used = d.get("total_tokens_used", 0)
        return bm
