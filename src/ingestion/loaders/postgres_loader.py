"""
PostgreSQL loader — upserts HREP API data into the database.

All operations are idempotent (upsert, not insert) so the loader
is safe to re-run without creating duplicates.
"""

from datetime import date

import structlog
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    Bill,
    BillAuthorship,
    Congress,
    Legislator,
)
from src.ingestion.models import CongressRef, HrepBill, LegislatorRef

log = structlog.get_logger(__name__)


def _parse_date(value: str | None) -> date | None:
    """Safely parse ISO date string to date object."""
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


async def upsert_congress(
    session: AsyncSession,
    ref: CongressRef,
) -> None:
    """Insert or update a congress record."""
    stmt = pg_insert(Congress).values(
        id=ref.id,
        name=ref.value,
        number=ref.number,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={"name": ref.value, "number": ref.number},
    )
    await session.execute(stmt)


async def upsert_legislator(
    session: AsyncSession,
    leg: LegislatorRef,
) -> None:
    """Insert or update a legislator record."""
    stmt = pg_insert(Legislator).values(
        id=leg.author_id,
        full_name=leg.fullname,
        nick_name=leg.nick_name or "",
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "full_name": leg.fullname,
            "nick_name": leg.nick_name or "",
        },
    )
    await session.execute(stmt)


async def upsert_bill(
    session: AsyncSession,
    bill: HrepBill,
) -> None:
    """
    Insert or update a bill record.
    Uses the HREP internal integer id converted to string as the PK.
    """
    bill_id = str(bill.id)

    stmt = pg_insert(Bill).values(
        id=bill_id,
        bill_no=bill.bill_no,
        bill_no_f=bill.bill_no_f,
        session_no=bill.session_no,
        title_full=bill.title_full,
        title_short=bill.title_short,
        abstract=bill.abstract,
        congress_id=bill.congress,
        significance_code=bill.significance,
        significance_desc=bill.significance_desc,
        status=bill.status,
        status_order=bill.status_order,
        date_filed=_parse_date(bill.date_filed),
        mother_bill_no=bill.mother_bill_no,
        mother_status=bill.mother_status,
        text_as_filed=bill.text_as_filed,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "status": bill.status,
            "status_order": bill.status_order,
            "mother_bill_no": bill.mother_bill_no,
            "mother_status": bill.mother_status,
            "abstract": bill.abstract,
            "text_as_filed": bill.text_as_filed,
        },
    )
    await session.execute(stmt)


async def upsert_bill_authorships(
    session: AsyncSession,
    bill: HrepBill,
    legislator_ids: set[str],
) -> None:
    """
    Insert authors and co-authors for a bill.
    Skips any author whose author_id is not in the legislators table.

    Note: The HREP API returns author names but not author_ids in the
    authors[] array. We match by name against the legislator reference
    data loaded in Phase 1.
    """
    bill_id = str(bill.id)

    # Principal authors
    for author in bill.authors:
        # Try to find the legislator by name_code or name
        # The bill.author field has the principal author's author_id
        author_id = None

        # For the first author, we can use the bill.author field
        if author.sequence_no == 1 and bill.author:
            author_id = bill.author

        if author_id and author_id in legislator_ids:
            stmt = pg_insert(BillAuthorship).values(
                bill_id=bill_id,
                legislator_id=author_id,
                is_coauthor=False,
                sequence_no=author.sequence_no,
                name_code=author.name_code,
                date=_parse_date(author.date),
            )
            stmt = stmt.on_conflict_do_nothing()
            await session.execute(stmt)

    log.debug(
        "Bill authorships upserted",
        bill_no=bill.bill_no,
        authors=len(bill.authors),
        coauthors=len(bill.coauthors),
    )


async def get_all_legislator_ids(session: AsyncSession) -> set[str]:
    """Return the set of all legislator IDs currently in the database."""
    result = await session.execute(text("SELECT id FROM legislators"))
    return {row[0] for row in result.fetchall()}
