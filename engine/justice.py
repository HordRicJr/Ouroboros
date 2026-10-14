"""Lois coutumières et litiges — sans table de grades imposée.

Les rangs sociaux ne sont plus assignés par le code (Priorité 1A).
Le statut vient du graphe de déférence (`social_graph`). Ce module enregistre
seulement des faits : codes adoptés, procès, bannissements.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .people import People
    from .rng import Rng
    from .society import Society

# Principes génériques (contenu variable) — pas de titres politiques.
CUSTOMARY_LAWS = [
    ("Compensation mutuelle", "Un préjudice est racheté par un tribut de peaux et de vivres."),
    ("Éloignement du camp", "Quiconque brise une coutume partagée peut être tenu à l'écart."),
    ("Épreuve du foyer", "Un différend peut être tranché par une épreuve acceptée par les présents."),
    ("Restitution", "Ce qui a été pris doit être rendu ou remplacé."),
]


@dataclass
class LegalCode:
    clan_id: int
    law_name: str
    law_principle: str
    enacted_year: int
    strictness: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LegalCode:
        return cls(**d)


@dataclass
class Trial:
    id: int
    tick: int
    year: int
    clan_id: int
    accused_id: int
    accused_name: str
    crime: str
    verdict: str
    punishment_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Trial:
        return cls(**d)


class JusticeSystem:
    """Faits judiciaires sans hiérarchie préétablie."""

    def __init__(self):
        self.legal_codes: dict[int, LegalCode] = {}
        self.trials: list[Trial] = []
        # Conservé pour compatibilité API / snapshots : statut factuel seulement
        # (ex. "écarté du camp"), jamais une table Chef/Chamane/Juge.
        self.person_ranks: dict[int, str] = {}
        self.next_trial_id = 1
        self.banished_ids: set[int] = set()

    def assign_ranks(self, society: Society, people: People):
        """Ne fixe plus de grades. Nettoie les anciens titres scriptés s'ils existent."""
        scripted = {
            "Chef Suprême",
            "Guerrier d'Élite",
            "Chamane & Gardien des Rites",
            "Maître Artisan",
            "Chasseur-Cueilleur",
            "Banni / Hors-la-loi",
        }
        for pid in list(self.person_ranks.keys()):
            if self.person_ranks[pid] in scripted:
                if pid in self.banished_ids:
                    self.person_ranks[pid] = "écarté du camp"
                else:
                    del self.person_ranks[pid]

    def step(self, tick: int, year: int, society: Society, people: People, rng: Rng) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("justice", tick)

        self.assign_ranks(society, people)

        # Adoption d'une coutume écrite si le groupe est assez large (fait, pas titre)
        for clan in society.clans.values():
            if clan.id not in self.legal_codes and len(clan.member_ids) >= 10:
                law_title, law_desc = CUSTOMARY_LAWS[int(g.integers(0, len(CUSTOMARY_LAWS)))]
                code = LegalCode(
                    clan_id=clan.id,
                    law_name=law_title,
                    law_principle=law_desc,
                    enacted_year=year,
                    strictness=float(g.uniform(0.4, 0.9)),
                )
                self.legal_codes[clan.id] = code
                events.append(Event(tick, "law_enacted", {
                    "clan_id": clan.id,
                    "clan_name": clan.name,
                    "law_name": code.law_name,
                    "principle": code.law_principle,
                    "year": year,
                }))

        for clan in society.clans.values():
            if clan.id not in self.legal_codes or not clan.member_ids:
                continue

            if g.random() < 0.15:
                accused_id = int(g.choice(clan.member_ids))
                accused = people.persons.get(accused_id)
                if not accused or not accused.alive:
                    continue

                crime = str(g.choice([
                    "Prise de vivres du stock commun",
                    "Transgression d'une coutume du camp",
                    "Altercation ayant blessé un autre membre",
                    "Refus de contribuer à une tâche partagée",
                ]))

                code = self.legal_codes[clan.id]
                roll = float(g.random())
                if roll < 0.30:
                    verdict = "acquitté"
                    punishment = "Reconnu innocent par les présents."
                elif roll < 0.70:
                    verdict = "amende_wergild"
                    punishment = "Doit restituer peaux et servir aux corvées."
                else:
                    verdict = "bannissement"
                    punishment = "Écarté du territoire du camp pour trois hivers."
                    self.banished_ids.add(accused.id)
                    self.person_ranks[accused.id] = "écarté du camp"

                trial = Trial(
                    id=self.next_trial_id,
                    tick=tick,
                    year=year,
                    clan_id=clan.id,
                    accused_id=accused.id,
                    accused_name=accused.name,
                    crime=crime,
                    verdict=verdict,
                    punishment_text=punishment,
                )
                self.trials.append(trial)
                self.next_trial_id += 1

                events.append(Event(tick, "trial_held", {
                    "trial_id": trial.id,
                    "clan_id": clan.id,
                    "clan_name": clan.name,
                    "accused_id": accused.id,
                    "accused_name": accused.name,
                    "crime": trial.crime,
                    "verdict": trial.verdict,
                    "punishment": trial.punishment_text,
                    "year": year,
                }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "legal_codes": [c.to_dict() for c in self.legal_codes.values()],
            "trials": [t.to_dict() for t in self.trials],
            "person_ranks": {str(k): v for k, v in self.person_ranks.items()},
            "banished_ids": list(self.banished_ids),
            "next_trial_id": self.next_trial_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> JusticeSystem:
        js = cls()
        js.next_trial_id = d.get("next_trial_id", 1)
        js.legal_codes = {c["clan_id"]: LegalCode.from_dict(c) for c in d.get("legal_codes", [])}
        js.trials = [Trial.from_dict(t) for t in d.get("trials", [])]
        js.person_ranks = {int(k): v for k, v in d.get("person_ranks", {}).items()}
        js.banished_ids = set(int(x) for x in d.get("banished_ids", []))
        return js
