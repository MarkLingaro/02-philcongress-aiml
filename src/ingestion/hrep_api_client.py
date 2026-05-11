"""
HREP API Client — api.congress.gov.ph

Primary data source for PhilCongressAI.
Reverse-engineered from the Philippine House of Representatives LEGIS system.

Covers: 8th–19th Congress (20th has no bills loaded yet)
Rate limit: 5,000 req/hour — no throttling needed for ingestion
Auth: X-Hrep-Website-Backend header (public token from website JS)
"""

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import get_settings
from src.ingestion.models import (
    BillSearchResponse,
    CongressRef,
    HrepBill,
    LegislatorRef,
)

log = structlog.get_logger(__name__)


class HrepApiClient:
    """
    Async client for api.congress.gov.ph.

    Usage:
        async with HrepApiClient() as client:
            legislators = await client.get_legislators()
            async for bill in client.iter_bills(congress=19):
                process(bill)
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.settings.hrep_api_base_url,
            headers={
                "Content-Type": "application/json",
                "X-Hrep-Website-Backend": self.settings.hrep_api_token,
                "Accept": "*/*",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=30),
        reraise=True,
    )
    async def _get(self, path: str) -> dict:
        """GET request with retry."""
        assert self._client, "Use as async context manager"
        response = await self._client.get(path)
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=30),
        reraise=True,
    )
    async def _post(self, path: str, payload: dict) -> dict:
        """POST request with retry."""
        assert self._client, "Use as async context manager"
        response = await self._client.post(path, json=payload)
        response.raise_for_status()
        return response.json()

    def _snapshot_path(self, filename: str) -> Path:
        """Return path for saving raw API snapshots."""
        path = Path("data/snapshots") / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ── Reference data ────────────────────────────────────────────

    async def get_congress_map(self) -> dict[int, int]:
        """
        Returns mapping of human congress number → API congress ID.
        e.g. {20: 103, 19: 19, 18: 18, ...}

        The 20th Congress uses ID 103 internally — a quirk of the API.
        """
        log.info("Fetching congress reference data")
        data = await self._get("/system-config/reference-congress")

        congress_map = {}
        refs = [CongressRef(**row) for row in data.get("data", [])]

        for ref in refs:
            if ref.id == 0:
                continue  # skip "All Congress" entry
            if ref.number is not None:
                congress_map[ref.number] = ref.id

        log.info("Congress map loaded", count=len(congress_map))

        # Save snapshot
        snapshot = self._snapshot_path("congress_map.json")
        snapshot.write_text(json.dumps(congress_map, indent=2))

        return congress_map

    async def get_legislators(self) -> list[LegislatorRef]:
        """
        Returns all legislators who have ever served in the House.
        Covers 8th Congress to present (~1,100+ records).
        """
        log.info("Fetching legislator reference data")
        data = await self._get("/house-members/ddl-reference")

        legislators = [LegislatorRef(**row) for row in data.get("data", [])]
        log.info("Legislators loaded", count=len(legislators))

        # Save snapshot
        snapshot = self._snapshot_path("legislators.json")
        snapshot.write_text(
            json.dumps([leg.model_dump() for leg in legislators], indent=2)
        )

        return legislators

    # ── Bills ─────────────────────────────────────────────────────

    async def search_bills(
        self,
        congress_id: int,
        page: int = 0,
        limit: int = 999,
        title: str = "",
        significance: str = "Both",
    ) -> BillSearchResponse:
        """
        Search bills for a given congress ID (not congress number).
        Use get_congress_map() to convert congress number → ID.
        """
        payload = {
            "page": page,
            "limit": limit,
            "congress": congress_id,
            "significance": significance,
            "field": "Title",
            "numbers": "",
            "title": title,
            "author_id": "",
            "author_type": "Both",
            "committee_id": "",
        }
        data = await self._post("/bills/search", payload)
        return BillSearchResponse(**data.get("data", {}))

    async def iter_bills(
        self,
        congress: int,
        limit: int = 999,
    ) -> AsyncGenerator[HrepBill, None]:
        """
        Async generator that yields all bills for a given congress number.
        Handles pagination automatically.

        Usage:
            async for bill in client.iter_bills(congress=19):
                await load_bill(bill)
        """
        # Get the API congress ID
        congress_map = await self.get_congress_map()
        congress_id = congress_map.get(congress)

        if congress_id is None:
            log.error("Unknown congress number", congress=congress)
            return

        log.info(
            "Starting bill iteration",
            congress=congress,
            congress_id=congress_id,
        )

        page = 0
        total_yielded = 0

        while True:
            log.info("Fetching bills page", page=page, congress=congress)

            response = await self.search_bills(
                congress_id=congress_id,
                page=page,
                limit=limit,
            )

            if not response.rows:
                log.info("No more bills", page=page)
                break

            # Save raw snapshot
            snapshot = self._snapshot_path(
                f"congress_{congress}/bills_page_{page:04d}.json"
            )
            snapshot.write_text(
                json.dumps(
                    [b.model_dump() for b in response.rows],
                    indent=2,
                    default=str,
                )
            )

            for bill in response.rows:
                total_yielded += 1
                yield bill

            log.info(
                "Page complete",
                page=page,
                page_count=response.pageCount,
                total_so_far=total_yielded,
                grand_total=response.count,
            )

            # Check if we've reached the last page
            if page >= response.pageCount - 1:
                break

            page += 1

        log.info(
            "Bill iteration complete",
            congress=congress,
            total=total_yielded,
        )
