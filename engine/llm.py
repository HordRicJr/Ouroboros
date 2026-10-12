"""Client d'inférence LLM pour les notables et le narrateur.

Prend en charge :
- MockLLMClient (déterministe, pour les tests sans réseau/GPU)
- HuggingFaceInferenceClient (API Serverless ou Endpoint dédié Hugging Face / vLLM AWS)
"""
from __future__ import annotations

import os
import json
from typing import Protocol, Any
import httpx


class LLMClient(Protocol):
    def generate(self, messages: list[dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        ...


class MockLLMClient:
    """Simulateur LLM déterministe pour tests unitaires et intégration sans appel API."""
    def __init__(self, fixed_response: str | None = None):
        self.fixed_response = fixed_response
        self.call_history: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        self.call_history.append(messages)
        if self.fixed_response:
            return self.fixed_response
        # Réponse contextuelle simulée cohérente avec le dernier message
        user_msg = messages[-1].get("content", "") if messages else ""
        return f"[Pensée de l'habitant] Par les cieux et la terre de mes ancêtres, je ressens le souffle du vent et je songe à mes proches. ({user_msg[:30]}...)"


class HuggingFaceClient:
    """Client pour Hugging Face Inference API ou vLLM déployé sur AWS."""
    def __init__(self, model_id: str = "Qwen/Qwen2.5-7B-Instruct", api_token: str | None = None, api_url: str | None = None):
        self.model_id = model_id
        self.api_token = api_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY", "")
        # Si api_url personnalisé (ex: endpoint privé AWS vLLM), sinon HF inference router
        self.api_url = api_url or f"https://api-inference.huggingface.co/models/{model_id}/v1/chat/completions"

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
        
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self.api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Compatible OpenAI format (vLLM / Hugging Face chat completions)
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"].strip()
            # Format text direct HF alternatif
            if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                return data[0]["generated_text"].strip()
            return str(data)
