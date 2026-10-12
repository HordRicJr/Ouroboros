"""M13 - Technologies Primitives, Innovations Émergentes & Économie de Troc.

Ce module modélise le développement technique et matériel des sociétés primitives :
- Arbre d'innovations préhistoriques (feu, taille du silex, remèdes, poterie, arc...)
- Découverte fortuite et inspirée selon l'environnement géographique (biome, rivières)
- Économie de troc (échange de matières premières et surplus entre clans amis)
- Diffusion technologique inter-clans par contact commercial et matrimonial
- Effets directs sur l'efficacité alimentaire (feff) et la résilience démographique
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .rng import Rng
    from .society import Society
    from .worldmap import WorldMap


@dataclass
class TechDefinition:
    id: str
    name: str
    category: str        # "chasse", "survie", "artisanat", "nourriture", "transport"
    prerequisites: list[str] = field(default_factory=list)
    description: str = ""
    food_bonus: float = 0.05
    health_bonus: float = 0.05
    required_biomes: list[int] = field(default_factory=list)  # biomes favorisant la découverte
    requires_river: bool = False


TECH_CATALOG: dict[str, TechDefinition] = {
    "flint_knapping": TechDefinition(
        id="flint_knapping",
        name="Taille du silex",
        category="chasse",
        description="Façonnage de lames tranchantes pour couper la viande et préparer le gibier.",
        food_bonus=0.10,
        health_bonus=0.02,
    ),
    "fire_mastery": TechDefinition(
        id="fire_mastery",
        name="Maîtrise du feu sacré",
        category="survie",
        description="Allumage et conservation du foyer. Chasse les bêtes, cuit les aliments et réchauffe l'hiver.",
        food_bonus=0.15,
        health_bonus=0.15,
    ),
    "herbal_remedies": TechDefinition(
        id="herbal_remedies",
        name="Remèdes par les plantes",
        category="survie",
        description="Connaissance des baies curatives, écorces antalgiques et onguents cicatrisants.",
        food_bonus=0.02,
        health_bonus=0.20,
    ),
    "leather_tanning": TechDefinition(
        id="leather_tanning",
        name="Tannage des peaux",
        category="artisanat",
        prerequisites=["flint_knapping"],
        description="Transformation des peaux de bêtes en manteaux chauds et récipients souples.",
        food_bonus=0.05,
        health_bonus=0.10,
    ),
    "bow_and_arrow": TechDefinition(
        id="bow_and_arrow",
        name="Arc et flèches",
        category="chasse",
        prerequisites=["flint_knapping"],
        description="Arme de trait permettant de frapper le gros gibier à longue distance.",
        food_bonus=0.20,
        health_bonus=0.05,
    ),
    "fish_traps": TechDefinition(
        id="fish_traps",
        name="Nasses et harpons",
        category="nourriture",
        prerequisites=["flint_knapping"],
        description="Piégeage de poissons dans les cours d'eau et baies côtières.",
        food_bonus=0.15,
        health_bonus=0.05,
        requires_river=True,
    ),
    "pottery": TechDefinition(
        id="pottery",
        name="Poterie de terre cuite",
        category="artisanat",
        prerequisites=["fire_mastery"],
        description="Modelage et cuisson de jarres étanches pour conserver les graines et l'eau.",
        food_bonus=0.15,
        health_bonus=0.08,
    ),
    "water_craft": TechDefinition(
        id="water_craft",
        name="Pirogue monoxyle",
        category="transport",
        prerequisites=["fire_mastery", "flint_knapping"],
        description="Embarcation creusée dans un tronc permettant de franchir les fleuves.",
        food_bonus=0.10,
        health_bonus=0.02,
        requires_river=True,
    ),
    "early_horticulture": TechDefinition(
        id="early_horticulture",
        name="Semis et jardinage proto-agricole",
        category="nourriture",
        prerequisites=["pottery"],
        description="Plantation intentionnelle de tubercules et de graines autour du campement permanent.",
        food_bonus=0.30,
        health_bonus=0.10,
    ),
}


@dataclass
class ClanTechState:
    clan_id: int
    unlocked_techs: list[str] = field(default_factory=list)
    inventory: dict[str, int] = field(default_factory=lambda: {
        "silex": 10, "peaux": 5, "viande_sechee": 15, "plantes_medicinales": 5
    })

    def has(self, tech_id: str) -> bool:
        return tech_id in self.unlocked_techs

    def total_food_bonus(self) -> float:
        return sum(TECH_CATALOG[tid].food_bonus for tid in self.unlocked_techs if tid in TECH_CATALOG)

    def total_health_bonus(self) -> float:
        return sum(TECH_CATALOG[tid].health_bonus for tid in self.unlocked_techs if tid in TECH_CATALOG)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ClanTechState:
        return cls(**d)


class TechnologyRegistry:
    """Gestionnaire mondial des découvertes et du troc économique."""

    def __init__(self):
        self.clan_states: dict[int, ClanTechState] = {}

    def get_or_create(self, clan_id: int) -> ClanTechState:
        if clan_id not in self.clan_states:
            self.clan_states[clan_id] = ClanTechState(clan_id)
        return self.clan_states[clan_id]

    @classmethod
    def genesis(cls, society: Society) -> TechnologyRegistry:
        reg = cls()
        # Au départ, chaque clan maîtrise au moins la taille du silex
        for clan in society.clans.values():
            state = reg.get_or_create(clan.id)
            state.unlocked_techs = ["flint_knapping"]
        return reg

    def step(self, tick: int, year: int, society: Society, world: WorldMap, rng: Rng) -> list[Event]:
        """Évolution annuelle des innovations, du troc et de la diffusion."""
        events: list[Event] = []
        g = rng.gen("technology", tick)

        # 1. Découvertes autonomes
        for clan in society.clans.values():
            if not clan.member_ids:
                continue
            state = self.get_or_create(clan.id)
            y, x = clan.settlement_cell
            has_river = bool(world.river[y, x] > 0)

            # Recherche parmi les technologies candidates disponibles
            candidates = []
            for tid, tdef in TECH_CATALOG.items():
                if tid in state.unlocked_techs:
                    continue
                # Vérifier les prérequis
                if all(req in state.unlocked_techs for req in tdef.prerequisites):
                    if tdef.requires_river and not has_river:
                        continue
                    candidates.append(tdef)

            if candidates and g.random() < 0.20:  # 20% de chance annuelle d'illumination technique
                discovered = candidates[int(g.integers(0, len(candidates)))]
                state.unlocked_techs.append(discovered.id)
                events.append(Event(tick, "tech_discovered", {
                    "clan_id": clan.id,
                    "clan_name": clan.name,
                    "tech_id": discovered.id,
                    "tech_name": discovered.name,
                    "year": year,
                    "description": discovered.description,
                }))

        # 2. Diffusion par le commerce et les alliances inter-clans
        clan_ids = list(society.clans.keys())
        for i in range(len(clan_ids)):
            c1 = society.clans[clan_ids[i]]
            s1 = self.get_or_create(c1.id)
            for j in range(i + 1, len(clan_ids)):
                c2 = society.clans[clan_ids[j]]
                s2 = self.get_or_create(c2.id)

                rel = c1.relations.get(c2.id, 0.0)
                # Si relation d'alliance amicale (> 0.4), échange de biens et savoirs
                if rel > 0.4:
                    # Partage technologique (diffusion de c1 vers c2)
                    for tid in s1.unlocked_techs:
                        if tid not in s2.unlocked_techs and g.random() < 0.15:
                            s2.unlocked_techs.append(tid)
                            tname = TECH_CATALOG[tid].name
                            events.append(Event(tick, "tech_shared", {
                                "teacher_clan_id": c1.id,
                                "teacher_clan_name": c1.name,
                                "learner_clan_id": c2.id,
                                "learner_clan_name": c2.name,
                                "tech_name": tname,
                                "year": year,
                            }))
                    # Troc de ressources
                    events.append(Event(tick, "barter_trade", {
                        "clan1_id": c1.id,
                        "clan1_name": c1.name,
                        "clan2_id": c2.id,
                        "clan2_name": c2.name,
                        "year": year,
                        "goods_exchanged": "peaux et outillage de silex contre herbes séchées",
                    }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "clan_states": [s.to_dict() for s in self.clan_states.values()]
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TechnologyRegistry:
        reg = cls()
        reg.clan_states = {s["clan_id"]: ClanTechState.from_dict(s) for s in d.get("clan_states", [])}
        return reg
