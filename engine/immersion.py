"""Module d'immersion totale et de dialogue pour les notables simulés.

RÈGLES CRUCIALES D'IMMERSION :
1. Les habitants IGNORENT ABSOLUMENT qu'ils sont dans une simulation numérique ou un programme informatique.
2. Tout concept technologique moderne (code, IA, CPU, bits, simulation, développeur) est INTERDIT et filtré.
3. Leurs explications des phénomènes du monde (climat, foudre, maladies, saisons, étoiles) sont
   purement mythologiques, empiriques et basées sur leurs croyances culturelles.
4. Le filtre d'immersion (ImmersionFilter) détecte et assainit tout anachronisme ou bris de quatrième mur.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import Universe
    from .llm import LLMClient
    from .notable import NotableProfile
    from .people import Person


FORBIDDEN_SIMULATION_TERMS = [
    r"\bsimulation\b", r"\bsimulé\b", r"\bsimuler\b", r"\bordinateur\b", r"\bia\b",
    r"\bintelligence artificielle\b", r"\bprogramme\b", r"\bcode\b", r"\balgorithme\b",
    r"\bserveur\b", r"\bnumérique\b", r"\bpixel\b", r"\bmatrice\b", r"\bbot\b",
    r"\blangage python\b", r"\bbackend\b", r"\bdatabase\b", r"\bdataset\b",
]

# Mots de théorie / expérience à écarter des prompts (PIMMUR minimal-control & unawareness)
FORBIDDEN_THEORY_TERMS = [
    r"\bhiérarchie\b", r"\bcontrat social\b", r"\bgénèse\b", r"\bgenese\b",
    r"\bexpérience\b", r"\bhypothèse\b", r"\bémergence\b", r"\bpimmur\b",
    r"\bbig five\b", r"\bllm\b", r"\bagents?\b",
]

MYTHOLOGICAL_SUBSTITUTES = {
    "simulation": "mystère du monde",
    "programme": "destinée",
    "ordinateur": "oracle céleste",
    "ia": "esprit",
    "code": "lois de la création",
}


class ImmersionFilter:
    """Filtre garantissant qu'aucune réponse ne brise l'immersion ou le réalisme subjectif."""

    anachronism_hits: int = 0
    anachronism_checks: int = 0

    @classmethod
    def sanitize(cls, text: str) -> str:
        out = text
        for pat in FORBIDDEN_SIMULATION_TERMS:
            out = re.sub(pat, "mystère des ancêtres", out, flags=re.IGNORECASE)
        for pat in FORBIDDEN_THEORY_TERMS:
            out = re.sub(pat, "coutume", out, flags=re.IGNORECASE)
        return out

    @classmethod
    def check_immersion_break(cls, text: str) -> bool:
        """Retourne True si le texte contient un bris de 4e mur."""
        for pat in FORBIDDEN_SIMULATION_TERMS + FORBIDDEN_THEORY_TERMS:
            if re.search(pat, text, flags=re.IGNORECASE):
                return True
        return False

    @classmethod
    def check_anachronism_trap(cls, text: str, year: int) -> bool:
        """Piège simple : vocabulaire technologique hors époque (fer avant métallurgie mondiale)."""
        cls.anachronism_checks += 1
        traps = [r"\bfer\b", r"\bacier\b", r"\bpoudre\b", r"\bélectricité\b", r"\bmoteur\b"]
        # Avant an 0 simulé ou monde « early », ces mots sont anachroniques par défaut
        if year > 500:
            return False
        hit = any(re.search(pat, text, flags=re.IGNORECASE) for pat in traps)
        if hit:
            cls.anachronism_hits += 1
        return hit

    @classmethod
    def anachronism_rate(cls) -> float:
        if cls.anachronism_checks <= 0:
            return 0.0
        return round(cls.anachronism_hits / cls.anachronism_checks, 4)


def build_immersion_prompt(person: Person, profile: NotableProfile, universe: Universe) -> list[dict[str, str]]:
    """Construit un prompt complet en immersion totale pour Qwen2.5-7B."""
    date = universe.date
    y, x = person.cell
    biome = universe.world.biome_name(y, x)
    round(float(universe.world.mean_temp[y, x]), 1)
    
    # Liens familiaux
    kin_text = []
    if person.mother_id and person.mother_id in universe.people.persons:
        kin_text.append(f"Mère: {universe.people.persons[person.mother_id].name}")
    if person.father_id and person.father_id in universe.people.persons:
        kin_text.append(f"Père: {universe.people.persons[person.father_id].name}")
    if person.spouse_ids:
        spouses = [universe.people.persons[sid].name for sid in person.spouse_ids if sid in universe.people.persons]
        if spouses:
            kin_text.append(f"Conjoint(e): {', '.join(spouses)}")
    if person.children_ids:
        children = [universe.people.persons[cid].name for cid in person.children_ids if cid in universe.people.persons]
        if children:
            kin_text.append(f"Enfants ({len(children)}): {', '.join(children[:4])}")

    family_str = " | ".join(kin_text) if kin_text else "Vit seul(e) ou parents disparus"
    mem_str = profile.summary_context()

    clan = universe.society.get_person_clan(person.id) if hasattr(universe, "society") else None
    clan_info = []
    if clan:
        clan_info.append(f"Appartenance : {clan.name} (Totem : {clan.totem})")
        clan_info.append(f"Mythe fondateur : {clan.cosmogony}")
        if clan.taboos:
            clan_info.append("Usages évités par les miens : " + " ; ".join(clan.taboos))
        if hasattr(universe, "languages") and clan.language_id in universe.languages.languages:
            lang = universe.languages.languages[clan.language_id]
            words = [f"{c}={lang.lexicon[c]}" for c in ["soleil", "eau", "feu"] if c in lang.lexicon]
            if words:
                clan_info.append(f"Paroles du camp ({lang.name}) : " + ", ".join(words))
        if hasattr(universe, "technology") and clan.id in universe.technology.clan_states:
            techs = universe.technology.clan_states[clan.id].unlocked_techs
            from .technology import TECH_CATALOG
            tech_names = [TECH_CATALOG[tid].name for tid in techs if tid in TECH_CATALOG]
            if tech_names:
                clan_info.append("Gestes et savoirs du camp : " + ", ".join(tech_names))
    clan_str = "\n- ".join(clan_info)
    clan_line = f"- {clan_str}\n" if clan_str else ""

    cognition_ctx = ""
    if hasattr(universe, "agent_cognitions") and person.id in universe.agent_cognitions:
        cog = universe.agent_cognitions[person.id]
        cognition_ctx = f"\n- {cog.build_minimal_prompt_context(universe.tick)}\n"

    system_prompt = f"""Tu es {person.name}. Tu vis dans ce monde avec un corps, des attachements et des peurs.
