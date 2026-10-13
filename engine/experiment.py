"""Module d'expérimentation, de reproductibilité et de branches d'univers pour Ouroboros.

Conforme à la Priorité 4 et aux principes PIMMUR :
- Journal complet et auditable de tous les appels LLM (prompt, réponse, graine, température, latence)
- Gestion des branches / forks d'instantanés pour comparer observation pure vs intervention
- Métadonnées de préenregistrement du protocole scientifique (ODD, conditions, versions des modèles)
"""
from __future__ import annotations

import copy
import time
from dataclasses import asdict, dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from engine.engine import Universe


@dataclass
class AICallRecord:
    record_id: int
    timestamp: float
    tick: int
    year: int
    agent_id: int | None
    model_name: str
    temperature: float
    prompt: str
    response: str
    duration_ms: float
    kind: str = "dialogue"  # "dialogue", "reflection", "naming", "deliberation"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AICallRecord:
        return cls(**d)


class AICallLogger:
    """Enregistre exhaustivement chaque interaction neuronale pour auditabilité et rejeu."""

    def __init__(self, max_records: int = 2000):
        self.records: list[AICallRecord] = []
        self.counter: int = 0
        self.max_records: int = max_records

    def log(
        self,
        tick: int,
        year: int,
        agent_id: int | None,
        model_name: str,
        temperature: float,
        prompt: str,
        response: str,
        duration_ms: float,
        kind: str = "dialogue",
    ) -> AICallRecord:
        self.counter += 1
        rec = AICallRecord(
            record_id=self.counter,
            timestamp=time.time(),
            tick=tick,
            year=year,
            agent_id=agent_id,
            model_name=model_name,
            temperature=temperature,
            prompt=prompt,
            response=response,
            duration_ms=round(duration_ms, 2),
            kind=kind,
        )
        self.records.append(rec)
        if len(self.records) > self.max_records:
            self.records.pop(0)
        return rec

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return [r.to_dict() for r in reversed(self.records[-limit:])]

    def to_dict(self) -> dict[str, Any]:
        return {
            "counter": self.counter,
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AICallLogger:
        logger = cls()
        logger.counter = data.get("counter", 0)
        logger.records = [AICallRecord.from_dict(r) for r in data.get("records", [])]
        return logger


@dataclass
class BranchMetadata:
    universe_id: str
    parent_universe_id: str | None = None
    fork_tick: int = 0
    fork_year: int = 0
    branch_type: str = "pure_observation"  # "pure_observation" | "observer_intervention"
    description: str = "Branche de référence"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BranchMetadata:
        return cls(**d)


def fork_universe_state(
    parent_universe: Universe,
    new_universe_id: str,
    branch_type: str = "observer_intervention",
    description: str = "",
) -> Universe:
    """Crée une copie autonome (branche / fork) d'un univers pour comparaison expérimentale."""
    from engine.engine import Universe

    # Cloner l'état profond via snapshot binaire
    snap_bytes = parent_universe.snapshot()
    cloned = Universe.from_snapshot(snap_bytes)
    cloned.id = new_universe_id
    cloned.branch_metadata = BranchMetadata(
        universe_id=new_universe_id,
        parent_universe_id=parent_universe.id,
        fork_tick=parent_universe.tick,
        fork_year=parent_universe.date.year,
        branch_type=branch_type,
        description=description or f"Fork depuis {parent_universe.id} au tick {parent_universe.tick}",
    )
    return cloned
