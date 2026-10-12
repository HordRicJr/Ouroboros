"""M04 - Climat et saisons : température, pluie, cycle jour/nuit, dérive lente."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .clock import Calendar
from .constants import UniverseConstants
from .rng import Rng
from .worldmap import WorldMap


@dataclass
class Weather:
    temperature: np.ndarray   # °C du jour
    rainfall: np.ndarray      # mm du jour
    daylight_hours: np.ndarray

    def summary(self, land: np.ndarray) -> dict:
        return {
            "mean_temp_land": float(self.temperature[land].mean()) if land.any() else None,
            "mean_rain_land": float(self.rainfall[land].mean()) if land.any() else None,
        }


class Climate:
    def __init__(self, world: WorldMap, consts: UniverseConstants, rng: Rng):
        self.world, self.consts, self.rng = world, consts, rng
        self.calendar = Calendar(consts.year_length_days)
        # amplitude saisonnière : faible sous les tropiques, forte en haute latitude
        self.season_amp = 2.0 + 18.0 * world.latitude ** 1.2
        self.cal_year_offset = 0

    def daylight(self, phase: float) -> np.ndarray:
        tilt = np.deg2rad(23.4)
        decl = tilt * np.sin(2 * np.pi * (phase - 0.2225))  # déclinaison solaire, nord positif
        lat = np.deg2rad(self.world.latitude * 90.0) * self.world.hemisphere  # nord > 0
        x = np.clip(-np.tan(lat) * np.tan(decl), -1, 1)
        return 24.0 * np.arccos(x) / np.pi

    def weather(self, tick: int, date_phase: float, year: int) -> Weather:
        w, g = self.world, self.rng.gen("weather", tick)
        shape = w.elevation.shape
        # hémisphère nord (+1) : plus chaud à mi-année ; sud (-1) : saisons inversées
        season = -np.cos(2 * np.pi * date_phase) * w.hemisphere
        drift = self.consts.climate_drift_per_century * (year / 100.0)
        temp = w.mean_temp + self.season_amp * season + drift + g.normal(0, 2.0, shape)
        # pluie : humidité locale, modulée par la saison, épisodes aléatoires
        seasonal = 1.0 + 0.4 * np.sin(2 * np.pi * date_phase + w.latitude * 3)
        wet_day = g.random(shape) < (0.15 + 0.5 * w.moisture)
        amount = g.gamma(2.0, 3.0, shape) * w.moisture * seasonal
        rain = np.where(wet_day & w.is_land, amount, 0.0)
        rain = np.where(~w.is_land, 0.0, rain)
        return Weather(temp, rain, self.daylight(date_phase))
