"""
LLM Service — backed by AWS Bedrock (Claude Sonnet 4.5 + Titan Embeddings).

Keeps the same interface (generate, generate_structured, embed, embed_batch,
is_available) so all existing imports continue to work unchanged.
The module-level export is still named `ollama_service` to avoid touching
every import across the codebase.
"""

import asyncio
import json
import boto3
from app.config import get_settings

settings = get_settings()


class LLMService:
    def __init__(self):
        self.model_id = settings.aws_bedrock_model_id
        self.embed_model_id = settings.aws_bedrock_embed_model_id
        self.region = settings.aws_region
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
        return self._client

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        system_blocks = [{"text": system}] if system else []
        messages = [{"role": "user", "content": [{"text": prompt}]}]

        response = await asyncio.to_thread(
            self.client.converse,
            modelId=self.model_id,
            messages=messages,
            system=system_blocks,
            inferenceConfig={"temperature": temperature, "maxTokens": 4096},
        )
        return response["output"]["message"]["content"][0]["text"]

    async def generate_structured(self, prompt: str, system: str = "") -> dict:
        raw = await self.generate(prompt, system, temperature=0.3)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass
        return {"raw_response": raw}

    async def embed(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text, "dimensions": 1024})
        response = await asyncio.to_thread(
            self.client.invoke_model,
            modelId=self.embed_model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            emb = await self.embed(text)
            embeddings.append(emb)
        return embeddings

    async def is_available(self) -> bool:
        try:
            await asyncio.to_thread(
                self.client.list_foundation_models, byOutputModality="TEXT"
            )
            return True
        except Exception:
            return False


# Keep export name as `ollama_service` so all imports work without changes
ollama_service = LLMService()
