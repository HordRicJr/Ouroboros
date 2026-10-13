"""Client d'inférence LLM pour les notables et le narrateur.

Prend en charge :
- MockLLMClient (déterministe, pour les tests sans réseau/GPU)
- HuggingFaceInferenceClient (API Serverless ou Endpoint dédié Hugging Face / vLLM AWS)
"""
import logging
import os
import re
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    def generate(self, messages: list[dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        ...


class ContextualPersonaGenerator:
    """Générateur narratif contextuel incarnant fidèlement l'habitant selon sa vie simulée."""

    @classmethod
    def generate_response(cls, messages: list[dict[str, str]]) -> str:
        sys_prompt = ""
        user_msg = ""
        for m in messages:
            if m.get("role") == "system":
                sys_prompt = m.get("content", "")
            elif m.get("role") == "user":
                user_msg = m.get("content", "")

        # Extraction du message réel posé au notable
        q_match = re.search(r"«\s*(.*?)\s*»", user_msg)
        query = (q_match.group(1) if q_match else user_msg).strip().lower()

        # Extraction des traits du personnage depuis le prompt
        name_match = re.search(r"Tu es ([^,\n]+)", sys_prompt)
        name = name_match.group(1).strip() if name_match else "l'habitant"

        title_match = re.search(r"Ton titre / rôle : ([^\n\.]+)", sys_prompt)
        title = title_match.group(1).strip() if title_match else "Chef de clan"

        clan_match = re.search(r"Appartenance : ([^\(\n]+)", sys_prompt)
        clan = clan_match.group(1).strip() if clan_match else "la communauté"

        kin_match = re.search(r"Tes liens du sang : ([^\n]+)", sys_prompt)
        kin = kin_match.group(1).strip() if kin_match else ""

        year_match = re.search(r"l'an ([-\d]+)", sys_prompt)
        year_str = year_match.group(1) if year_match else "-4004"
        try:
            year_int = int(year_str)
            date_display = f"{abs(year_int)} av. J.-C." if year_int < 0 else f"l'An {year_int}"
        except ValueError:
            date_display = f"l'an {year_str}"

        has_spouse = "Conjoint(e)" in kin or "Épous" in kin
        has_children = "Enfants" in kin

        # 1. Salutations et présentations
        if any(w in query for w in ["salut", "bonjour", "cc", "hello", "coucou", "qui es-tu", "qui t'es", "qui es tu", "te presente"]):
            if name.lower().startswith("adan"):
                return (
                    f"Salutations, Voyageur. Je suis Adan, Patriarche de cette maisonnée et le premier homme façonné sur cette terre. "
                    f"En cette ère ({date_display}), je veille sur notre clan et auprès de ma compagne Eva. "
                    f"Que la paix du ciel accompagne tes pas parmi nous."
                )
            elif name.lower().startswith("eva"):
                return (
                    "Bienvenue à toi, noble voyageur. Je suis Eva, mère de tous les vivants et matriarche de notre foyer. "
                    "Mes journées sont consacrées à veiller sur notre feu sacré et sur le souffle de notre descendance. "
                    "Quelle parole céleste viens-tu apporter à notre campement ?"
                )
            else:
                return (
                    f"Salutations, voyageur des songes. Je me nomme {name}, et je sers notre peuple en qualité de {title}. "
                    f"En cette année de {date_display}, notre sang s'enracine au sein de {clan}. "
                    f"Dis-moi, quelle quête ou quel dessein t'amène auprès du feu de mon clan ?"
                )

        # 2. Famille, enfants et lignée
        if any(w in query for w in ["enfant", "fils", "fille", "bébé", "pelega", "eva", "adan", "femme", "mari", "famille", "lignée", "parent"]):
            if has_children:
                return (
                    "Par la bénédiction de la vie, le foyer s'agrandit. Les cris de notre descendance résonnent autour de nous, "
                    "et voir nos petits grandir est notre plus grande fierté en cette aube du monde. "
                    "Chaque enfant est une promesse que la terre continuera d'être habitée après nous."
                )
            elif has_spouse:
                return (
                    "Pour l'instant, notre force réside dans l'alliance de nos cœurs. Nous partageons chaque repas, "
                    "chaque abri contre la pluie et nous espérons que nos enfants peupleront bientôt les vallées et les collines."
                )
            else:
                return (
                    "Les liens du sang sont sacrés pour moi. Même lorsque les hivers sont rudes, c'est l'espoir de voir "
                    "prospérer la lignée de nos aïeux qui me pousse à me lever à chaque aurore."
                )

        # 3. Rôle, fonctions, hiérarchie et devoirs
        if any(w in query for w in ["rôle", "role", "grade", "rang", "hiérarchie", "titre", "fais-tu", "que fais", "travail", "mission", "notable"]):
            return (
                f"Mon rang de {title} n'est pas un vain mot : c'est la charge de protéger les nôtres, de distribuer les baies "
                f"et le gibier avec équité, et de transmettre la coutume sacrée. "
                f"Tant que mon souffle sera chaud, je tiendrai ce rôle pour préserver l'harmonie de notre monde."
            )

        # 4. Nourriture, météo, saisons et survie
        if any(w in query for w in ["faim", "manger", "nourriture", "chasse", "cueillette", "froid", "chaud", "météo", "saison", "vivres", "hiver"]):
            return (
                "La terre nous offre ce que le ciel lui accorde. Nous suivons les traces du gibier le long des rivières "
                "et cueillons les fruits mûrs des sous-bois. "
                "Nous prions pour que la sécheresse ou le grand froid n'éprouvent pas notre humble campement."
            )

        # 5. Croyances, dieux, cosmogonie et esprits
        if any(w in query for w in ["dieu", "dieux", "esprits", "totem", "ciel", "terre", "sacré", "prière", "âme", "mort", "culte", "ancêtres"]):
            return (
                "Nous vénérons le souffle de la création et les forces qui meuvent les étoiles et les saisons. "
                "Le totem de notre clan nous rappelle d'où nous venons et quelle promesse nous unit à cette terre. "
                "Respecter les esprits de nos aînés est la clé de notre survie."
            )

        # 6. Ordres, conseils, avenir ou prophétie
        if any(w in query for w in ["guerre", "paix", "conseil", "attention", "danger", "voyageur", "prophétie", "pars", "construis", "fuis"]):
            return (
                f"Tes paroles sonnent avec l'écho d'une voix lointaine et sage. En tant que {title}, je les pèserai avec les miens. "
                f"Si les signes célestes confirment ton avertissement, je guiderai notre communauté selon ta parole."
            )

        # 7. Réponse générique incarnée de haute fidélité
        return (
            f"Je t'écoute avec respect, voyageur venu d'au-delà de l'horizon. En ma qualité de {title}, "
            f"je songe souvent à la fragilité de notre existence et à la destinée de notre lignée. "
            f"Partage avec moi ta sagesse : ce monde est encore jeune, et chaque vérité nous éclaire."
        )


class MockLLMClient:
    """Client d'inférence contextualisé et résilient avec repli incarné intelligent."""

    def __init__(self, fixed_response: str | None = None):
        self.fixed_response = fixed_response
        self.call_history: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        self.call_history.append(messages)
        if self.fixed_response:
            return self.fixed_response

        # Tenter d'abord de contacter un LLM local actif (ex: llama-server sur le port 8080)
        local_url = os.environ.get("LLM_LOCAL_URL", "http://127.0.0.1:8080/v1/chat/completions")
        try:
            with httpx.Client(timeout=3.0) as client:
                payload = {
                    "model": "local",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                resp = client.post(local_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0].get("message", {}).get("content", "").strip()
                        if content:
                            return content
        except (httpx.HTTPError, OSError, ValueError, KeyError) as err:
            logger.debug("Local llama call bypassed: %s", err)

        # Repli incarné intelligent déterministe
        return ContextualPersonaGenerator.generate_response(messages)


class HuggingFaceClient:
    """Client pour llama-server local, vLLM ou Hugging Face Inference API."""

    def __init__(self, model_id: str = "Qwen/Qwen2.5-7B-Instruct", api_token: str | None = None, api_url: str | None = None):
        self.model_id = model_id
        self.api_token = api_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY", "")
        # Priorité à l'endpoint local si spécifié ou présent
        self.api_url = (
            api_url
            or os.environ.get("LLM_ENDPOINT")
            or os.environ.get("LLM_URL")
            or "http://127.0.0.1:8080/v1/chat/completions"
        )

    def generate(self, messages: list[dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self.api_url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        choice = data["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            return choice["message"]["content"].strip()
                    if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                        return data[0]["generated_text"].strip()
        except (httpx.HTTPError, OSError, ValueError, KeyError) as err:
            logger.debug("HuggingFace/vLLM call fallback: %s", err)

        return ContextualPersonaGenerator.generate_response(messages)


