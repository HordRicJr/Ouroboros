"""M10/M11 - Sociétés, Clans, Cultures & Croyances Émergentes.

Ce module gère la structure sociale des humains simulés :
- Regroupement en clans/tribus géolocalisés avec chefferies et territoires
- Récits cosmogoniques, totems sacrés et tabous culturels
- Dérive culturelle et transmission des traditions
- Dynamique territoriale : fissions lors de surpopulation, alliances et rivalités
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from .events import Event
from .people import CultureRules

if TYPE_CHECKING:
    from .ecology import Ecosystem
    from .people import People, Person
    from .rng import Rng
    from .worldmap import WorldMap

# Totems et éléments cosmogoniques pour génération émergente
_TOTEMS = [
    "Loup Gris", "Faucon d'Or", "Ours Noir", "Grand Cerf", "Vipère Rouge",
    "Bison des Plaines", "Aigle Royal", "Sanglier Écarlate", "Corbeau Sage",
    "Lynx des Ombres", "Truite d'Argent", "Grand Chêne Ancestral"
]

_TERRITORY_EPITHETS = [
    "du Soleil Levant", "de la Rivière Claire", "des Terres Fertiles",
    "de la Forêt Profonde", "des Collines Brumeuses", "des Roches Anciennes",
    "du Vent du Nord", "des Rives Paisibles"
]

_COSMOGONIES = [
    "Nés du souffle originel des grands arbres et de la sève éternelle.",
    "Façonnés dans l'argile des rivières sacrées par les ancêtres des étoiles.",
    "Sortis de la matrice rocheuse de la Première Montagne lors du Grand Fracas.",
    "Guidés depuis les brumes par le regard vigilant du Totem fondateur.",
    "Descendants directs du feu primordial qui réchauffa la première nuit.",
]

_TABOOS = [
    "Interdit formel de souiller les sources d'eau vive.",
    "Chasser le totem du clan attire la malédiction des esprits.",
    "Les récoltes de l'automne doivent être partagées avec les anciens.",
    "Nul ne doit couper un arbre porteur de marques sacrées.",
    "Honorer les défunts par trois veillées silencieuses sous la lune.",
]


@dataclass
class Clan:
    id: int
    name: str
    totem: str
    settlement_cell: tuple[int, int]
    territory_cells: list[tuple[int, int]]
    leader_id: int | None = None
    matriarch_id: int | None = None
    member_ids: list[int] = field(default_factory=list)
    cosmogony: str = ""
    taboos: list[str] = field(default_factory=list)
    culture_name: str = "ancestrale"
    language_id: int = 1
    settlement_name: str = "Campement Sacré"
    relations: dict[int, float] = field(default_factory=dict)  # clan_id -> score (-1.0 à +1.0)
    founded_year: int = 0

    @property
    def population_size(self) -> int:
        return len(self.member_ids)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["settlement_cell"] = list(self.settlement_cell)
        d["territory_cells"] = [list(c) for c in self.territory_cells]
        d["relations"] = {str(k): v for k, v in self.relations.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Clan:
        d = dict(d)
        d["settlement_cell"] = tuple(d["settlement_cell"])
        d["territory_cells"] = [tuple(c) for c in d["territory_cells"]]
        d["relations"] = {int(k): float(v) for k, v in d.get("relations", {}).items()}
        return cls(**d)


class Society:
    """Gestionnaire de la société, des clans et de la dérive culturelle."""

    def __init__(self):
        self.clans: dict[int, Clan] = {}
        self.next_clan_id = 1
        self.cultures: dict[str, CultureRules] = {"ancestrale": CultureRules()}

    def get_person_clan(self, person_id: int) -> Clan | None:
        for c in self.clans.values():
            if person_id in c.member_ids:
                return c
        return None

    def _elect_leaders(self, clan: Clan, people: People, tick: int):
        """Désigne ou remplace le chef et la matriarche du clan."""
        alive_members = [people.persons[pid] for pid in clan.member_ids if pid in people.persons and people.persons[pid].alive]
        if not alive_members:
            clan.leader_id = None
            clan.matriarch_id = None
            return

        males = [p for p in alive_members if p.sex == "M"]
        females = [p for p in alive_members if p.sex == "F"]

        # Chef (homme le plus âgé ou notable existant)
        if clan.leader_id is None or clan.leader_id not in people.persons or not people.persons[clan.leader_id].alive:
            candidates = males or alive_members
            eldest = max(candidates, key=lambda p: people.age_years(p, tick))
            clan.leader_id = eldest.id
            eldest.notable = True

        # Matriarche (femme la plus âgée ou notable existante)
        if clan.matriarch_id is None or clan.matriarch_id not in people.persons or not people.persons[clan.matriarch_id].alive:
            candidates = females or alive_members
            eldest_f = max(candidates, key=lambda p: people.age_years(p, tick))
            clan.matriarch_id = eldest_f.id
            eldest_f.notable = True

    @classmethod
    def genesis(cls, people: People, eco: Ecosystem, rng: Rng, world: WorldMap, tick: int = 0) -> Society:
        """Crée la structure sociale initiale à partir des campements écologiques."""
        soc = cls()
        soc.cultures = dict(people.cultures)
        g = rng.gen("society-genesis")

        # Grouper les personnes vivantes par cellule de campement
        camp_members: dict[tuple[int, int], list[Person]] = {}
        for p in people.alive_persons():
            camp_members.setdefault(p.cell, []).append(p)

        for cell, members in sorted(camp_members.items(), key=lambda item: item[0]):
            totem = str(g.choice(_TOTEMS))
            epithet = str(g.choice(_TERRITORY_EPITHETS))
            clan_name = f"Clan du {totem} {epithet}"
            cosmo = str(g.choice(_COSMOGONIES))
            taboo = [str(g.choice(_TABOOS))]

            # Territoire immédiat : la cellule du camp et les voisines terrestres directes
            y, x = cell
            territory: list[tuple[int, int]] = [cell]
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < world.height and 0 <= nx < world.width and world.is_land[ny, nx] and (ny, nx) != cell:
                        territory.append((ny, nx))

            clan = Clan(
                id=soc.next_clan_id,
                name=clan_name,
                totem=totem,
                settlement_cell=cell,
                territory_cells=territory,
                member_ids=[p.id for p in members],
                cosmogony=cosmo,
                taboos=taboo,
                culture_name="ancestrale",
                language_id=1,
                settlement_name=f"Havre-{totem.split()[0]}",
                founded_year=0,
            )
            soc.clans[clan.id] = clan
            soc.next_clan_id += 1
            soc._elect_leaders(clan, people, tick)

        # Initialiser les relations neutres entre clans
        clan_ids = list(soc.clans.keys())
        for i in clan_ids:
            for j in clan_ids:
                if i != j:
                    soc.clans[i].relations[j] = 0.2  # Entente amicale neutre par défaut

        return soc

    def step(self, tick: int, year: int, people: People, eco: Ecosystem, rng: Rng,
             world: WorldMap, is_new_year: bool = False) -> list[Event]:
        """Évolution annuelle et événementielle de la société."""
        events: list[Event] = []
        g = rng.gen("society", tick)

        # 1. Mise à jour des effectifs vivants et succession des chefs
        for clan in list(self.clans.values()):
            alive_pids = [pid for pid in clan.member_ids if pid in people.persons and people.persons[pid].alive]
            clan.member_ids = alive_pids

            if not alive_pids:
                # Clan éteint
                continue

            old_leader = clan.leader_id
            self._elect_leaders(clan, people, tick)
            if old_leader is not None and old_leader != clan.leader_id and clan.leader_id is not None:
                new_leader_p = people.persons[clan.leader_id]
                events.append(Event(tick, "clan_leadership", {
                    "clan_id": clan.id,
                    "clan_name": clan.name,
                    "new_leader_id": clan.leader_id,
                    "new_leader_name": new_leader_p.name,
                    "reason": "succession",
                }))

        # 2. Rattachement des nouveaux-nés au clan de leur mère ou de leur père
        for p in people.alive_persons():
            if self.get_person_clan(p.id) is None:
                mother_clan = self.get_person_clan(p.mother_id) if p.mother_id else None
                father_clan = self.get_person_clan(p.father_id) if p.father_id else None
                chosen_clan = mother_clan or father_clan
                if chosen_clan:
                    chosen_clan.member_ids.append(p.id)
                elif self.clans:
                    # Trouver le clan le plus proche de sa cellule
                    closest = min(self.clans.values(), key=lambda c: (c.settlement_cell[0] - p.cell[0])**2 + (c.settlement_cell[1] - p.cell[1])**2)
                    closest.member_ids.append(p.id)

        # 3. Actions annuelles : Dérive culturelle, fissions et diplomatie
        if is_new_year:
            events.extend(self._yearly_cultural_drift(tick, year, g))
            events.extend(self._check_fissions(tick, year, people, eco, world, g))
            events.extend(self._yearly_diplomacy(tick, year, eco, g))

        return events

    def _yearly_cultural_drift(self, tick: int, year: int, g: np.random.Generator) -> list[Event]:
        """Dérive culturelle annuelle : mutation lente de croyances et tabous."""
        events: list[Event] = []
        for clan in self.clans.values():
            if not clan.member_ids:
                continue

            # Probabilité de 10% par an d'adopter un nouveau tabou ou faire évoluer une coutume
            if g.random() < 0.10:
                available = [t for t in _TABOOS if t not in clan.taboos]
                if available:
                    new_taboo = str(g.choice(available))
                    clan.taboos.append(new_taboo)
                    events.append(Event(tick, "cultural_drift", {
                        "clan_id": clan.id,
                        "clan_name": clan.name,
                        "year": year,
                        "taboo_adopted": new_taboo,
                    }))
        return events

    def _check_fissions(self, tick: int, year: int, people: People, eco: Ecosystem,
                        world: WorldMap, g: np.random.Generator) -> list[Event]:
        """Scission d'un clan si surpopulation par rapport à la capacité locale."""
        events: list[Event] = []
        for clan in list(self.clans.values()):
            members = [people.persons[pid] for pid in clan.member_ids if pid in people.persons and people.persons[pid].alive]
            # Seuil de surpopulation clanique : plus de 24 membres sur un campement
            if len(members) >= 24:
                # Chercher une terre habitable adjacente libre de tout campement
                y, x = clan.settlement_cell
                candidate_cells = []
                occupied = {c.settlement_cell for c in self.clans.values()}
                for dy in (-1, 0, 1, -2, 2):
                    for dx in (-1, 0, 1, -2, 2):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < world.height and 0 <= nx < world.width and world.is_land[ny, nx] and (ny, nx) not in occupied:
                            candidate_cells.append((ny, nx))

                if candidate_cells:
                    new_cell = candidate_cells[int(g.integers(0, len(candidate_cells)))]
                    # La moitié des jeunes adultes partent fonder le nouveau clan
                    migrants = [p for p in members if 16 <= people.age_years(p, tick) <= 35]
                    if len(migrants) >= 4:
                        split_count = len(migrants) // 2
                        leaving_members = migrants[:split_count]
                        leaving_ids = {p.id for p in leaving_members}

                        # Retirer du clan d'origine
                        clan.member_ids = [pid for pid in clan.member_ids if pid not in leaving_ids]

                        # Déplacer physiquement les pionniers
                        for p in leaving_members:
                            p.cell = new_cell

                        totem = str(g.choice(_TOTEMS))
                        new_name = f"Clan des Fils de {clan.totem}"
                        cosmo = f"Nés de la scission du {clan.name} lors de la Grande Abondance."
                        new_clan = Clan(
                            id=self.next_clan_id,
                            name=new_name,
                            totem=totem,
                            settlement_cell=new_cell,
                            territory_cells=[new_cell],
                            member_ids=list(leaving_ids),
                            cosmogony=cosmo,
                            taboos=list(clan.taboos),
                            culture_name=clan.culture_name,
                            founded_year=year,
                        )
                        self.clans[new_clan.id] = new_clan
                        self.next_clan_id += 1
                        self._elect_leaders(new_clan, people, tick)

                        # Enregistrer la nouvelle cellule dans l'écosystème pour cueillette/chasse
                        if new_cell not in eco.human_cells:
                            eco.human_cells.append(new_cell)

                        # Relations fraternelles fortes au départ entre la métropole et la colonie
                        clan.relations[new_clan.id] = 0.8
                        new_clan.relations[clan.id] = 0.8

                        events.append(Event(tick, "clan_split", {
                            "parent_clan_id": clan.id,
                            "parent_clan_name": clan.name,
                            "new_clan_id": new_clan.id,
                            "new_clan_name": new_clan.name,
                            "pioneers_count": len(leaving_members),
                            "new_cell": list(new_cell),
                            "year": year,
                        }))
        return events

    def _yearly_diplomacy(self, tick: int, year: int, eco: Ecosystem, g: np.random.Generator) -> list[Event]:
        """Ajustement des relations diplomatiques selon l'abondance et la pression écologique."""
        events: list[Event] = []
        clan_ids = [cid for cid, c in self.clans.items() if c.member_ids]

        for i in range(len(clan_ids)):
            c1 = self.clans[clan_ids[i]]
            y1, x1 = c1.settlement_cell
            f1 = float(eco.feff[0, y1, x1]) if len(eco.feff) > 0 else 1.0

            for j in range(i + 1, len(clan_ids)):
                c2 = self.clans[clan_ids[j]]
                y2, x2 = c2.settlement_cell
                f2 = float(eco.feff[0, y2, x2]) if len(eco.feff) > 0 else 1.0

                current_rel = c1.relations.get(c2.id, 0.0)

                # Si disette alimentaire généralisée : rivalité et frictions pour les ressources
                if f1 < 0.45 or f2 < 0.45:
                    delta = -0.15 * float(g.uniform(0.5, 1.5))
                    new_rel = max(-1.0, current_rel + delta)
                    if new_rel < -0.4 and current_rel >= -0.4:
                        events.append(Event(tick, "clan_friction", {
                            "clan1_id": c1.id,
                            "clan1_name": c1.name,
                            "clan2_id": c2.id,
                            "clan2_name": c2.name,
                            "year": year,
                            "reason": "disette alimentaire et tension territoriale",
                        }))
                else:
                    # En période d'abondance : commerce de troc et consolidation de paix
                    delta = 0.08 * float(g.uniform(0.5, 1.2))
                    new_rel = min(1.0, current_rel + delta)
                    if new_rel > 0.6 and current_rel <= 0.6:
                        events.append(Event(tick, "clan_alliance", {
                            "clan1_id": c1.id,
                            "clan1_name": c1.name,
                            "clan2_id": c2.id,
                            "clan2_name": c2.name,
                            "year": year,
                            "reason": "pacte de partage et fraternité",
                        }))

                c1.relations[c2.id] = round(new_rel, 3)
                c2.relations[c1.id] = round(new_rel, 3)

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "clans": [c.to_dict() for c in self.clans.values()],
            "next_clan_id": self.next_clan_id,
            "cultures": {k: asdict(v) for k, v in self.cultures.items()},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Society:
        soc = cls()
        soc.next_clan_id = d.get("next_clan_id", 1)
        soc.clans = {c["id"]: Clan.from_dict(c) for c in d.get("clans", [])}
        soc.cultures = {k: CultureRules(**v) for k, v in d.get("cultures", {}).items()}
        return soc
