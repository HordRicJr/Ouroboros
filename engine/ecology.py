"""M06/M08 - Écosystème et population de masse (niveau statistique).

État : N[s, stade, y, x] (stades : 0 juvénile, 1 adulte, 2 âgé) et T[s, trait, y, x]
(traits moyens de l'espèce s dans la case). Dynamique de type Lotka-Volterra avec
réponse fonctionnelle saturante, sélection naturelle annuelle, dispersion hebdomadaire,
spéciation (divergence génétique) et extinction.
"""
from __future__ import annotations

import numpy as np

from .climate import Climate, Weather
from .constants import UniverseConstants
from .events import Event
from .genetics import (
    I_AGGR,
    I_CAMO,
    I_COLD,
    I_DIG,
    I_DROUGHT,
    I_FERT,
    I_HEAT,
    I_IMM,
    I_INT,
    I_LONG,
    I_META,
    I_RES,
    I_SENS,
    I_SIZE,
    I_SOC,
    I_SPEED,
    NT,
)
from .rng import Rng
from .species import (
    ARCHETYPES,
    DIET,
    HERBIVORE,
    HUMAN,
    KIND_PARAMS,
    PLANT,
    PREDATOR,
    Species,
    new_species_name,
)
from .worldmap import Biome, WorldMap

K0_PLANT = 20000.0
STAGES = np.array([0.25, 0.55, 0.20])
DT = 1.0 / 365.0
SPECIATION_THRESHOLD = 0.08
CELL_MIN = 1e-4   # seuil numérique seulement : la dispersion doit conserver la masse (pas de suppression des franges)
SATIETY = 0.4     # disponibilité de nourriture pondérée à partir de laquelle un consommateur est rassasié

_B_COMMON = {I_RES: .30, I_IMM: .25, I_SENS: .15, I_LONG: .15, I_FERT: .30, I_META: .15, I_DIG: .20, I_SOC: .10}
_B_KIND = {
    PLANT: {I_SIZE: .2},
    HERBIVORE: {I_SPEED: .35, I_CAMO: .25, I_INT: .25, I_SIZE: .2},
    PREDATOR: {I_SPEED: .4, I_AGGR: .35, I_INT: .3, I_SENS: .15, I_SIZE: .2},
    HUMAN: {I_SPEED: .1, I_INT: .5, I_SOC: .2, I_SIZE: .1},
}
_COST = np.zeros(NT)
for _i, _c in {I_SIZE: .35, I_RES: .15, I_FERT: .30, I_INT: .30, I_LONG: .15, I_SPEED: .20, I_META: .2,
               I_COLD: .08, I_HEAT: .08, I_DROUGHT: .1, I_AGGR: .12, I_SOC: .15, I_CAMO: .1,
               I_SENS: .1, I_DIG: .2, I_IMM: .12}.items():
    _COST[_i] = _c


def _benefit(kind: str) -> np.ndarray:
    b = np.zeros(NT)
    for i, v in {**_B_COMMON, **_B_KIND[kind]}.items():
        b[i] = v
    return b


def suitability(cold: np.ndarray, heat: np.ndarray, temp: np.ndarray) -> np.ndarray:
    """Adéquation climatique (0..1) selon les tolérances au froid et à la chaleur."""
    tmin = 18.0 - 55.0 * cold
    tmax = 8.0 + 38.0 * heat
    return np.clip(1.0 - (np.maximum(tmin - temp, 0) + np.maximum(temp - tmax, 0)) / 12.0, 0.0, 1.0)


def _nb_sum(a: np.ndarray) -> np.ndarray:
    p = np.pad(a, [(0, 0)] * (a.ndim - 2) + [(1, 1), (1, 1)])
    return p[..., :-2, 1:-1] + p[..., 2:, 1:-1] + p[..., 1:-1, :-2] + p[..., 1:-1, 2:]


def _diffuse(x: np.ndarray, rate: np.ndarray, land: np.ndarray) -> np.ndarray:
    """Dispersion conservative vers les 4 voisins terrestres."""
    L = land.astype(float)
    nl = _nb_sum(L)
    r = rate * x
    return (x - r * nl / 4.0 + _nb_sum(r) / 4.0 * L) * L


