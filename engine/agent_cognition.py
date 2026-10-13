"""Module de cognition des agents selon les principes de recherche PIMMUR et Park et al. (2023).

- Profile : Traits Big Five différenciés, motivations et inventaire de connaissances.
- Interaction : Perception strictement locale (cellule immédiate, campement, voisins).
- Memory : Flux de souvenirs, importance émotionnelle, oubli exponentiel et réflexion périodique.
- Minimal-control : Prompts purement descriptifs, aucune consigne de comportement prescriptive.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CognitiveMemory:
    tick: int
    year: int
    text: str
    importance: float = 0.5  # 0.0 (anecdotique) à 1.0 (fondateur/vital)
    last_recalled_tick: int = 0
    is_reflection: bool = False

    def current_salience(self, current_tick: int, decay_rate: float = 0.001) -> float:
        """Calcule la vivacité du souvenir avec décroissance temporelle (oubli progressif)."""
        dt = max(0, current_tick - self.tick)
        recency = math.exp(-decay_rate * dt)
        return round((self.importance * 0.7) + (recency * 0.3), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "year": self.year,
            "text": self.text,
            "importance": self.importance,
            "last_recalled_tick": self.last_recalled_tick,
            "is_reflection": self.is_reflection,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CognitiveMemory:
        return cls(**d)


@dataclass
class PersonalityProfile:
    """Traits des Big Five (0.0 à 1.0) pour garantir la diversité des comportements."""
    openness: float = 0.5          # Curiosité, accueil de la nouveauté / tabous
    conscientiousness: float = 0.5 # Discipline, respect des coutumes
    extraversion: float = 0.5      # Prise de parole, recherche des pairs
    agreeableness: float = 0.5     # Coopération, confiance, déférence
    neuroticism: float = 0.5       # Réaction à la peur, anxiété, prudence

    def to_dict(self) -> dict[str, float]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> PersonalityProfile:
        return cls(**d)


@dataclass
class AgentCognition:
    """Modèle cognitif interne persistant pour chaque habitant."""
    person_id: int
    personality: PersonalityProfile = field(default_factory=PersonalityProfile)
    values: list[str] = field(default_factory=list)
    fears: list[str] = field(default_factory=list)
    knowledge_inventory: list[str] = field(default_factory=list)
    memory_stream: list[CognitiveMemory] = field(default_factory=list)
    unreflected_importance: float = 0.0
    reflection_threshold: float = 3.0
    max_memory_capacity: int = 40

    @classmethod
    def create_random(cls, person_id: int, seed: int = 42) -> AgentCognition:
        """Instancie un profil cognitif différencié selon les Big Five (PIMMUR #1 Profile)."""
        import random
        rng = random.Random(seed + person_id * 1000)
        p = PersonalityProfile(
            openness=round(rng.uniform(0.15, 0.85), 2),
            conscientiousness=round(rng.uniform(0.15, 0.85), 2),
            extraversion=round(rng.uniform(0.15, 0.85), 2),
            agreeableness=round(rng.uniform(0.15, 0.85), 2),
            neuroticism=round(rng.uniform(0.15, 0.85), 2),
        )
        return cls(person_id=person_id, personality=p)

    @property
    def known_facts(self) -> set[str]:
        if not hasattr(self, "_known_facts_set") or self._known_facts_set is None:
            self._known_facts_set = set(self.knowledge_inventory)
        return self._known_facts_set

    @property
    def reflections(self) -> list[str]:
        return [m.text for m in self.memory_stream if m.is_reflection]

    def add_memory(
        self,
        tick: int,
        year: int,
        text: str,
        importance: float = 0.5,
    ) -> None:
        """Alias pour add_observation."""
        self.add_observation(tick, year, text, importance)

    def add_observation(
        self,
        tick: int,
        year: int,
        text: str,
        importance: float = 0.5,
    ) -> None:
        """Enregistre une observation vécue dans le flux de mémoire."""
        mem = CognitiveMemory(
            tick=tick,
            year=year,
            text=text,
            importance=importance,
            last_recalled_tick=tick,
        )
        self.memory_stream.append(mem)
        self.unreflected_importance += importance

        # Élagage et oubli des souvenirs les moins vifs si capacité atteinte
        if len(self.memory_stream) > self.max_memory_capacity:
            # Trier par vivacité actuelle
            self.memory_stream.sort(
                key=lambda m: (m.is_reflection, m.current_salience(tick)),
                reverse=True,
            )
            self.memory_stream = self.memory_stream[:self.max_memory_capacity]

    def trigger_reflection_if_needed(self, current_tick: int, current_year: int = -4004) -> str | None:
        """Synthétise périodiquement les souvenirs récents en une réflexion de haut niveau (Park et al., 2023)."""
        if self.unreflected_importance < self.reflection_threshold:
            return None

        # Sélectionner les souvenirs récents les plus saillants
        recent = [m for m in self.memory_stream if not m.is_reflection][-6:]
        if not recent:
            self.unreflected_importance = 0.0
            return None

        # Synthèse empirique basée sur les thèmes vécus
        all_text = " ".join(m.text.lower() for m in recent)
        reflection_text = None

        if any(w in all_text for w in ["faim", "gibier", "froid", "sécheresse", "hiver"]):
            reflection_text = "La nature impose ses cycles ; nous devons préserver nos forces et partager chaque prise pour traverser les saisons dures."
        elif any(w in all_text for w in ["naissance", "enfant", "union", "famille"]):
            reflection_text = "Notre lignée s'enracine dans cette terre ; voir les nôtres grandir donne un sens à chacune de nos aurores."
        elif any(w in all_text for w in ["deuil", "mort", "blessure", "danger"]):
            reflection_text = "La vie est fragile et éphémère ; veiller les uns sur les autres est la seule digue contre l'inconnu."
        elif any(w in all_text for w in ["interdit", "tabou", "sacré", "voyageur"]):
            reflection_text = "Certaines paroles venues d'au-delà de nos repères méritent qu'on y songe avant de transgresser l'ordre des coutumes."
        else:
            reflection_text = "Par mes gestes quotidiens au campement, j'apprends à lire les signes du vent et la coutume des miens."

        ref_mem = CognitiveMemory(
            tick=current_tick,
            year=current_year,
            text=f"Réflexion intérieure : « {reflection_text} »",
            importance=0.85,
            last_recalled_tick=current_tick,
            is_reflection=True,
        )
        self.memory_stream.append(ref_mem)
        self.unreflected_importance = 0.0
        return reflection_text

    def decide_on_proposal(self, text_or_topic: str, arg2: Any = None) -> dict[str, Any]:
        """Évalue une suggestion extérieure (ex: voyageur/observateur) sans contrainte scriptée.

        Retourne un dictionnaire avec :
        - 'proposal_detected': bool
        - 'proposal_text': str
        - 'decision': 'accept' | 'doubt' | 'reject'
        - 'justification': str
        """
        if isinstance(arg2, str):
            proposal_text = arg2
        else:
            proposal_text = text_or_topic

        low = proposal_text.lower()
        proposal_detected = any(w in low for w in [
            "tabou", "interdit", "défendu", "ne dois pas", "ne mange pas",
            "ne touchez pas", "défense de", "ne consomme pas", "paix",
            "harmonie", "dieu", "étoile", "nature", "amour", "veillez", "ensemble"
        ])

        # Utilise les traits Big Five de l'agent
        o = self.personality.openness
        c = self.personality.conscientiousness
        a = self.personality.agreeableness
        n = self.personality.neuroticism

        receptivity = (o * 0.4) + (a * 0.3) + (c * 0.2) - (n * 0.3)

        if any(w in low for w in ["tabou", "interdit", "défendu", "ne dois pas", "ne mange pas"]):
            if c >= 0.55 and receptivity >= 0.35:
                decision = "accept"
                just = "J'accueille cet interdit avec gravité et j'en tiendrai compte pour protéger le campement."
            elif n >= 0.65:
                decision = "doubt"
                just = "Tes mots m'inquiètent. Quel malheur nous guetterait si nous suivions ou ignorions cela ?"
            else:
                decision = "reject"
                just = "Nos ancêtres ne nous ont jamais transmis semblable défense. Je ne changerai pas nos coutumes à la légère."
        elif receptivity >= 0.5:
            decision = "accept"
            just = "Ta parole résonne avec justesse dans mon esprit ; je la méditerai."
        elif receptivity >= 0.3:
            decision = "doubt"
            just = "Je t'entends, mais le monde est imprévisible et je dois d'abord observer ce que disent les miens."
        else:
            decision = "reject"
            just = "Mes mains ont d'autres tâches pour assurer la vie des miens."

        return {
            "proposal_detected": proposal_detected,
            "proposal_text": proposal_text,
            "decision": decision,
            "justification": just,
        }

    def build_minimal_prompt_context(self, current_tick: int, current_year: int = -4004) -> str:
        """Produit le contexte strictement conforme au principe Minimal-Control (PIMMUR #4)."""
        lines = []

        # 1. Traits subjectifs de tempérament
        traits_desc = []
        if self.personality.openness > 0.6:
            traits_desc.append("nature curieuse et observatrice")
        elif self.personality.openness < 0.4:
            traits_desc.append("très attaché aux habitudes")

        if self.personality.agreeableness > 0.6:
            traits_desc.append("enclin à la conciliation")
        elif self.personality.agreeableness < 0.4:
            traits_desc.append("méfiant et franc-parler")

        if self.personality.neuroticism > 0.6:
            traits_desc.append("vite inquiet face aux menaces")
        elif self.personality.neuroticism < 0.4:
            traits_desc.append("calme face aux imprévus")

        if traits_desc:
            lines.append("Traits de caractère dominants (Big Five) : " + ", ".join(traits_desc) + ".")
        else:
            lines.append("Traits de caractère dominants (Big Five) : tempérament mesuré et pondéré.")

        # 2. Savoirs empiriques (TimeChara anti-anachronisme)
        if self.knowledge_inventory:
            lines.append("Connaissances du monde : " + ", ".join(self.knowledge_inventory[:6]) + ".")

        # 3. Flux de souvenirs récents et réflexions
        salient_memories = sorted(
            self.memory_stream,
            key=lambda m: m.current_salience(current_tick),
            reverse=True,
        )[:5]

        if salient_memories:
            m_texts = [f"An {m.year}: {m.text}" for m in salient_memories]
            lines.append("Mémoire vive : " + " | ".join(m_texts))

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "personality": self.personality.to_dict(),
            "values": list(self.values),
            "fears": list(self.fears),
            "knowledge_inventory": list(self.knowledge_inventory),
            "memory_stream": [m.to_dict() for m in self.memory_stream],
            "unreflected_importance": self.unreflected_importance,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentCognition:
        c = cls(person_id=d["person_id"])
        if "personality" in d:
            c.personality = PersonalityProfile.from_dict(d["personality"])
        c.values = list(d.get("values", []))
        c.fears = list(d.get("fears", []))
        c.knowledge_inventory = list(d.get("knowledge_inventory", []))
        c.memory_stream = [CognitiveMemory.from_dict(m) for m in d.get("memory_stream", [])]
        c.unreflected_importance = float(d.get("unreflected_importance", 0.0))
        return c
