"""M05 - Persistance : sauvegarde/reprise (snapshots) + journal d'événements.

Deux implémentations : PostgresStore (production AWS RDS) et MemoryStore (tests).
"""
from __future__ import annotations

import json
from typing import Protocol

from .engine import Universe
from .events import Event


class Store(Protocol):
    def init(self) -> None: ...
    def exists(self, universe_id: str) -> bool: ...
    def save(self, u: Universe) -> None: ...
    def load(self, universe_id: str, tick: int | None = None) -> Universe: ...
    def append_events(self, universe_id: str, events: list[Event]) -> None: ...
    def events(self, universe_id: str, since_tick: int = 0, until_tick: int | None = None,
               limit: int = 1000) -> list[Event]: ...
    def list_universes(self) -> list[dict]: ...


class MemoryStore:
    def __init__(self):
        self._snaps: dict[str, dict[int, bytes]] = {}
        self._events: dict[str, list[Event]] = {}

    def init(self) -> None: ...

    def exists(self, universe_id: str) -> bool:
        return universe_id in self._snaps

    def save(self, u: Universe) -> None:
        self._snaps.setdefault(u.id, {})[u.tick] = u.snapshot()

    def load(self, universe_id: str, tick: int | None = None) -> Universe:
        snaps = self._snaps[universe_id]
        t = max(snaps) if tick is None else max(k for k in snaps if k <= tick)
        return Universe.from_snapshot(snaps[t])

    def append_events(self, universe_id: str, events: list[Event]) -> None:
        self._events.setdefault(universe_id, []).extend(events)

    def events(self, universe_id, since_tick=0, until_tick=None, limit=1000):
        ev = [e for e in self._events.get(universe_id, [])
              if e.tick >= since_tick and (until_tick is None or e.tick <= until_tick)]
        return ev[:limit]

    def list_universes(self) -> list[dict]:
        return [{"id": k, "snapshots": sorted(v)} for k, v in self._snaps.items()]


SCHEMA = """
CREATE TABLE IF NOT EXISTS universes (
    id TEXT PRIMARY KEY, seed BIGINT NOT NULL, parent_id TEXT, constants JSONB NOT NULL,
    start_year INT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS snapshots (
    universe_id TEXT NOT NULL REFERENCES universes(id) ON DELETE CASCADE,
    tick BIGINT NOT NULL, data BYTEA NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (universe_id, tick)
);
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    universe_id TEXT NOT NULL REFERENCES universes(id) ON DELETE CASCADE,
    tick BIGINT NOT NULL, type TEXT NOT NULL, payload JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS events_u_tick ON events (universe_id, tick);
"""


class PostgresStore:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def _conn(self):
        import psycopg
        return psycopg.connect(self.dsn)

    def init(self) -> None:
        with self._conn() as c:
            c.execute(SCHEMA)

    def exists(self, universe_id: str) -> bool:
        with self._conn() as c:
            row = c.execute("SELECT 1 FROM universes WHERE id=%s", (universe_id,)).fetchone()
            return row is not None

    def save(self, u: Universe) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO universes (id, seed, parent_id, constants, start_year) VALUES (%s,%s,%s,%s,%s) "
                "ON CONFLICT (id) DO NOTHING",
                (u.id, u.seed, u.parent_id, json.dumps(u.consts.to_dict()), u.start_year))
            c.execute(
                "INSERT INTO snapshots (universe_id, tick, data) VALUES (%s,%s,%s) "
                "ON CONFLICT (universe_id, tick) DO UPDATE SET data = EXCLUDED.data",
                (u.id, u.tick, u.snapshot()))

    def load(self, universe_id: str, tick: int | None = None) -> Universe:
        with self._conn() as c:
            if tick is None:
                row = c.execute("SELECT data FROM snapshots WHERE universe_id=%s ORDER BY tick DESC LIMIT 1",
                                (universe_id,)).fetchone()
            else:
                row = c.execute("SELECT data FROM snapshots WHERE universe_id=%s AND tick<=%s "
                                "ORDER BY tick DESC LIMIT 1", (universe_id, tick)).fetchone()
        if not row:
            raise KeyError(universe_id)
        return Universe.from_snapshot(bytes(row[0]))

    def append_events(self, universe_id: str, events: list[Event]) -> None:
        if not events:
            return
        with self._conn() as c, c.cursor() as cur:
            cur.executemany("INSERT INTO events (universe_id, tick, type, payload) VALUES (%s,%s,%s,%s)",
                            [(universe_id, e.tick, e.type, json.dumps(e.payload)) for e in events])

    def events(self, universe_id, since_tick=0, until_tick=None, limit=1000):
        q = "SELECT tick, type, payload FROM events WHERE universe_id=%s AND tick>=%s"
        args: list = [universe_id, since_tick]
        if until_tick is not None:
            q += " AND tick<=%s"
            args.append(until_tick)
        q += " ORDER BY id LIMIT %s"
        args.append(limit)
        with self._conn() as c:
            return [Event(t, ty, p) for t, ty, p in c.execute(q, args).fetchall()]

    def list_universes(self) -> list[dict]:
        with self._conn() as c:
            return [{"id": i, "seed": s, "parent_id": p, "start_year": y}
                    for i, s, p, y in c.execute("SELECT id, seed, parent_id, start_year FROM universes").fetchall()]
