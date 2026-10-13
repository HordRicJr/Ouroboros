"""M09 - Individus suivis (niveau « notables ») : cycle de vie, mariage, hérédité, lignées.

Ces individus ont un génome diploïde réel, des parents, des conjoints et des enfants.
Les règles de mariage et de famille dépendent de la culture (CultureRules).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from .events import Event
from .genetics import (
    I_FERT,
    I_IMM,
    I_LONG,
    I_RES,
    make_child,
    make_genome,
    phenotype,
)
from .rng import Rng

_FIRST_M = [
    "Adan", "Seth", "Enosh", "Kenan", "Jared", "Enoch", "Mathus", "Lamek", "Noe", "Sem",
    "Cham", "Japhet", "Eber", "Peleg", "Abram", "Isaac", "Jacob", "Ruben", "Juda", "Joseph"
]
_FIRST_F = [
    "Eva", "Sara", "Ada", "Silla", "Dina", "Lia", "Rachel", "Noema", "Rebecca", "Milca",
    "Tamar", "Ruth", "Miryam", "Anna", "Debora", "Hana", "Sarra", "Ela", "Mara", "Ketsia"
]
_END = ["", "el", "an", "ar", "en", "ir", "on", "us", "a", "or"]


@dataclass
class CultureRules:
    """Règles familiales d'une culture (étendues par le module Société plus tard)."""
    name: str = "ancestrale"
    marriage_min_age: int = 15
    max_age_gap: int = 25
    kin_taboo_degree: int = 1        # 0 = aucun interdit ; 1 = parents/fratrie directe ; 2 = + cousins/oncles
    monogamy: bool = True
    fertility_norm: float = 1.3      # vitalité naturelle de natalité pionnière
    min_birth_spacing_years: float = 1.0


@dataclass
class Person:
    id: int
    name: str
    sex: str                         # "F" ou "M"
    species_id: int
    birth_tick: int
    cell: tuple[int, int]
    genome: list                     # (2, NT) sous forme de listes
    mother_id: int | None = None
    father_id: int | None = None
    spouse_ids: list[int] = field(default_factory=list)
    children_ids: list[int] = field(default_factory=list)
    death_tick: int | None = None
    cause_of_death: str | None = None
    last_birth_tick: int | None = None
    culture: str = "ancestrale"
    notable: bool = False

    @property
    def alive(self) -> bool:
        return self.death_tick is None

    def genome_array(self) -> np.ndarray:
        return np.asarray(self.genome, dtype=float)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["cell"] = list(self.cell)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Person:
        d = dict(d)
        d["cell"] = tuple(d["cell"])
        return cls(**d)


