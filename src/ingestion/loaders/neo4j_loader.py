"""
Neo4j loader — creates nodes and relationships from HREP API data.

Nodes:    Person, Bill, Congress
Edges:    SPONSORED, CO_SPONSORED, SERVED_IN

All Cypher uses MERGE (not CREATE) so it's safe to re-run.
"""

import structlog
from neo4j import AsyncGraphDatabase

from src.core.config import get_settings
from src.ingestion.models import CongressRef, HrepBill, LegislatorRef

log = structlog.get_logger(__name__)


class Neo4jLoader:
    """
    Async Neo4j loader.

    Usage:
        async with Neo4jLoader() as loader:
            await loader.upsert_congress(ref)
            await loader.upsert_legislator(leg, congress_ids=[19, 18])
            await loader.upsert_bill(bill)
    """

    def __init__(self):
        self.settings = get_settings()
        self._driver = None

    async def __aenter__(self):
        self._driver = AsyncGraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )
        return self

    async def __aexit__(self, *args):
        if self._driver:
            await self._driver.close()

    async def upsert_congress(self, ref: CongressRef) -> None:
        """Create or update a Congress node."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (c:Congress {id: $id})
                SET c.name   = $name,
                    c.number = $number
                """,
                id=ref.id,
                name=ref.value,
                number=ref.number or 0,
            )

    async def upsert_legislator(
        self,
        leg: LegislatorRef,
    ) -> None:
        """Create or update a Person node."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (p:Person {id: $id})
                SET p.full_name  = $full_name,
                    p.nick_name  = $nick_name,
                    p.membership = $membership
                """,
                id=leg.author_id,
                full_name=leg.fullname,
                nick_name=leg.nick_name or "",
                membership=leg.membership,
            )

    async def upsert_bill(self, bill: HrepBill) -> None:
        """Create or update a Bill node."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (b:Bill {id: $id})
                SET b.bill_no          = $bill_no,
                    b.bill_no_f        = $bill_no_f,
                    b.title_full       = $title_full,
                    b.status           = $status,
                    b.status_order     = $status_order,
                    b.significance     = $significance,
                    b.congress_id      = $congress_id,
                    b.text_as_filed    = $text_as_filed
                """,
                id=str(bill.id),
                bill_no=bill.bill_no,
                bill_no_f=bill.bill_no_f,
                title_full=bill.title_full,
                status=bill.status,
                status_order=bill.status_order or 0.0,
                significance=bill.significance_desc,
                congress_id=bill.congress,
                text_as_filed=bill.text_as_filed,
            )

    async def upsert_sponsored_edge(
        self,
        author_id: str,
        bill_id: str,
        sequence_no: int = 1,
    ) -> None:
        """Create SPONSORED edge between Person and Bill."""
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (p:Person {id: $author_id})
                MATCH (b:Bill   {id: $bill_id})
                MERGE (p)-[r:SPONSORED]->(b)
                SET r.sequence_no = $sequence_no,
                    r.role        = 'author'
                """,
                author_id=author_id,
                bill_id=bill_id,
                sequence_no=sequence_no,
            )

    async def upsert_bill_with_edges(
        self,
        bill: HrepBill,
        legislator_ids: set[str],
    ) -> None:
        """
        Convenience method: upsert bill node + all authorship edges.
        Only creates edges for legislators that exist as Person nodes.
        """
        await self.upsert_bill(bill)

        bill_id = str(bill.id)

        # Principal author edge (sequence_no == 1, author_id from bill.author)
        if bill.author and bill.author in legislator_ids:
            await self.upsert_sponsored_edge(
                author_id=bill.author,
                bill_id=bill_id,
                sequence_no=1,
            )
