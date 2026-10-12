"""M16 - Récursivité des Univers & Dérivation Multiverselle.

Ce module gère la filiation cosmique et la récursion d'univers :
- Génération d'univers enfants à partir d'un univers parent (`spawn_child`)
- Mutation des constantes cosmologiques fondamentales (gravité, climat, richesse des sols, mutations)
- Arbre généalogique multiversel et traçabilité de divergence physique
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .constants import UniverseConstants
    from .engine import Universe


@dataclass
class UniverseNode:
    id: str
    parent_id: str | None
    seed: int
    created_at_tick: int
    constants: dict[str, Any]
    children_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UniverseNode:
        return cls(**d)


class MultiverseRegistry:
    """Gestionnaire de l'arbre multiversel et des filiations d'univers."""

    def __init__(self):
        self.nodes: dict[str, UniverseNode] = {}

    def register(self, universe: Universe):
        if universe.id not in self.nodes:
            node = UniverseNode(
                id=universe.id,
                parent_id=universe.parent_id,
                seed=universe.seed,
                created_at_tick=universe.tick,
                constants=universe.consts.to_dict(),
            )
            self.nodes[universe.id] = node
            if universe.parent_id and universe.parent_id in self.nodes:
                self.nodes[universe.parent_id].children_ids.append(universe.id)

    def spawn_child(self, parent: Universe, child_id: str,
                    seed: int | None = None, amplitude: float = 0.05) -> Universe:
        """Donne naissance à un univers enfant avec variations des lois physiques."""
        from .engine import Universe

        child_seed = seed if seed is not None else parent.rng.child_seed(f"child-{child_id}")
        mutated_consts: UniverseConstants = parent.consts.mutate(parent.rng, amplitude=amplitude)

        child = Universe(
            universe_id=child_id,
            seed=child_seed,
            consts=mutated_consts,
            start_year=0,
            parent_id=parent.id,
        )
        self.register(child)
        return child

    def get_lineage(self, universe_id: str) -> dict[str, Any]:
        """Retourne la lignée ascendante et descendante d'un univers."""
        node = self.nodes.get(universe_id)
        if not node:
            return {"id": universe_id, "found": False}

        # Ascendance
        ancestors = []
        curr = node.parent_id
        while curr and curr in self.nodes:
            ancestors.append(self.nodes[curr].to_dict())
            curr = self.nodes[curr].parent_id

        # Descendance directe
        children = [self.nodes[cid].to_dict() for cid in node.children_ids if cid in self.nodes]

        return {
            "universe": node.to_dict(),
            "ancestors": ancestors,
            "children": children,
            "total_multiverse_count": len(self.nodes),
        }

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": {k: v.to_dict() for k, v in self.nodes.items()}}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MultiverseRegistry:
        reg = cls()
        reg.nodes = {k: UniverseNode.from_dict(v) for k, v in d.get("nodes", {}).items()}
        return reg
