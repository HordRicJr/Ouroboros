"""M18 - Panthéons Polythéistes, Rites Funéraires & Lieux Sacrés.

Ce module modélise l'élévation spirituelle et religieuse des sociétés :
- Panthéon de divinités personnalisées associées aux forces naturelles
- Érection de monuments et sanctuaires sacrés (mégalithes, tumulus, autels de pierre)
- Rites funéraires et culte des ancêtres lors du trépas des notables
- Fêtes saisonnières et offrandes garantissant la bienveillance des esprits
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .events import Event

if TYPE_CHECKING:
    from .people import People
    from .rng import Rng
    from .society import Society

DEITY_DOMAINS = [
    ("Soleil Radieux", "dispensateur de lumière et de vie", "fertilité"),
    ("Orage Rugissant", "maître de la foudre et des déluges", "guerre"),
    ("Mère des Moissons", "gardienne de la terre et des graines", "abondance"),
    ("Gardien des Abîmes", "juge des âmes et maître du repos éternel", "mort"),
    ("Grand Cerf Stellaire", "protecteur des bêtes et guide des chasseurs", "chasse"),
    ("Esprit des Rivières", "purificateur des eaux et source de clarté", "guérison"),
]

SITE_KINDS = [
    "Cercle de Mégalithes", "Source Sacrée", "Tumulus Ancestral",
    "Grotte aux Peintures Rituelles", "Autel de Pierre Noire"
]


@dataclass
class Deity:
    id: int
    name: str
    title: str
    domain: str
    symbol: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Deity:
        return cls(**d)


@dataclass
class SacredSite:
    id: int
    name: str
    cell: tuple[int, int]
    kind: str
    clan_id: int
    deity_name: str
    founded_year: int
    veneration_power: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cell"] = list(self.cell)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SacredSite:
        d = dict(d)
        d["cell"] = tuple(d["cell"])
        return cls(**d)


class ReligionRegistry:
    """Gestionnaire mondial des croyances théologiques, panthéons et lieux sacrés."""

    def __init__(self):
        self.deities: dict[int, Deity] = {}
        self.sacred_sites: dict[int, SacredSite] = {}
        self.next_deity_id = 1
        self.next_site_id = 1

    @classmethod
    def genesis(cls, rng: Rng) -> ReligionRegistry:
        reg = cls()
        g = rng.gen("religion-genesis")

        # Générer 4 à 6 divinités majeures du panthéon originel
        for title, domain_desc, domain_key in DEITY_DOMAINS:
            name_root = str(g.choice(["Sol", "Thor", "Gaï", "Morg", "Khor", "Lyr", "Astra", "Bel"]))
            deity_name = f"{name_root}an"
            d = Deity(
                id=reg.next_deity_id,
                name=deity_name,
                title=f"{title} ({domain_desc})",
                domain=domain_key,
                symbol=str(g.choice(["Disque d'or", "Éclair gravé", "Épi de blé", "Crâne d'ours", "Spirale d'eau"])),
            )
            reg.deities[d.id] = d
            reg.next_deity_id += 1
        return reg

    def step(self, tick: int, year: int, society: Society, people: People, rng: Rng) -> list[Event]:
        """Évolution annuelle des cultes et érection de nouveaux sanctuaires."""
        events: list[Event] = []
        g = rng.gen("religion", tick)

        # 1. Érection de monuments sacrés par les clans ayant dépassé 15 membres
        for clan in society.clans.values():
            if not clan.member_ids:
                continue

            # Vérifier si le clan possède déjà un sanctuaire
            clan_sites = [s for s in self.sacred_sites.values() if s.clan_id == clan.id]
            if not clan_sites and len(clan.member_ids) >= 12 and g.random() < 0.25:
                kind = str(g.choice(SITE_KINDS))
                deity = self.deities[int(g.choice(list(self.deities.keys())))]
                site_name = f"{kind} de {deity.name} ({clan.name})"

                site = SacredSite(
                    id=self.next_site_id,
                    name=site_name,
                    cell=clan.settlement_cell,
                    kind=kind,
                    clan_id=clan.id,
                    deity_name=deity.name,
                    founded_year=year,
                )
                self.sacred_sites[site.id] = site
                self.next_site_id += 1

                events.append(Event(tick, "sacred_site_erected", {
                    "site_id": site.id,
                    "site_name": site.name,
                    "clan_id": clan.id,
                    "clan_name": clan.name,
                    "deity_name": deity.name,
                    "year": year,
                    "cell": list(clan.settlement_cell),
                }))

        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "deities": [d.to_dict() for d in self.deities.values()],
            "sacred_sites": [s.to_dict() for s in self.sacred_sites.values()],
            "next_deity_id": self.next_deity_id,
            "next_site_id": self.next_site_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReligionRegistry:
        reg = cls()
        reg.next_deity_id = d.get("next_deity_id", 1)
        reg.next_site_id = d.get("next_site_id", 1)
        reg.deities = {x["id"]: Deity.from_dict(x) for x in d.get("deities", [])}
        reg.sacred_sites = {x["id"]: SacredSite.from_dict(x) for x in d.get("sacred_sites", [])}
        return reg
