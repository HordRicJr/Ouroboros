"""M12 - Langues, Dialectes Émergents & Toponymie.

Ce module modélise l'émergence linguistique :
- Phonotaxe générative (inventaire de consonnes, voyelles, structures syllabiques)
- Lexique proto-linguistique fondamental (racines pour la terre, l'eau, le feu, le chef, le soleil, etc.)
- Toponymie émergente (noms des lieux et campements générés dans la langue du clan local)
- Anthroponymie (prénoms générés selon la phonotaxe de la culture)
- Dérive linguistique annuelle (mutations phonétiques, glissements lexicaux lors des scissions)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from .rng import Rng

# Notions fondamentales du lexique primordial
CORE_CONCEPTS = [
    "eau", "feu", "soleil", "lune", "terre", "arbre", "montagne", "riviere",
    "bête", "homme", "femme", "enfant", "chef", "chasseur", "ciel", "nuit",
    "froid", "chaud", "mort", "vie", "esprit", "pierre", "vent", "grand"
]

# Inventaires phonétiques de base
CONSONANT_SETS = [
    ["k", "t", "p", "m", "n", "s", "r", "l", "w", "y"],          # Harmonieux / doux
    ["kh", "th", "g", "d", "b", "z", "r", "v", "sh", "ng"],       # Guttural / rugueux
    ["t", "k", "s", "h", "m", "n", "l", "f", "ch", "ts"],         # Léger / sifflant
    ["b", "d", "g", "r", "l", "m", "n", "p", "t", "k"],           # Classique équilibré
]

VOWEL_SETS = [
    ["a", "i", "u", "e", "o"],
    ["a", "e", "o"],
    ["a", "i", "u"],
    ["a", "e", "i", "o", "u", "y"],
]

SYLLABLE_PATTERNS = ["CV", "CVC", "VC", "CVV"]


@dataclass
class Language:
    id: int
    name: str
    family_name: str
    consonants: list[str]
    vowels: list[str]
    syllable_patterns: list[str]
    lexicon: dict[str, str] = field(default_factory=dict)  # concept -> mot
    parent_lang_id: int | None = None
    drift_count: int = 0

    def generate_syllable(self, g: np.random.Generator) -> str:
        pat = str(g.choice(self.syllable_patterns))
        out = []
        for char in pat:
            if char == "C":
                out.append(str(g.choice(self.consonants)))
            elif char == "V":
                out.append(str(g.choice(self.vowels)))
        return "".join(out)

    def generate_word(self, g: np.random.Generator, syllables_count: int = 2) -> str:
        parts = [self.generate_syllable(g) for _ in range(syllables_count)]
        return "".join(parts).capitalize()

    def translate(self, concept: str, g: np.random.Generator | None = None) -> str:
        if concept in self.lexicon:
            return self.lexicon[concept]
        if g is not None:
            word = self.generate_word(g, syllables_count=2).lower()
            self.lexicon[concept] = word
            return word
        return concept

    def generate_person_name(self, sex: str, g: np.random.Generator) -> str:
        syl = 2 if g.random() < 0.7 else 3
        base = self.generate_word(g, syllables_count=syl)
        suffix = "a" if sex == "F" and not base.endswith(("a", "e", "i")) else ("r" if sex == "M" and base.endswith(("a", "e", "i", "o", "u")) else "")
        return (base + suffix).capitalize()

    def generate_place_name(self, biome_or_feature: str, g: np.random.Generator) -> str:
        """Génère un toponyme selon les racines de la langue (ex: Eau-Grande, Terre-Montagne)."""
        root1 = self.translate(biome_or_feature, g)
        descriptor = str(g.choice(["grand", "terre", "eau", "esprit", "soleil"]))
        root2 = self.translate(descriptor, g)
        return f"{root1.capitalize()}-{root2.capitalize()}"

    def branch(self, new_id: int, new_name: str, g: np.random.Generator) -> Language:
        """Crée un dialecte dérivé lors d'une scission clanique ou dispersion géographique."""
        new_cons = list(self.consonants)
        new_vow = list(self.vowels)

        # Mutation phonologique légère
        if g.random() < 0.4 and len(new_cons) > 5:
            idx = int(g.integers(0, len(new_cons)))
            mutated = new_cons[idx] + "h" if not new_cons[idx].endswith("h") else new_cons[idx][:-1]
            new_cons[idx] = mutated or "s"

        # Glissement lexical sur 20% des mots existants
        new_lex = dict(self.lexicon)
        for c in list(new_lex.keys()):
            if g.random() < 0.25:
                new_lex[c] = self.generate_word(g, syllables_count=2).lower()

        return Language(
            id=new_id,
            name=new_name,
            family_name=self.family_name,
            consonants=new_cons,
            vowels=new_vow,
            syllable_patterns=list(self.syllable_patterns),
            lexicon=new_lex,
            parent_lang_id=self.id,
            drift_count=self.drift_count + 1,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Language:
        return cls(**d)


class LanguageRegistry:
    """Gestionnaire global des langues et dialectes de la simulation."""

    def __init__(self):
        self.languages: dict[int, Language] = {}
        self.next_lang_id = 1

    @classmethod
    def genesis(cls, rng: Rng) -> LanguageRegistry:
        reg = cls()
        g = rng.gen("language-genesis")

        # Création de la proto-langue primordiale
        c_set = list(CONSONANT_SETS[int(g.integers(0, len(CONSONANT_SETS)))])
        v_set = list(VOWEL_SETS[int(g.integers(0, len(VOWEL_SETS)))])

        proto = Language(
            id=reg.next_lang_id,
            name="Proto-Ouroboréen",
            family_name="Ouroboréenne",
            consonants=c_set,
            vowels=v_set,
            syllable_patterns=list(SYLLABLE_PATTERNS),
            lexicon={},
        )
        # Initialiser le lexique primordial
        for concept in CORE_CONCEPTS:
            proto.translate(concept, g)

        reg.languages[proto.id] = proto
        reg.next_lang_id += 1
        return reg

    def get_or_default(self, lang_id: int | None) -> Language:
        if lang_id is not None and lang_id in self.languages:
            return self.languages[lang_id]
        if self.languages:
            return next(iter(self.languages.values()))
        raise ValueError("Aucune langue enregistrée.")

    def step(self, tick: int, year: int, g: np.random.Generator) -> list[dict[str, Any]]:
        """Dérive phonétique lente au fil des générations (tous les 5 ans)."""
        events = []
        if year > 0 and year % 5 == 0:
            for lang in self.languages.values():
                if g.random() < 0.15:
                    concept = str(g.choice(CORE_CONCEPTS))
                    old_word = lang.lexicon.get(concept, "")
                    new_word = lang.generate_word(g, 2).lower()
                    lang.lexicon[concept] = new_word
                    lang.drift_count += 1
                    events.append({
                        "type": "linguistic_drift",
                        "language_id": lang.id,
                        "language_name": lang.name,
                        "concept": concept,
                        "old_word": old_word,
                        "new_word": new_word,
                        "year": year,
                    })
        return events

    def to_dict(self) -> dict[str, Any]:
        return {
            "languages": [lang.to_dict() for lang in self.languages.values()],
            "next_lang_id": self.next_lang_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LanguageRegistry:
        reg = cls()
        reg.next_lang_id = d.get("next_lang_id", 1)
        reg.languages = {l["id"]: Language.from_dict(l) for l in d.get("languages", [])}
        return reg
