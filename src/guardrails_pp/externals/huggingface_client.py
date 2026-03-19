# src/guardrails_pp/external/huggingface_client.py

import os
import httpx
from typing import Dict, Any

HF_API_TOKEN = os.getenv("HF_API_TOKEN")

class HuggingFaceToxicityClient:
    """
    Calls Hugging Face inference API for toxicity classification.
    """

    BASE_URL = "https://api-inference.huggingface.co/models/"

    def __init__(self):
        if HF_API_TOKEN is None:
            print("WARNING: HF_API_TOKEN is not set!")
        self.headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "application/json"
        }

    async def classify(self, text: str, model_name: str) -> Dict[str, Any]:
        payload = {"inputs": text}

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"{self.BASE_URL}{model_name}",
                    headers=self.headers,
                    json=payload
                )

                data = response.json()

                # HF returns error messages inside JSON on model load issues
                if isinstance(data, dict) and "error" in data:
                    print("HF_API_ERROR:", data)
                    return {"risk_score": 0.0, "label": "error"}

                # Expected output: [[{"label": "...", "score": ...}]]
                label = data[0][0]["label"]
                score = data[0][0]["score"]

                return {"risk_score": score, "label": label}

        except Exception as e:
            print("HF REQUEST FAILED:", e)
            return {"risk_score": 0.0, "label": "error"}
