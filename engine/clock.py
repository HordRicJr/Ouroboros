"""M01 - Temps et calendrier. Règle : 1 seconde réelle = 1 jour simulé.

Le tick 0 correspond au 1er jour de l'année `start_year`. Les années négatives
sont supportées (numérotation astronomique : l'année 0 existe). Une année est
bissextile si divisible par 4 (sauf siècles non divisibles par 400), à partir
d'une année de base de 365 jours ; si `year_length_days` n'est pas 365, pas de
bissextile (univers aux années exotiques).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

SECONDS_PER_DAY = 1.0  # 1 s réelle = 1 jour simulé


@dataclass(frozen=True)
class Date:
    year: int
    day_of_year: int  # 0-indexé
    year_length: int

    @property
    def season_phase(self) -> float:
        """0..1 sur l'année (0 = début d'année)."""
        return self.day_of_year / self.year_length

    def __str__(self) -> str:
        return f"An {self.year}, jour {self.day_of_year + 1}/{self.year_length}"


class Calendar:
    def __init__(self, year_length_days: int = 365, start_year: int = 0):
        self.base = year_length_days
        self.start_year = start_year
        self.leap = year_length_days == 365

    def is_leap(self, year: int) -> bool:
        return self.leap and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))

    def year_length(self, year: int) -> int:
        return self.base + (1 if self.is_leap(year) else 0)

    def date_at(self, tick: int) -> Date:
        year, day = self.start_year, tick
        # saut rapide par blocs de 400 ans (146097 jours en grégorien)
        if self.leap and day >= 146097:
            blocks = day // 146097
            year += 400 * blocks
            day -= 146097 * blocks
        elif not self.leap and day >= self.base:
            years = day // self.base
            year += years
            day -= years * self.base
        while day >= self.year_length(year):
            day -= self.year_length(year)
            year += 1
        return Date(year, day, self.year_length(year))

    def tick_of(self, year: int, day_of_year: int = 0) -> int:
        tick = 0
        y = self.start_year
        step = 1 if year >= y else -1
        while y != year:
            if step == 1:
                tick += self.year_length(y)
                y += 1
            else:
                y -= 1
                tick -= self.year_length(y)
        return tick + day_of_year


def real_seconds_to_ticks(elapsed_seconds: float, speed: float = 1.0) -> int:
    return int(math.floor(elapsed_seconds * speed / SECONDS_PER_DAY))
