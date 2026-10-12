import numpy as np
from univers.engine import Universe
from univers.ecology import suitability
from univers.genetics import I_COLD, I_HEAT

u = Universe("d", 42)
e = u.eco
h = [s.id for s in e.species if s.kind == "human"][0]
print("camps", e.human_cells, "temp", [round(float(u.world.mean_temp[c]), 1) for c in e.human_cells])
for week in range(0, 53):
    u.step(7)
    if week % 8 == 0:
        y, x = e.human_cells[0]
        w = u.last_weather
        su = suitability(e.T[h, I_COLD], e.T[h, I_HEAT], w.temperature)[y, x]
        print(week, "N cell", np.round(e.N[h, :, y, x], 2), "suit", round(float(su), 2),
              "feff", round(float(e.feff[h, y, x]), 2), "tot", round(float(e.N[h].sum()), 1),
              "plants", round(float(e.N[0, :, y, x].sum())), "herb", round(float(e.N[2, :, y, x].sum()), 1))
