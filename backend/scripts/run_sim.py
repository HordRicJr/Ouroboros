"""Simulation rapide pour observer la dynamique : python scripts/run_sim.py [années] [seed]"""
import sys
import time

from univers.engine import Universe

years = int(sys.argv[1]) if len(sys.argv) > 1 else 20
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
u = Universe("sim", seed, start_year=2015)
t0 = time.time()
for y in range(years):
    ev = u.step(365)
    kinds = {}
    for e in ev:
        kinds[e.type] = kinds.get(e.type, 0) + 1
    pops = {s["name"]: round(s["population"]) for s in u.eco.stats()}
    alive = len(u.people.alive_persons())
    print(y + 1, pops, "suivis:", alive, {k: v for k, v in kinds.items() if k in ("speciation", "extinction")})
print(f"{time.time() - t0:.1f}s")
