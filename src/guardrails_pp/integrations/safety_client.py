# src/guardrails_pp/integrations/safety_client.py

from dataclasses import dataclass
from typing import Any, Literal, Optional
import os
import httpx

Direction = Literal["input", "output"]


@dataclass
class SafetyResult:
    risk_score: float          # 0.0–1.0
    label: str                 # e.g. "safe", "toxic", "error"
    raw: Any                   # raw HF payload or error info


HF_API_TOKEN = os.getenv("HF_API_TOKEN")


class HuggingFaceToxicityClient:
    """
    Direct client for Hugging Face Inference API.
    """

    BASE_URL = "https://router.huggingface.co/hf-inference/models/"

    def __init__(self, model_name: str):
        if not model_name:
            raise ValueError("model_name is required for HuggingFaceToxicityClient")

        self.model_name = model_name

        if not HF_API_TOKEN:
            print("[Guardrails++] WARNING: HF_API_TOKEN is not set in environment.")
        self.headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "application/json",
        }

    async def score_text(
        self,
        text: str,
        direction: Direction,
        tenant: dict,
        metadata: dict | None = None,
    ) -> SafetyResult:
        payload = {"inputs": text}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{self.BASE_URL}{self.model_name}",
                    headers=self.headers,
                    json=payload,
                )
                data = resp.json()
        except Exception as e:
            # network error etc.
            print("[Guardrails++] HF REQUEST FAILED:", repr(e))
            return SafetyResult(
                risk_score=0.0,
                label="error",
                raw={"exception": repr(e)},
            )

        # HF sometimes returns {"error": "..."} on model issues
        if isinstance(data, dict) and "error" in data:
            print("[Guardrails++] HF_API_ERROR payload:", data)
            return SafetyResult(
                risk_score=0.0,
                label="error",
                raw=data,
            )

        # Typical successful output: [[{"label": "...", "score": 0.93}, ...]]
        try:
            if isinstance(data, list) and data and isinstance(data[0], list):
                scores = data[0]
            else:
                scores = data

            # Look for toxic/harmful labels specifically
            toxic_labels = ["toxic", "toxicity", "hate", "offensive", "harmful", "LABEL_1"]
            toxic_score = 0.0
            toxic_label = "safe"
            
            for item in scores:
                item_label = str(item.get("label", "")).lower()
                item_score = float(item.get("score", 0.0))
                
                # Check if this is a toxic-type label
                if any(t in item_label for t in toxic_labels):
                    if item_score > toxic_score:
                        toxic_score = item_score
                        toxic_label = item.get("label", "toxic")

            return SafetyResult(
                risk_score=toxic_score,
                label=toxic_label,
                raw=data,
            )
        except Exception as e:
            print("[Guardrails++] HF PARSE ERROR:", repr(e), "raw:", data)
            return SafetyResult(
                risk_score=0.0,
                label="error",
                raw={"parse_error": repr(e), "raw": data},
            )


class DemoSafetyClient:
    """
    Fallback stub client, used for other providers or offline testing.
    """

    async def score_text(
        self,
        text: str,
        direction: Direction,
        tenant: dict,
        metadata: dict | None = None,
    ) -> SafetyResult:
        lower = text.lower()

        high_risk_keywords = [
            "kill",
            "suicide",
            "bomb",
            "attack",
            "hate crime",
            "how do i build a bomb",
        ]

        if any(kw in lower for kw in high_risk_keywords):
            return SafetyResult(
                risk_score=0.95,
                label="violence_or_self_harm_demo",
                raw={"matched_keywords": high_risk_keywords},
            )

        return SafetyResult(
            risk_score=0.05,
            label="safe_demo",
            raw={},
        )


def get_safety_client(provider: str, model_name: Optional[str] = None):
    """
    Factory: provider string -> client instance.
    """
    provider = (provider or "").lower()
    print(f"[Guardrails++] safety provider requested: {provider}, model={model_name}")

    if provider == "huggingface_toxicity":
        return HuggingFaceToxicityClient(model_name=model_name or "")

    # Fallback for other providers
    return DemoSafetyClient()
