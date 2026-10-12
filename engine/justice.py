"""M20 - Lois, Codes de Justice, Rangs Sociaux & Stratification Politique.

Ce module modélise l'émergence des institutions judiciaires et politiques :
- Rangs et castes sociales : Chefs suprêmes, Chamanes/Prêtres, Guerriers d'élite, Artisans, Laboureurs
- Édiction de codes de lois coutumières (Lex Talionis, compensation en bétail, bannissement, ordalie)
- Jugements et ordalies pour les délits (vols, homicides, rupture de tabou)
- Cohésion sociale et risque d'insurrection / révolte interne
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .people import People
    from .rng import Rng
    from .society import Society

SOCIAL_RANKS = [
    "Chef Suprême",
    "Guerrier d'Élite",
    "Chamane & Gardien des Rites",
    "Maître Artisan",
    "Chasseur-Cueilleur",
    "Banni / Hors-la-loi",
]

CUSTOMARY_LAWS = [
    ("Loi du Talion", "Œil pour œil : tout préjudice physique est rendu à l'agresseur."),
    ("Wergild (Compensation)", "Le sang versé ou le vol est racheté par un tribut de peaux et de vivres."),
    ("Le Grand Bannissement", "Quiconque brise le tabou sacré du clan est exilé dans les terres sauvages."),
    ("L'Ordalie du Feu", "L'innocence est prouvée en portant une pierre chauffée au foyer sans brûlure grave."),
]


@dataclass
class LegalCode:
    clan_id: int
    law_name: str
    law_principle: str
    enacted_year: int
    strictness: float = 0.5  # 0.0 (permissif) à 1.0 (inflexible)

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
    verdict: str  # "acquitté", "amende_wergild", "bannissement", "châtiment_corporel"
    punishment_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Trial:
        return cls(**d)


class JusticeSystem:
    """Gestionnaire de la justice, des rangs sociaux et des ordalies."""

    def __init__(self):
        self.legal_codes: dict[int, LegalCode] = {}  # clan_id -> LegalCode
        self.trials: list[Trial] = []
        self.person_ranks: dict[int, str] = {}       # person_id -> Social Rank
        self.next_trial_id = 1

    def assign_ranks(self, society: Society, people: People):
        """Met à jour les rangs sociaux selon le rôle et le prestige de chaque individu."""
        for clan in society.clans.values():
            for pid in clan.member_ids:
                p = people.persons.get(pid)
                if not p or not p.alive:
                    continue

                if pid == clan.leader_id:
                    self.person_ranks[pid] = "Chef Suprême"
                elif pid == clan.matriarch_id:
                    self.person_ranks[pid] = "Chamane & Gardien des Rites"
                elif p.notable:
                    self.person_ranks[pid] = "Guerrier d'Élite" if p.sex == "M" else "Maître Artisan"
                else:
                    self.person_ranks[pid] = "Chasseur-Cueilleur"

    def step(self, tick: int, year: int, society: Society, people: People, rng: Rng) -> list[Event]:
        """Évolution annuelle du système judiciaire et tenue des ordalies."""
        events: list[Event] = []
        g = rng.gen("justice", tick)

        self.assign_ranks(society, people)

        # 1. Édiction de lois pour les clans sédentaires ou de plus de 10 membres
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

        # 2. Litiges et ordalies (tirage rare annuel : 15% de chance par clan ayant des lois)
        for clan in society.clans.values():
            if clan.id not in self.legal_codes or not clan.member_ids:
                continue

            if g.random() < 0.15:
                accused_id = int(g.choice(clan.member_ids))
                accused = people.persons.get(accused_id)
                if not accused or not accused.alive:
                    continue

                crime = str(g.choice([
                    "Vol de viandes séchées dans le grenier commun",
                    "Rupture délibérée du tabou sacré du clan",
                    "Dispute violente ayant blessé un ancien",
                    "Refus d'obéissance au chef de clan",
                ]))

                # Délibération selon la sévérité du code de loi
                code = self.legal_codes[clan.id]
                roll = float(g.random())
                if roll < 0.30:
                    verdict = "acquitté"
                    punishment = "Reconnu innocent par l'ordalie des ancêtres."
                elif roll < 0.70:
                    verdict = "amende_wergild"
                    punishment = "Doit payer 5 peaux tannées et servir le clan aux corvées."
                else:
                    verdict = "bannissement"
                    punishment = "Banni du territoire du clan pour trois hivers."
                    self.person_ranks[accused.id] = "Banni / Hors-la-loi"

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
            "next_trial_id": self.next_trial_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> JusticeSystem:
        js = cls()
        js.next_trial_id = d.get("next_trial_id", 1)
        js.legal_codes = {c["clan_id"]: LegalCode.from_dict(c) for c in d.get("legal_codes", [])}
        js.trials = [Trial.from_dict(t) for t in d.get("trials", [])]
        js.person_ranks = {int(k): v for k, v in d.get("person_ranks", {}).items()}
        return js