- Année : {date.year}, jour {date.day_of_year}.
- Lieu : région de {biome}.
- Les autres te décrivent parfois ainsi : {profile.title}.
- Liens du sang : {family_str}.
{clan_line}{cognition_ctx}- {mem_str}

Réponds à la première personne, en 2 à 4 phrases. Ne parle que de ce que tu as vécu ou appris ici.
"""

    return [
        {"role": "system", "content": system_prompt}
    ]


class NotableAgent:
    """Gestionnaire d'interactions pour un notable doté d'IA."""
    def __init__(self, person_id: int, profile: NotableProfile, llm_client: LLMClient):
        self.person_id = person_id
        self.profile = profile
        self.llm = llm_client

    def ponder(self, question_or_event: str, universe: Universe) -> str:
        """Génère une réflexion ou réponse incarnée de l'habitant."""
        import time

        person = universe.people.persons.get(self.person_id)
        if not person:
            return "..."

        messages = build_immersion_prompt(person, self.profile, universe)
        messages.append({
            "role": "user",
            "content": f"Voici ce qui t'arrive ou la question qu'on te pose : « {question_or_event} ». Que dis-tu ou que penses-tu ?"
        })

        t_start = time.time()
        raw_response = self.llm.generate(messages, max_tokens=80, temperature=0.7)
        duration_ms = (time.time() - t_start) * 1000.0
        ImmersionFilter.check_anachronism_trap(raw_response, universe.date.year)
        sanitized = ImmersionFilter.sanitize(raw_response)

        self.profile.log_short_term(f"A songé : « {sanitized[:60]}... »")

        if hasattr(universe, "ai_logger"):
            model_name = getattr(self.llm, "model_name", "qwen2.5-1.5b")
            model_fingerprint = getattr(self.llm, "model_fingerprint", "")
            llama_version = getattr(self.llm, "llama_cpp_version", "")
            universe.ai_logger.log(
                tick=universe.tick,
                year=universe.date.year,
                agent_id=self.person_id,
                model_name=model_name,
                temperature=0.7,
                prompt=f"{messages[0]['content']}\n[USER]: {question_or_event}",
                response=sanitized,
                duration_ms=duration_ms,
                kind="dialogue",
                model_fingerprint=model_fingerprint,
                llama_cpp_version=llama_version,
            )

        return sanitized