def _weighted_median(T: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Médiane pondérée par trait (robuste aux sous-populations divergentes). T: (NT,H,W), w: (H,W)."""
    idx = np.flatnonzero(w.ravel() > 0)
    wv = w.ravel()[idx]
    out = np.empty(T.shape[0])
    for t in range(T.shape[0]):
        v = T[t].ravel()[idx]
        order = np.argsort(v)
        cw = np.cumsum(wv[order])
        out[t] = v[order][np.searchsorted(cw, cw[-1] / 2.0)]
    return out


class Ecosystem:
    def __init__(self, species: list[Species], N: np.ndarray, T: np.ndarray):
        self.species = species
        self.N = N
        self.T = T
        self.feff = np.ones(N.shape[:1] + N.shape[2:])
        self.human_cells: list[tuple[int, int]] = []

    # ------------------------------------------------------------------ genèse
    @classmethod
    def genesis(cls, world: WorldMap, consts: UniverseConstants, rng: Rng, tick: int = 0) -> Ecosystem:
        g = rng.gen("genesis")
        H, W = world.elevation.shape
        land = world.is_land
        species, Ts = [], []
        for i, (name, kind, traits) in enumerate(ARCHETYPES):
            species.append(Species(i, name, kind, None, tick, None, traits.tolist()))
            Ts.append(np.clip(traits[:, None, None] + g.normal(0, 0.02, (NT, H, W)), 0, 1))
        T = np.stack(Ts)
        S = len(species)
        N = np.zeros((S, 3, H, W))
        me = np.clip(world.moisture / 0.6, 0, 1)
        for s, sp in enumerate(species):
            suit = suitability(T[s, I_COLD], T[s, I_HEAT], world.mean_temp) * land
            if sp.kind == PLANT:
                K = K0_PLANT * consts.soil_richness * (0.1 + 0.9 * me ** (1 - 0.8 * T[s, I_DROUGHT])) * suit
                tot = 0.3 * K
            elif sp.kind == HERBIVORE:
                tot = np.where((suit > 0.5) & (g.random((H, W)) < 0.5), 20.0, 0.0) * land
            elif sp.kind == PREDATOR:
                tot = np.where((suit > 0.5) & (g.random((H, W)) < 0.2), 3.0, 0.0) * land
            else:
                tot = np.zeros((H, W))
            N[s] = tot[None] * STAGES[:, None, None]
        eco = cls(species, N, T)
        # humains : 3 campements dans des cases favorables, de préférence près d'une rivière
        h = next(i for i, sp in enumerate(species) if sp.kind == HUMAN)
        riv = (_nb_sum(world.river.astype(float)) > 0) | world.river
        ok = land & np.isin(world.biome, [Biome.GRASSLAND, Biome.SAVANNA, Biome.FOREST]) & (world.mean_temp > 5)
        cand = np.argwhere(ok & riv)
        if len(cand) < 3:
            cand = np.argwhere(ok) if ok.sum() >= 3 else np.argwhere(land)
        pick = g.choice(len(cand), size=min(3, len(cand)), replace=False)
        for k in pick:
            y, x = (int(v) for v in cand[k])
            eco.human_cells.append((y, x))
            N[h, :, y, x] = 30.0 * np.array([0.35, 0.55, 0.10])
        return eco

    # --------------------------------------------------------------- utilitaires
    def totals(self) -> np.ndarray:
        return self.N.sum(axis=(1, 2, 3))

    def stats(self) -> list[dict]:
        tot = self.totals()
        return [{"id": s.id, "name": s.name, "kind": s.kind, "parent_id": s.parent_id,
                 "born_tick": s.born_tick, "extinct_tick": s.extinct_tick, "population": float(tot[s.id])}
                for s in self.species]

    def species_index(self, kind: str) -> list[int]:
        return [s.id for s in self.species if s.kind == kind and s.extinct_tick is None]

    def _kind_arrays(self):
        kp = [KIND_PARAMS[s.kind] for s in self.species]
        col = lambda k: np.array([p[k] for p in kp])[:, None, None]
        return {k: col(k) for k in ("bio", "need", "birth", "life", "mat", "half")}

    def _diet_matrix(self) -> np.ndarray:
        S = len(self.species)
        alive = {k: [s.id for s in self.species if s.kind == k and s.extinct_tick is None] for k in KIND_PARAMS}
        W = np.zeros((S, S))
        for s in self.species:
            if s.extinct_tick is not None:
                continue
            for pk, w in DIET.get(s.kind, {}).items():
                if alive[pk]:
                    for p in alive[pk]:
                        W[s.id, p] = w / len(alive[pk])
        return W

    # --------------------------------------------------------------- pas quotidien
    def step(self, tick: int, weather: Weather, world: WorldMap, consts: UniverseConstants,
             rng: Rng, climate: Climate, days: int = 7) -> list[Event]:
        """Avance l'écosystème de `days` jours en un pas (agrégation hebdomadaire par défaut)."""
        events: list[Event] = []
        dt = days / 365.0
        S = len(self.species)
        land = world.is_land
        N, T = self.N, self.T
        kp = self._kind_arrays()
        is_plant = np.array([s.kind == PLANT for s in self.species])[:, None, None]
        Ntot = N.sum(1)

        suit = suitability(T[:, I_COLD], T[:, I_HEAT], weather.temperature) * land
        me = np.clip(world.moisture / 0.6, 0, 1)
        me_s = me[None] ** np.clip(1.0 - 0.8 * T[:, I_DROUGHT], 0.1, 1.0)
        K = K0_PLANT * consts.soil_richness * (0.1 + 0.9 * me_s) * suit

        # --- prédation / consommation (réponse fonctionnelle saturante)
        Wd = self._diet_matrix()
        sat = Ntot / (Ntot + kp["half"])
        kills = np.zeros_like(Ntot)
        demands = []
        for s in range(S):
            if kp["need"][s, 0, 0] == 0 or self.species[s].extinct_tick is not None:
                continue
            # le consommateur se rabat sur les proies disponibles : la demande totale est plafonnée
            # à 0.7 (satiété pleine) et répartie au prorata de poids * disponibilité * réussite
            contrib = []
            for p in range(S):
                w = Wd[s, p]
                if w <= 0:
                    continue
                if is_plant[p, 0, 0]:
                    succ = 1.0
                else:
                    succ = np.clip(0.75 + 0.5 * (T[s, I_SPEED] - T[p, I_SPEED]) + 0.3 * (T[s, I_SENS] - T[p, I_CAMO]), 0.2, 1.0)
                contrib.append((p, w * sat[p] * succ))
            if not contrib:
                continue
            tot_c = sum(c for _, c in contrib)
            frac = np.minimum(tot_c, SATIETY) / (tot_c + 1e-12)
            for p, c in contrib:
                dem = days * kp["need"][s, 0, 0] * Ntot[s] * c * frac
                demands.append((s, p, dem))
                kills[p] += dem / kp["bio"][p, 0, 0]
        scale = np.where(kills > 0, np.minimum(1.0, 0.2 * Ntot / (kills + 1e-9)), 1.0)
        got = np.zeros_like(Ntot)
        for s, p, dem in demands:
            got[s] += dem * scale[p]
        need_tot = kp["need"] * Ntot
        feff = np.where(need_tot > 1e-9, np.clip(got / (days * need_tot + 1e-12) / SATIETY, 0, 1), 1.0)
        feff = np.where(is_plant, 1.0, feff)
        self.feff = feff
        loss = np.clip(kills * scale / (Ntot + 1e-9), 0, 0.2)
        N *= (1.0 - loss)[:, None]

        # --- démographie par stade
        life = kp["life"] * (0.5 + T[:, I_LONG])
        mat = kp["mat"]
        mat_f = np.minimum(1.0, dt / mat)
        adult_y = np.maximum(1.0, 0.55 * life - mat)
        ad_f = np.minimum(1.0, dt / adult_y)
        mres = (1.5 - T[:, I_RES]) * (1.3 - 0.6 * T[:, I_IMM])
        stress = (1 - suit) * 1.5 + np.where(is_plant, 0.0, (1 - feff) * 1.0)
        over = np.where(is_plant, np.clip(1 - K / (Ntot + 1e-9), 0, 1) * 0.8, 0.0)
        mJ = np.minimum(1.0, (0.69 / mat * mres + stress + over) * dt)
        mA = np.minimum(1.0, (0.5 / life * mres + stress + over) * dt)
        mE = np.minimum(1.0, (3.0 / life * mres + stress + over) * dt)
        fert = kp["birth"] * (0.5 + T[:, I_FERT])
        J, A, E = N[:, 0], N[:, 1], N[:, 2]
        crowd = np.where(is_plant, np.clip(1 - Ntot / (K + 1e-9), 0, 1), feff)
        births = A * fert * dt * crowd * suit
        nJ = J + births - J * mJ - J * mat_f
        nA = A + J * mat_f - A * mA - A * ad_f
        nE = E + A * ad_f - E * mE
        N = np.stack([nJ, nA, nE], axis=1)
        N = np.maximum(N, 0.0) * land
        N[(N.sum(1) < CELL_MIN)[:, None].repeat(3, 1)] = 0.0

        # --- dispersion (une fois par pas)
        rate = np.where(is_plant, 0.01, 0.02 * (0.5 + T[:, I_SPEED]))[:, None]  # (S,1,H,W) ou (S,1,1,1)
        rate = np.broadcast_to(rate, (S, 1) + land.shape)
        wt = N.sum(1, keepdims=True)
        newN = _diffuse(N, rate, land)
        newwt = newN.sum(1, keepdims=True)
        mixed = _diffuse(T * wt, rate, land)
        T = np.where(newwt > CELL_MIN, mixed / np.maximum(newwt, 1e-9), T)
        N = newN
        N[(N.sum(1) < CELL_MIN)[:, None].repeat(3, 1)] = 0.0

        self.N, self.T = N, T
        events += self._extinctions(tick)
        return events

    def yearly(self, tick: int, world: WorldMap, consts: UniverseConstants, rng: Rng,
               climate: Climate) -> list[Event]:
        """Sélection naturelle, spéciation et extinctions - une fois par an."""
        events = self._selection(world, climate, consts, rng, tick)
        events += self._speciation(world, rng, tick)
        events += self._extinctions(tick)
        return events

    # ------------------------------------------------------- sélection naturelle
    def _selection(self, world: WorldMap, climate: Climate, consts: UniverseConstants, rng: Rng,
                   tick: int) -> list[Event]:
        len(self.species)
        T, N = self.T, self.N
        Ntot = N.sum(1)
        g = rng.gen("selection", tick)
        B = np.stack([_benefit(s.kind) for s in self.species])           # (S, NT)
        grad = B[:, :, None, None] - 2 * _COST[None, :, None, None] * T   # (S, NT, H, W)
        cold_env = np.clip((10.0 - world.mean_temp) / 30.0, -1, 1)
        plant = np.array([s.kind == PLANT for s in self.species], dtype=float)[:, None, None]
        grad[:, I_SIZE] += 0.4 * cold_env[None]
        grad[:, I_DROUGHT] += 0.4 * (1 - world.moisture)[None] * (0.3 + 0.7 * plant)
        # gradient de l'adéquation climatique (différences finies, extrêmes saisonniers inclus)
        temps = [world.mean_temp - climate.season_amp, world.mean_temp, world.mean_temp + climate.season_amp]
        eps = 0.02

        def logs(cold, heat):
            return np.log(np.maximum(np.mean([suitability(cold, heat, t) for t in temps], axis=0), 0.02))
        base = logs(T[:, I_COLD], T[:, I_HEAT])
        grad[:, I_COLD] += (logs(T[:, I_COLD] + eps, T[:, I_HEAT]) - base) / eps
        grad[:, I_HEAT] += (logs(T[:, I_COLD], T[:, I_HEAT] + eps) - base) / eps
        V = 0.01 + consts.mutation_rate
        drift_sd = 0.004 * np.sqrt(consts.mutation_rate / 0.01) / np.sqrt(1 + Ntot / 50.0)
        noise = g.normal(0, 1, T.shape) * drift_sd[:, None]
        present = (Ntot > 0.5)[:, None]
        self.T = np.where(present, np.clip(T + V * grad + noise, 0.0, 1.0), T)
        return []

    # ----------------------------------------------------------------- spéciation
    def _speciation(self, world: WorldMap, rng: Rng, tick: int) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("speciation", tick)
        land = world.is_land
        for s in list(range(len(self.species))):
            sp = self.species[s]
            if sp.kind == HUMAN or sp.extinct_tick is not None:
                continue
            Ntot = self.N[s].sum(0)
            tot = Ntot.sum()
            if tot < 150:
                continue
            c = _weighted_median(self.T[s], Ntot)
            d = np.sqrt(np.mean((self.T[s] - c[:, None, None]) ** 2, axis=0))
            mask = (d > SPECIATION_THRESHOLD) & (Ntot > 2) & land
            if mask.sum() < 3 or Ntot[mask].sum() < 100 or Ntot[~mask].sum() < 50:
                continue
            new_id = len(self.species)
            m_tot = Ntot[mask].sum()
            cn = (self.T[s][:, mask] * Ntot[mask]).sum(axis=1) / m_tot
            name = new_species_name(sp.name, g)
            self.species.append(Species(new_id, name, sp.kind, sp.id, tick, None, cn.tolist()))
            newN = self.N[s] * mask[None]
            newT = np.where(mask[None], self.T[s], cn[:, None, None])
            self.N[s] = self.N[s] * (~mask)[None]
            self.N = np.concatenate([self.N, newN[None]])
            self.T = np.concatenate([self.T, newT[None]])
            self.feff = np.concatenate([self.feff, np.ones((1,) + land.shape)])
            events.append(Event(tick, "speciation", {"species_id": new_id, "name": name, "parent_id": sp.id,
                                                      "parent_name": sp.name, "population": float(m_tot)}))
        return events

    # ----------------------------------------------------------------- extinctions
    def _extinctions(self, tick: int) -> list[Event]:
        events = []
        tot = self.totals()
        for s in self.species:
            if s.extinct_tick is None and tot[s.id] < 0.5:
                s.extinct_tick = tick
                self.N[s.id] = 0.0
                events.append(Event(tick, "extinction", {"species_id": s.id, "name": s.name, "kind": s.kind}))
        return events
