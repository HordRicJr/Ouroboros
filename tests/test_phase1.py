import numpy as np

from univers.clock import Calendar
from univers.constants import UniverseConstants
from univers.engine import Universe
from univers.persistence import MemoryStore
from univers.rng import Rng
from univers.worldmap import Biome, generate_world


def test_rng_deterministic():
    a = Rng(42).gen("x", 5).random(4)
    b = Rng(42).gen("x", 5).random(4)
    c = Rng(42).gen("x", 6).random(4)
    assert (a == b).all() and not (a == c).all()


def test_calendar_leap_and_negative():
    cal = Calendar(365, start_year=-3004)
    assert cal.is_leap(-3004) and not cal.is_leap(-3000) and not cal.is_leap(1900) and cal.is_leap(2000)
    assert cal.date_at(0).year == -3004
    t = cal.tick_of(2015)
    assert cal.date_at(t).year == 2015 and cal.date_at(t).day_of_year == 0
    assert cal.date_at(t - 1).year == 2014
    assert cal.date_at(366).year == -3003  # -3004 est bissextile (366 jours)


def test_world_deterministic_and_valid():
    c = UniverseConstants()
    w1, w2 = generate_world(c, Rng(1)), generate_world(c, Rng(1))
    assert (w1.elevation == w2.elevation).all()
    assert w1.biome.shape == (100, 100)
    land = w1.is_land.mean()
    assert 0.3 < land < 0.7
    assert w1.river.any()
    assert len(set(np.unique(w1.biome))) >= 4
    assert not (w1.biome[~w1.is_land] != Biome.OCEAN).any()


def test_seasons_inverted_between_hemispheres():
    u = Universe("t", 7)
    north = np.where(u.world.hemisphere == 1)
    south = np.where(u.world.hemisphere == -1)
    cl = u.climate
    jan = cl.weather(0, 0.0, 0).temperature
    jul = cl.weather(1, 0.5, 0).temperature
    assert (jul - jan)[north].mean() > 0 > (jul - jan)[south].mean()


def test_step_and_resume_identical():
    u = Universe("a", 99, start_year=2015)
    u.step(400)
    store = MemoryStore()
    store.save(u)
    r = store.load("a")
    assert r.tick == 400
    e1, e2 = u.step(800), r.step(800)
    assert [e.to_dict() for e in e1] == [e.to_dict() for e in e2]
    assert (u.last_weather.temperature == r.last_weather.temperature).all()
    assert any(e.type == "new_year" for e in e1)


def test_child_constants_vary():
    p = UniverseConstants()
    ch = p.mutate(Rng(5))
    assert ch != p and abs(ch.gravity / p.gravity - 1) <= 0.05 + 1e-9
