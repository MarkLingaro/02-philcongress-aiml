"""
Embedder — generates vector embeddings using nomic-embed-text via Ollama.

Abstract-first strategy:
  text = f"{bill_no} {title_full} {abstract}"
  One vector per bill — simple, fast, no PDF needed.

768 dimensions (nomic-embed-text default).
"""

import asyncio

import httpx
import structlog

from src.core.config import get_settings

log = structlog.get_logger(__name__)

EMBED_DIM = 768  # nomic-embed-text output dimensions


class Embedder:
    """
    Generates embeddings via Ollama's nomic-embed-text model.

    Usage:
        async with Embedder() as embedder:
            vector = await embedder.embed("some text")
            vectors = await embedder.embed_batch(["text1", "text2"])
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.settings.ollama_base_url,
            timeout=60.0,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns a 768-dim vector."""
        assert self._client, "Use as async context manager"

        if not text.strip():
            # Return zero vector for empty text
            return [0.0] * EMBED_DIM

        response = await self._client.post(
            "/api/embeddings",
            json={
                "model": self.settings.ollama_embed_model,
                "prompt": text,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """
        Embed multiple texts. Processes in batches to avoid overwhelming Ollama.
        Returns vectors in the same order as input texts.
        """
        all_vectors = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            log.info(
                "Embedding batch",
                batch_num=i // batch_size + 1,
                batch_size=len(batch),
                total=len(texts),
            )
            # Run batch concurrently within the batch
            vectors = await asyncio.gather(*[self.embed(text) for text in batch])
            all_vectors.extend(vectors)

        return all_vectors
