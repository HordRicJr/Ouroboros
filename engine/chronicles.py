"""M15 - Récits Mythologiques, Bardes & Chroniques Épiques.

Ce module consigne l'histoire vivante et la mémoire collective du monde :
- Chroniques épiques générées automatiquement à partir des faits marquants
- Récits héroïques et poèmes de bardes pour les victoires, traités et découvertes
- Registre historique consultable par les notables et via l'API
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .events import Event


@dataclass
class ChronicleEntry:
    id: int
    tick: int
    year: int
    category: str        # "fondation", "guerre", "paix", "invention", "famine", "alliance"
    title: str
    narrative: str
    involved_clans: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChronicleEntry:
        return cls(**d)


class ChronicleKeeper:
    """Gardien des chroniques et conteur des mémoires de l'univers."""

    def __init__(self):
        self.entries: list[ChronicleEntry] = []
        self.next_entry_id = 1

    def record(self, tick: int, year: int, category: str, title: str,
               narrative: str, clans: list[str] | None = None) -> ChronicleEntry:
        entry = ChronicleEntry(
            id=self.next_entry_id,
            tick=tick,
            year=year,
            category=category,
            title=title,
            narrative=narrative,
            involved_clans=clans or [],
        )
        self.entries.append(entry)
        self.next_entry_id += 1
        return entry

    def record_from_events(self, events: list[Event], year: int, tick: int):
        """Transforme les événements majeurs de la simulation en récits épiques."""
        for ev in events:
            if ev.type == "war_declared":
                c1 = ev.payload.get("attacker_clan_name", "Un clan")
                c2 = ev.payload.get("defender_clan_name", "un autre clan")
                self.record(
                    tick, year, "guerre",
                    f"Le Tambour de Guerre : {c1} contre {c2}",
                    f"En l'an {year}, le ciel s'assombrit lorsque les guerriers du {c1} marchèrent contre le {c2}. Les tambours résonnèrent dans les vallées.",
                    [c1, c2]
                )
            elif ev.type == "peace_treaty":
                c1 = ev.payload.get("clan1_name", "Un clan")
                c2 = ev.payload.get("clan2_name", "un autre clan")
                self.record(
                    tick, year, "paix",
                    f"Le Pacte du Calumet : Réconciliation de {c1} et {c2}",
                    f"Après de rudes combats, les chefs de {c1} et {c2} partagèrent la fumée sacrée et jurèrent de respecter les frontières ancestrales.",
                    [c1, c2]
                )
            elif ev.type == "tech_discovered":
                cname = ev.payload.get("clan_name", "Le peuple")
                tname = ev.payload.get("tech_name", "une invention")
                desc = ev.payload.get("description", "")
                self.record(
                    tick, year, "invention",
                    f"L'Étincelle du Génie : {cname} découvre {tname}",
                    f"Inspirés par la nature et les nécessités de la survie, les anciens du {cname} mirent au point {tname}. {desc}",
                    [cname]
                )
            elif ev.type == "clan_split":
                parent = ev.payload.get("parent_clan_name", "Clan d'origine")
                child = ev.payload.get("new_clan_name", "Nouveau clan")
                self.record(
                    tick, year, "fondation",
                    f"La Grande Marche des Pionniers : Naissance du {child}",
                    f"Face à l'étroitesse des terres nourricières, de vaillants pionniers quittèrent le {parent} pour allumer de nouveaux feux et fonder le {child}.",
                    [parent, child]
                )

    def recent_tales(self, limit: int = 10) -> list[ChronicleEntry]:
        return self.entries[-limit:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "next_entry_id": self.next_entry_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChronicleKeeper:
        ck = cls()
        ck.next_entry_id = d.get("next_entry_id", 1)
        ck.entries = [ChronicleEntry.from_dict(e) for e in d.get("entries", [])]
        return ck
