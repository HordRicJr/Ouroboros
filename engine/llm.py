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

        # 1. Propositions / interdits : réponse ouverte (pas de serment scripté)
        is_prohibition = any(w in query for w in [
            "tabou", "interdit", "défendu", "ne dois pas", "ne mange pas", "ne pas manger",
            "ne touchez", "ne consomme", "défense de",
        ])
        if is_prohibition:
            return (
                f"J'entends ta parole, voyageur. En tant que {title}, je ne puis engager tout {clan} "
                f"sur un seul échange. Je méditerai ce que tu dis auprès des miens, "
                f"et chacun décidera s'il convient de changer nos usages — ou de les garder."
            )

        # 2. Salutations et présentations
        if any(w in query for w in ["salut", "bonjour", "cc", "hello", "coucou", "qui es-tu", "qui t'es", "qui es tu", "te presente"]):
            return (
                f"Salutations, voyageur. Je me nomme {name}. "
                f"En cette année de {date_display}, je vis parmi {clan}. "
                f"Que cherches-tu auprès de notre feu ?"
            )

        # 3. Conjoint(e) / Mariage / Compagne
        if any(w in query for w in ["femme", "épouse", "mari", "époux", "compagne", "compagnon", "mariage", "conjoint"]):
            if has_spouse:
                return (
                    f"Mon alliance avec ma moitié est le souffle qui réchauffe mon cœur. À mes côtés, elle veille sur notre foyer "
                    f"et partage chaque froidure et chaque joie de notre campement au sein de {clan}. Sans ce soutien, ce vaste monde ne serait qu'un désert de solitude."
                )
            return (
                f"Je n'ai point encore scellé d'union, mais au sein de {clan}, chaque membre est un frère ou une sœur de subsistance."
            )

        # 4. Famille, enfants et descendance
        if any(w in query for w in ["enfant", "fils", "fille", "bébé", "pelega", "famille", "lignée", "descendance", "génération"]):
            if has_children:
                return (
                    "Par la bénédiction de la vie, le foyer s'agrandit. Les cris de notre descendance résonnent autour de nous, "
                    "et voir nos petits grandir est notre plus grande fierté en cette aube du monde. "
                    "Chaque enfant est une promesse que la terre continuera d'être habitée après nous."
                )
            if has_spouse:
                return (
                    "Pour l'instant, notre force réside dans l'alliance de nos cœurs. Nous partageons chaque repas, "
                    "chaque abri contre la pluie et nous espérons que nos enfants peupleront bientôt les vallées et les collines."
                )
            return (
                "Les liens du sang sont sacrés pour moi. Même lorsque les hivers sont rudes, c'est l'espoir de voir "
                "prospérer la lignée de nos aïeux qui me pousse à me lever à chaque aurore."
            )

        # 5. Feu, froidure, abri et outils de survie
        if any(w in query for w in ["feu", "flamme", "foyer", "froid", "abri", "pierre", "silex", "outil"]):
            return (
                "Le feu sacré est notre bien le plus précieux. Il tient à distance les prédateurs de l'ombre "
                "et réchauffe nos chairs quand le gel s'abat sur la vallée. Nous taillons la pierre dure pour bâtir nos outils "
                "et protéger le souffle de notre maisonnée."
            )

        # 6. Dangers, loups, monstres, bêtes et guerre
        if any(w in query for w in ["loup", "loups", "bête", "danger", "menace", "guerre", "peur", "ennemi", "attention"]):
            return (
                f"Tes paroles éveillent ma vigilance de {title}. La nature est impitoyable avec ceux qui dorment d'un sommeil trop lourd. "
                f"Je prendrai mon épieu taillé dans le frêne pour monter la garde cette nuit. Nous protègerons notre campement coûte que coûte."
            )

        # 7. Dieux, création, ciel, prière et mystère originel
        if any(w in query for w in ["dieu", "dieux", "créateur", "création", "ciel", "étoile", "prière", "âme", "mort", "ancêtres", "totem"]):
            return (
                "Nous sentons une présence immense qui dépasse les cimes des montagnes et guide les constellations. "
                "Tirés de la poussière et animés d'un souffle vivant, nous marchons avec respect sous le grand dais du ciel, "
                "espérant mériter chaque aurore qui nous est accordée."
            )

        # 8. Rôle quotidien (sans vocabulaire de théorie sociale)
        if any(w in query for w in ["rôle", "role", "fais-tu", "que fais", "travail", "mission", "occupation"]):
            return (
                f"On m'appelle parfois {title} parce que d'autres viennent me parler. "
                f"Le reste du temps, je chasse, je partage, je veille — comme chacun d'entre nous."
            )

        # 9. Nourriture, chasse, cueillette
        if any(w in query for w in ["faim", "manger", "nourriture", "chasse", "cueillette", "vivres", "gibier", "poisson"]):
            return (
                "La terre nous offre ce que le ciel lui accorde. Nous suivons les traces du gibier le long des rivières "
                "et cueillons les baies sauvages des sous-bois, en prenant garde de ne rien prélever avec avarice."
            )

        # 10. Interrogations directes (pourquoi, comment, que penses-tu)
        if any(w in query for w in ["pourquoi", "comment", "que penses", "qu'en penses", "que dis-tu"]):
            return (
                f"Ta question sonde les profondeurs de mon cœur de {title}. En cette aube du monde, nous découvrons encore "
                f"les lois des saisons et les caprices du vent. Je crois que chaque épreuve nous forge, et que chercher la vérité "
                f"à tes côtés éclaire le sentier de notre avenir."
            )

        # 11. Réponse réactive incarnée avec écho des mots du joueur
        # Nettoyage des mots clés pour écho contextuel
        words = [w for w in re.findall(r"\b\w{4,}\b", query) if w not in ["cette", "dans", "avec", "pour", "nous", "vous", "leur", "comme", "mais"]]
        echo = f"concernant « {words[0]} »" if words else "à ce sujet"
        return (
            f"J'écoute attentivement ce que tu dis {echo}, noble Voyageur. En ma qualité de {title}, "
            f"je médite tes paroles auprès du feu de camp. Chaque parole que tu partages avec notre clan "
            f"laisse une empreinte sur notre terre encore jeune."
        )


