"""M02 - Carte du monde : relief, océans, rivières, biomes (grille grossière)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from .constants import UniverseConstants
from .rng import Rng


class Biome(IntEnum):
    OCEAN = 0
    ICE = 1
    TUNDRA = 2
    TAIGA = 3
    FOREST = 4
    GRASSLAND = 5
    SAVANNA = 6
    DESERT = 7
    RAINFOREST = 8
    MOUNTAIN = 9


def _fbm(g: np.random.Generator, h: int, w: int, octaves: int = 5) -> np.ndarray:
    """Bruit fractal par interpolation bilinéaire de grilles aléatoires."""
    out = np.zeros((h, w))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = 3 + 2 ** (o + 1)
        grid = g.random((n, n))
        ys = np.linspace(0, n - 1.0001, h)
        xs = np.linspace(0, n - 1.0001, w)
        y0, x0 = ys.astype(int), xs.astype(int)
        fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
        # lissage (smoothstep)
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        a = grid[y0][:, x0]
        b = grid[y0][:, x0 + 1]
        c = grid[y0 + 1][:, x0]
        d = grid[y0 + 1][:, x0 + 1]
        out += amp * (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy)
        total += amp
        amp *= 0.5
    out /= total
    return (out - out.min()) / (out.max() - out.min() + 1e-12)


def _blur(a: np.ndarray, passes: int) -> np.ndarray:
    for _ in range(passes):
        p = np.pad(a, 1, mode="edge")
        a = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] + p[1:-1, 1:-1] * 2) / 6
    return a


@dataclass
class WorldMap:
    height: int
    width: int
    elevation: np.ndarray     # 0..1
    sea_level: float
    latitude: np.ndarray      # 0 (équateur) .. 1 (pôle), par case
    hemisphere: np.ndarray    # +1 nord, -1 sud
    moisture: np.ndarray      # 0..1
    mean_temp: np.ndarray     # °C annuel moyen
    river: np.ndarray         # bool
    biome: np.ndarray         # int8 (Biome)

    @property
    def is_land(self) -> np.ndarray:
        return self.elevation >= self.sea_level

    def biome_name(self, y: int, x: int) -> str:
        b = int(self.biome[y, x])
        try:
            return Biome(b).name.lower()
        except ValueError:
            return "inconnu"

    def to_arrays(self) -> dict[str, np.ndarray]:
        return {
            "elevation": self.elevation, "latitude": self.latitude, "hemisphere": self.hemisphere,
            "moisture": self.moisture, "mean_temp": self.mean_temp, "river": self.river,
            "biome": self.biome, "sea_level": np.array(self.sea_level),
        }

    @classmethod
    def from_arrays(cls, a: dict[str, np.ndarray]) -> WorldMap:
        h, w = a["elevation"].shape
        return cls(h, w, a["elevation"], float(a["sea_level"]), a["latitude"], a["hemisphere"],
                   a["moisture"], a["mean_temp"], a["river"].astype(bool), a["biome"].astype(np.int8))


def _rivers(elev: np.ndarray, land: np.ndarray, moisture: np.ndarray) -> np.ndarray:
    h, w = elev.shape
    flow = np.where(land, 1.0 + moisture, 0.0)
    order = np.argsort(-elev, axis=None)
    nbrs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for idx in order:
        y, x = divmod(int(idx), w)
        if not land[y, x]:
            break
        best, by, bx = elev[y, x], -1, -1
        for dy, dx in nbrs:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and elev[ny, nx] < best:
                best, by, bx = elev[ny, nx], ny, nx
        if by >= 0:
            flow[by, bx] += flow[y, x]
    thr = max(12.0, np.percentile(flow[land], 94)) if land.any() else 1e9
    return land & (flow >= thr)


def generate_world(consts: UniverseConstants, rng: Rng) -> WorldMap:
    h, w = consts.map_height, consts.map_width
    g = rng.gen("worldgen")

    elev = _fbm(g, h, w, 6)
    # bords plus bas : continents entourés d'océan
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.minimum.reduce([yy, h - 1 - yy, xx, w - 1 - xx]) / (min(h, w) / 2)
    elev = elev * (0.55 + 0.45 * np.clip(edge * 2.2, 0, 1))
    elev = (elev - elev.min()) / (elev.max() - elev.min() + 1e-12)
    # sea_level est une fraction de la surface : on le convertit en seuil d'élévation
    sea = float(np.quantile(elev, consts.sea_level))
    land = elev >= sea

    lat_signed = (yy / (h - 1)) * 2 - 1       # -1 (sud) .. 1 (nord)
    latitude = np.abs(lat_signed)
    hemisphere = np.where(lat_signed >= 0, -1, 1).astype(np.int8)  # y=0 en haut = pôle nord

    ocean_prox = _blur((~land).astype(float), 8)
    moisture = np.clip(0.55 * _fbm(g, h, w, 4) + 0.7 * ocean_prox - 0.15 * np.clip((elev - sea) * 2, 0, 1), 0, 1)
    moisture = (moisture - moisture.min()) / (moisture.max() - moisture.min() + 1e-12)

    height_above = np.clip((elev - sea) / (1 - sea + 1e-12), 0, 1)
    mean_temp = consts.base_temperature + 15 - 55 * latitude ** 1.3 - 30 * height_above

    river = _rivers(elev, land, moisture)
    moisture = np.clip(moisture + _blur(river.astype(float), 2) * 2, 0, 1)

    biome = np.full((h, w), Biome.OCEAN, dtype=np.int8)
    t, m = mean_temp, moisture
    b = np.select(
        [t < -12, t < -2, (t < 6) & (m > 0.35), t < 6, m < 0.28, (t > 20) & (m > 0.7),
         (t > 18) & (m < 0.5), m > 0.55],
        [Biome.ICE, Biome.TUNDRA, Biome.TAIGA, Biome.TUNDRA, Biome.DESERT, Biome.RAINFOREST,
         Biome.SAVANNA, Biome.FOREST],
        default=Biome.GRASSLAND,
    ).astype(np.int8)
    b = np.where(height_above > 0.75, Biome.MOUNTAIN, b)
    biome = np.where(land, b, Biome.OCEAN).astype(np.int8)

    return WorldMap(h, w, elev, sea, latitude, hemisphere, moisture, mean_temp, river, biome)
