"""
Qdrant loader — stores bill embeddings with metadata for RAG retrieval.

Collection: "bills"
Dimensions: 768 (nomic-embed-text)
Distance:   Cosine

Payload schema (what you can filter on in RAG):
  bill_id         : str   — HREP internal bill ID
  bill_no         : str   — e.g. "HB00002"
  bill_no_f       : str   — final number e.g. "HB06518"
  congress        : int   — congress API ID (19, 18, ...)
  congress_number : int   — human number (19, 18, ...)
  status          : str   — human-readable status
  status_order    : float — sortable pipeline stage
  significance    : str   — "National" | "Local"
  has_abstract    : bool  — whether abstract field was non-empty
  text_as_filed   : str   — PDF URL (for future use)
  title           : str   — full title (for display)
  abstract        : str   — explanatory note (for display in RAG)
"""

import uuid

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from src.core.config import get_settings
from src.ingestion.models import HrepBill

log = structlog.get_logger(__name__)

COLLECTION_NAME = "bills"
VECTOR_SIZE = 768


class QdrantLoader:
    """
    Async Qdrant loader for bill embeddings.

    Usage:
        async with QdrantLoader() as loader:
            await loader.ensure_collection()
            await loader.upsert_bill(bill, vector)
            await loader.upsert_bills_batch(bills, vectors)
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: AsyncQdrantClient | None = None

    async def __aenter__(self):
        self._client = AsyncQdrantClient(
            host=self.settings.qdrant_host,
            port=self.settings.qdrant_port,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.close()

    async def ensure_collection(self, force_recreate: bool = False) -> None:
        """
        Create the bills collection if it doesn't exist.
        Set force_recreate=True to wipe and rebuild during development.
        """
        assert self._client, "Use as async context manager"

        existing = await self._client.get_collections()
        names = [c.name for c in existing.collections]

        if COLLECTION_NAME in names and force_recreate:
            log.warning("Deleting existing collection", name=COLLECTION_NAME)
            await self._client.delete_collection(COLLECTION_NAME)
            names.remove(COLLECTION_NAME)

        if COLLECTION_NAME not in names:
            log.info("Creating Qdrant collection", name=COLLECTION_NAME)
            await self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            log.info("Collection created", name=COLLECTION_NAME)
        else:
            log.info("Collection already exists", name=COLLECTION_NAME)

    def _bill_to_payload(self, bill: HrepBill) -> dict:
        """Convert a bill model to Qdrant payload metadata."""
        return {
            "bill_id": str(bill.id),
            "bill_no": bill.bill_no,
            "bill_no_f": bill.bill_no_f,
            "congress": bill.congress,
            "status": bill.status,
            "status_order": bill.status_order or 0.0,
            "significance": bill.significance_desc,
            "has_abstract": bool(bill.abstract),
            "text_as_filed": bill.text_as_filed,
            "title": bill.title_full,
            "abstract": bill.abstract[:500] if bill.abstract else "",
        }

    def _bill_point_id(self, bill: HrepBill) -> str:
        """Generate a stable UUID for a bill's Qdrant point."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bill:{bill.id}"))

    async def upsert_bill(
        self,
        bill: HrepBill,
        vector: list[float],
    ) -> None:
        """Upsert a single bill embedding into Qdrant."""
        assert self._client, "Use as async context manager"

        point = PointStruct(
            id=self._bill_point_id(bill),
            vector=vector,
            payload=self._bill_to_payload(bill),
        )
        await self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point],
        )

    async def upsert_bills_batch(
        self,
        bills: list[HrepBill],
        vectors: list[list[float]],
    ) -> None:
        """Upsert a batch of bill embeddings. Bills and vectors must be same length."""
        assert self._client, "Use as async context manager"
        assert len(bills) == len(vectors), "Bills and vectors must match"

        points = [
            PointStruct(
                id=self._bill_point_id(bill),
                vector=vector,
                payload=self._bill_to_payload(bill),
            )
            for bill, vector in zip(bills, vectors, strict=False)
        ]

        await self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )
        log.info("Batch upserted to Qdrant", count=len(points))

    async def count(self) -> int:
        """Return the number of vectors in the bills collection."""
        assert self._client, "Use as async context manager"
        result = await self._client.count(collection_name=COLLECTION_NAME)
        return result.count
