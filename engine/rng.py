"""M03 - Graine aléatoire par univers.

Les flux aléatoires sont *sans état* : chaque flux est dérivé de (seed, nom, tick).
Reprendre une sauvegarde ou rejouer un tick donne donc exactement les mêmes tirages.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np


def _name_key(name: str) -> int:
    return int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], "big")


@dataclass(frozen=True)
class Rng:
    seed: int

    def gen(self, name: str, tick: int = 0) -> np.random.Generator:
        ss = np.random.SeedSequence([self.seed & 0xFFFFFFFFFFFFFFFF, _name_key(name), tick & 0xFFFFFFFF, (tick >> 32) & 0xFFFFFFFF])
        return np.random.Generator(np.random.PCG64(ss))

    def child_seed(self, name: str = "child") -> int:
        """Graine déterministe pour un univers enfant."""
        return int(self.gen(name).integers(0, 2**63 - 1))
