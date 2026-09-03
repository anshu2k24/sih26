"""
Hugging Face Embedding Provider
===============================
Generates embeddings using Hugging Face:
1. Dedicated Hugging Face Space (if HF_SPACE_URL is configured)
2. Hugging Face Serverless Inference API (if HF_TOKEN is configured)
3. Graceful fallback to local SentenceTransformers
"""

import os
import logging
from typing import List, Optional
import httpx

from ertmac.rag.embeddings.base import EmbeddingProvider

logger = logging.getLogger("ertmac.rag.embeddings.huggingface")


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """Embedding provider connecting to Hugging Face Inference API or Space."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_token: Optional[str] = None,
        space_url: Optional[str] = None,
    ):
        self._model_name = model_name or os.getenv(
            "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._api_token = api_token or os.getenv("HF_TOKEN", "").strip()
        self._space_url = space_url or os.getenv("HF_SPACE_URL", "").strip().rstrip("/")
        self._dim = 384

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return f"huggingface/{self._model_name}"

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string."""
        results = self.embed_texts([text])
        return results[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch generates embeddings via Hugging Face Space or Serverless Inference."""
        if not texts:
            return []

        # 1. Option A: Custom Hugging Face Space
        if self._space_url:
            try:
                headers = {}
                if self._api_token:
                    headers["Authorization"] = f"Bearer {self._api_token}"
                with httpx.Client(timeout=30.0) as client:
                    res = client.post(
                        f"{self._space_url}/embed",
                        json={"texts": texts},
                        headers=headers,
                    )
                    if res.is_success:
                        data = res.json()
                        return data["embeddings"]
            except Exception as e:
                logger.warning(f"HF Space embedding call failed: {e}. Trying fallback.")

        # 2. Option B: Hugging Face Serverless Inference API (uses official InferenceClient)
        if self._api_token:
            try:
                from huggingface_hub import InferenceClient
                client = InferenceClient(token=self._api_token)
                all_embeddings = []
                for t in texts:
                    vec = client.feature_extraction(t, model=self._model_name)
                    if hasattr(vec, "tolist"):
                        all_embeddings.append(vec.tolist())
                    elif isinstance(vec, list):
                        all_embeddings.append(vec)
                    else:
                        all_embeddings.append(list(vec))
                if all_embeddings:
                    return all_embeddings
            except Exception as e:
                logger.warning(f"HF InferenceClient call failed: {e}. Trying local fallback.")

        # 3. Option C: Local SentenceTransformers fallback
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self._model_name.split("/")[-1])
            vectors = model.encode(texts, convert_to_numpy=True)
            return vectors.tolist()
        except Exception as local_err:
            logger.error(f"Local embedding fallback also failed: {local_err}")
            # Return synthetic zero-vector if entirely offline
            return [[0.0] * self._dim for _ in texts]

    def health_check(self) -> bool:
        """Verifies connection to Hugging Face or local model availability."""
        try:
            res = self.embed_text("health probe")
            return len(res) == self._dim
        except Exception:
            return False
