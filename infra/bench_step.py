import time
from engine.engine import Universe

u = Universe("bench", 1)
t0 = time.perf_counter()
u.step(1)
print("cold_step_ms", round((time.perf_counter() - t0) * 1000, 1))
t0 = time.perf_counter()
for _ in range(20):
    u.step(1)
print("avg20_ms", round((time.perf_counter() - t0) * 1000 / 20, 1))
t0 = time.perf_counter()
info = u.info()
print("info_ms", round((time.perf_counter() - t0) * 1000, 1), "pop", info["population"])