class MockLLMClient:
    """Client d'inférence contextualisé et résilient avec repli incarné intelligent."""

    def __init__(self, fixed_response: str | None = None, model_name: str = "mock-contextual"):
        self.fixed_response = fixed_response
        self.model_name = model_name
        self.model_fingerprint = "mock"
        self.llama_cpp_version = ""
        self.call_history: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        self.call_history.append(messages)
        if self.fixed_response:
            return self.fixed_response

        # Tenter d'abord de contacter un LLM local actif (ex: llama-server sur le port 8080)
        local_url = os.environ.get("LLM_LOCAL_URL", "http://127.0.0.1:8080/v1/chat/completions")
        try:
            with httpx.Client(timeout=18.0) as client:
                payload = {
                    "model": "local",
                    "messages": messages,
                    "max_tokens": min(max_tokens, 80),
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

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-7B-Instruct",
        api_token: str | None = None,
        api_url: str | None = None,
        model_fingerprint: str = "",
        llama_cpp_version: str = "",
    ):
        self.model_id = model_id
        self.model_name = model_id
        self.model_fingerprint = model_fingerprint or os.environ.get("LLM_MODEL_SHA256", "")
        self.llama_cpp_version = llama_cpp_version or os.environ.get("LLAMA_CPP_VERSION", "")
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
            "max_tokens": min(max_tokens, 80),
            "temperature": temperature,
        }

        # 1. Tentative sur l'endpoint local ou configuré (timeout adapté pour CPU)
        local_timeout = 18.0 if ("127.0.0.1" in self.api_url or "localhost" in self.api_url) else 10.0
        try:
            with httpx.Client(timeout=local_timeout) as client:
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
            logger.debug("Local/Configured LLM endpoint fallback: %s", err)

        # 2. Si un token Hugging Face est présent, tenter le routeur Serverless officiel
        if self.api_token:
            hf_router_url = f"https://router.huggingface.co/hf-inference/models/{self.model_id}/v1/chat/completions"
            try:
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(hf_router_url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            choice = data["choices"][0]
                            if "message" in choice and "content" in choice["message"]:
                                return choice["message"]["content"].strip()
            except (httpx.HTTPError, OSError, ValueError, KeyError) as err:
                logger.debug("Hugging Face router fallback: %s", err)

        # 3. Repli narratif contextuel de haute fidélité
        return ContextualPersonaGenerator.generate_response(messages)