class People:
    def __init__(self, max_followed: int = 2000):
        self.persons: dict[int, Person] = {}
        self.next_id = 1
        self.max_followed = max_followed
        self.cultures: dict[str, CultureRules] = {"ancestrale": CultureRules()}

    # -------------------------------------------------------------- création
    def _name(self, sex: str, g: np.random.Generator) -> str:
        first = _FIRST_F if sex == "F" else _FIRST_M
        suffix = str(g.choice(_END))
        base = str(g.choice(first))
        return base if not suffix or base.endswith(suffix) else base + suffix

    def add(self, sex, species_id, tick, cell, genome, g, mother=None, father=None, culture="ancestrale") -> Person:
        p = Person(self.next_id, self._name(sex, g), sex, species_id, tick, cell, genome.tolist(),
                   mother.id if mother else None, father.id if father else None, culture=culture)
        self.persons[p.id] = p
        self.next_id += 1
        if mother:
            mother.children_ids.append(p.id)
        if father:
            father.children_ids.append(p.id)
        return p

    @classmethod
    def genesis(cls, eco, rng: Rng, tick: int = 0, couples_per_camp: int = 1) -> People:
        """Genèse biblique originelle : exactement DEUX personnes au commencement (Adan & Eva).
        Si l'écosystème spécifie plusieurs campements distincts (tests multi-clans),
        instancie un couple fondateur par campement.
        """
        from .species import HUMAN
        people = cls()
        hs = [s for s in eco.species if s.kind == HUMAN]
        if not hs:
            return people
        sp = hs[0]
        base = np.asarray(sp.traits)
        g = rng.gen("people-genesis")

        if len(eco.human_cells) <= 1:
            # Exactement DEUX PERSONNES au commencement du monde
            y, x = eco.human_cells[0] if eco.human_cells else (50, 50)
            m = people.add("M", sp.id, tick, (y, x), make_genome(base, g), g)
            f = people.add("F", sp.id, tick, (y, x), make_genome(base, g), g)
            m.name = "Adan"
            f.name = "Eva"
            m.birth_tick = tick - 20 * 365
            f.birth_tick = tick - 18 * 365
            m.spouse_ids, f.spouse_ids = [f.id], [m.id]
            m.notable, f.notable = True, True
        else:
            # Campements multiples (ex: tests inter-clans, guerre ou diplomatie)
            for i, (y, x) in enumerate(eco.human_cells):
                m = people.add("M", sp.id, tick, (y, x), make_genome(base, g), g)
                f = people.add("F", sp.id, tick, (y, x), make_genome(base, g), g)
                if i == 0:
                    m.name = "Adan"
                    f.name = "Eva"
                m.birth_tick = tick - 20 * 365
                f.birth_tick = tick - 18 * 365
                m.spouse_ids, f.spouse_ids = [f.id], [m.id]
                m.notable, f.notable = True, True
        return people

    # --------------------------------------------------------------- requêtes
    def age_years(self, p: Person, tick: int) -> float:
        end = p.death_tick if p.death_tick is not None else tick
        return (end - p.birth_tick) / 365.0

    def alive_persons(self) -> list[Person]:
        return [p for p in self.persons.values() if p.alive]

    def ancestors(self, pid: int, depth: int) -> set[int]:
        out, frontier = set(), {pid}
        for _ in range(depth):
            nxt = set()
            for i in frontier:
                p = self.persons[i]
                for par in (p.mother_id, p.father_id):
                    if par is not None and par not in out:
                        nxt.add(par)
            out |= nxt
            frontier = nxt
        return out

    def are_kin(self, a: int, b: int, degree: int) -> bool:
        if degree <= 0:
            return False
        if a == b:
            return True
        aa, ab = self.ancestors(a, degree) | {a}, self.ancestors(b, degree) | {b}
        # lien direct (parent/enfant, grand-parent...) ou ancêtre commun dans `degree` générations
        return bool(aa & ab)

    def genealogy(self, pid: int, up: int = 3, down: int = 3) -> dict:
        def desc(i: int, d: int) -> dict:
            p = self.persons[i]
            node = {"id": p.id, "name": p.name, "sex": p.sex, "born": p.birth_tick, "died": p.death_tick}
            if d > 0:
                node["children"] = [desc(c, d - 1) for c in p.children_ids]
            return node

        def asc(i: int | None, d: int) -> dict | None:
            if i is None or d < 0:
                return None
            p = self.persons[i]
            return {"id": p.id, "name": p.name, "sex": p.sex, "born": p.birth_tick, "died": p.death_tick,
                    "mother": asc(p.mother_id, d - 1), "father": asc(p.father_id, d - 1)}
        return {"ancestors": asc(pid, up), "descendants": desc(pid, down)}

    # ------------------------------------------------------------------ pas
    def _biblical_baseline_life(self, p: Person, tick: int) -> float:
        """Calibre la longévité selon la référence biblique (Genèse antédiluvienne vers ère historique).
        
        Adam & Ève et les patriarches antédiluviens vivent plusieurs siècles (Genèse 5).
        La longévité décroît progressivement au fil des millénaires pour converger vers 70-80 ans (Psaume 90).
        """
        years_from_start = tick / 365.0
        if years_from_start < 1656:  # Période antédiluvienne (d'Adam au Déluge)
            if p.id in (1, 2):       # Adan et Eva
                return 930.0
            return max(350.0, 912.0 - years_from_start * 0.3)
        elif years_from_start < 2500:  # Patriarches postdiluviens (d'Abraham à Moïse)
            return max(120.0, 350.0 - (years_from_start - 1656) * 0.25)
        else:                          # Ère historique standard (Psaume 90)
            return 80.0

    def _death_hazard_per_year(self, p: Person, age: float, food_f: float, tick: int = 0) -> float:
        g = phenotype(p.genome_array())
        biblical_life = self._biblical_baseline_life(p, tick)
        life = biblical_life * (0.8 + 0.4 * g[I_LONG])
        base = 0.005 + 0.00010 * np.exp(6.0 * age / life)
        
        # Durant les premières générations bibliques, mortalité infantile minime
        years_from_start = tick / 365.0
        if years_from_start > 1500:
            if age < 1:
                base += 0.08
            elif age < 5:
                base += 0.02
        else:
            if age < 1:
                base += 0.01

        base *= (1.5 - g[I_RES]) * (1.3 - 0.6 * g[I_IMM])
        return float(base * (1 + 1.5 * (1 - food_f)))

    def step(self, tick: int, eco, rng: Rng, mutation_rate: float, human_food: dict | None = None) -> list[Event]:
        events: list[Event] = []
        g = rng.gen("people", tick)
        alive = sorted(self.alive_persons(), key=lambda p: p.id)
        n_alive = len(alive)

        # morts
        for p in alive:
            y, x = p.cell
            f = float(eco.feff[p.species_id, y, x]) if p.species_id < len(eco.feff) else 1.0
            age = self.age_years(p, tick)
            h = self._death_hazard_per_year(p, age, f, tick)
            if g.random() < 1 - np.exp(-h / 365.0):
                p.death_tick = tick
                p.cause_of_death = "famine" if f < 0.4 and g.random() < 0.5 else ("vieillesse" if age > 70 else "maladie")
                n_alive -= 1
                events.append(Event(tick, "death", {"person_id": p.id, "name": p.name, "age": round(age, 1),
                                                    "cause": p.cause_of_death}))
        # veuvage
        for p in alive:
            if p.alive:
                p.spouse_ids = [s for s in p.spouse_ids if self.persons[s].alive]

        alive = [p for p in alive if p.alive]
        by_cell: dict[tuple, list[Person]] = {}
        for p in alive:
            by_cell.setdefault(p.cell, []).append(p)

        # Mariages et unions spontanées au sein de la communauté
        single = [p for p in alive if p.alive and not p.spouse_ids]
        if single:
            for group in by_cell.values():
                males = [p for p in group if p.sex == "M" and not p.spouse_ids]
                females = [p for p in group if p.sex == "F" and not p.spouse_ids]
                for m in males:
                    if m.spouse_ids:
                        continue
                    rules = self.cultures.get(m.culture, CultureRules())
                    m_age = self.age_years(m, tick)
                    if m_age < rules.marriage_min_age:
                        continue
                    
                    # Déterminer les partenaires féminines éligibles :
                    # Règle biblique originelle : tant que la population vivante totale est < 30
                    # (commencement du monde), les enfants du premier couple s'unissent entre eux
                    # pour fonder la lignée humaine (en évitant l'union directe parent-enfant).
                    is_genesis_era = n_alive < 30 or (m.mother_id in (1, 2) and m.father_id in (1, 2))
                    
                    options = []
                    for f in females:
                        if f.spouse_ids:
                            continue
                        f_age = self.age_years(f, tick)
                        if f_age < rules.marriage_min_age:
                            continue
                        # Écart d'âge plus large durant l'ère de grande longévité patriarcale
                        max_gap = 150 if is_genesis_era else rules.max_age_gap
                        if abs(f_age - m_age) > max_gap:
                            continue
                        
                        if is_genesis_era:
                            # Ne pas épouser son propre père ou sa propre mère
                            if f.id in (m.mother_id, m.father_id) or m.id in (f.mother_id, f.father_id):
                                continue
                            options.append(f)
                        else:
                            # Interdit de consanguinité normale une fois le monde peuplé
                            if not self.are_kin(m.id, f.id, rules.kin_taboo_degree):
                                options.append(f)

                    if options and g.random() < 0.20:
                        f = options[int(g.integers(0, len(options)))]
                        m.spouse_ids, f.spouse_ids = [f.id], [m.id]
                        events.append(Event(tick, "marriage", {"husband_id": m.id, "wife_id": f.id,
                                                               "husband": m.name, "wife": f.name}))

        # Naissances émergentes (organiques, fondées sur la biologie, l'abondance de nourriture et le clan)
        for p in alive:
            if p.sex != "F" or n_alive >= self.max_followed:
                continue
            rules = self.cultures.get(p.culture, CultureRules())
            age = self.age_years(p, tick)
            
            # Période féconde :
            # Dans la Genèse, Ève et les premières matriarches engendrent sur une très longue période de leur vie
            biblical_life = self._biblical_baseline_life(p, tick)
            max_fertile_age = min(350.0, biblical_life * 0.45) if biblical_life > 150 else 46.0
            if not (15 <= age <= max_fertile_age):
                continue
            if p.last_birth_tick is not None and (tick - p.last_birth_tick) / 365.0 < rules.min_birth_spacing_years:
                continue

            # Père : époux ou partenaire d'union libre du campement
            fa = None
            if p.spouse_ids and self.persons[p.spouse_ids[0]].alive:
                fa = self.persons[p.spouse_ids[0]]
            else:
                is_genesis_era = n_alive < 30
                c_males = [m for m in by_cell.get(p.cell, [])
                           if m.sex == "M" and m.alive and self.age_years(m, tick) >= 15
                           and (is_genesis_era or not self.are_kin(p.id, m.id, degree=1))]
                if c_males:
                    fa = c_males[int(g.integers(0, len(c_males)))]

            if not fa:
                continue

            y, x = p.cell
            food = float(eco.feff[p.species_id, y, x]) if p.species_id < len(eco.feff) else 1.0
            gm = phenotype(p.genome_array())
            gf = phenotype(fa.genome_array())
            fert = (0.5 + gm[I_FERT]) * 0.7 + (0.5 + gf[I_FERT]) * 0.3
            annual = 0.55 * fert * rules.fertility_norm * max(0.4, min(1.5, food))
            if g.random() < 1 - np.exp(-annual / 365.0):
                child_genome = make_child(p.genome_array(), fa.genome_array(), g, mutation_rate)
                sex = "F" if g.random() < 0.5 else "M"
                c = self.add(sex, p.species_id, tick, p.cell, child_genome, g, p, fa, p.culture)
                p.last_birth_tick = tick
                n_alive += 1
                events.append(Event(tick, "birth", {"person_id": c.id, "name": c.name, "mother_id": p.id,
                                                    "father_id": fa.id, "sex": sex}))
        return events

    # ------------------------------------------------------------ sérialisation
    def to_dict(self) -> dict:
        return {"persons": [p.to_dict() for p in self.persons.values()], "next_id": self.next_id,
                "max_followed": self.max_followed,
                "cultures": {k: asdict(v) for k, v in self.cultures.items()}}

    @classmethod
    def from_dict(cls, d: dict) -> People:
        p = cls(d["max_followed"])
        p.next_id = d["next_id"]
        p.persons = {x["id"]: Person.from_dict(x) for x in d["persons"]}
        p.cultures = {k: CultureRules(**v) for k, v in d["cultures"].items()}
        return p
