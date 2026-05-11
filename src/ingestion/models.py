"""
Pydantic models for HREP API responses.

These are NOT the SQLAlchemy ORM models (those are in src/db/models.py).
These are data transfer objects — they validate and parse the raw API JSON
before it gets loaded into the database.
"""

from pydantic import BaseModel, field_validator


class CongressRef(BaseModel):
    """One entry from /system-config/reference-congress."""

    id: int  # API internal ID (103 = 20th, 19 = 19th, ...)
    key: str  # always "congress"
    value: str  # "19th Congress"
    remarks: str = ""  # human congress number as string e.g. "19"

    @property
    def number(self) -> int | None:
        """Human-readable congress number, or None for 'All Congress' (id=0)."""
        try:
            return int(self.remarks)
        except (ValueError, TypeError):
            return None


class LegislatorRef(BaseModel):
    """One entry from /house-members/ddl-reference."""

    id: int
    author_id: str  # HREP internal code e.g. "F061", "K001"
    fullname: str
    nick_name: str = ""
    membership: list[int] = []  # list of congress IDs this person served in


class BillAuthor(BaseModel):
    """One entry in bill.authors[] — principal author."""

    id: int
    name: str
    name_code: str = ""  # short display name e.g. "Romualdez (F.M.)"
    sequence_no: int = 1  # 1 = first/principal author
    date: str | None = None
    journal_no: str = ""
    session_no: str = ""


class BillCoauthor(BaseModel):
    """One entry in bill.coauthors[] — co-author."""

    id: int
    name: str
    name_code: str = ""
    date: str | None = None
    journal_no: str = ""


class HrepBill(BaseModel):
    """
    One bill record from POST /bills/search response.
    Maps directly to the bills + bill_authorships tables.
    """

    id: int  # HREP internal bill ID
    congress: int  # congress API ID (19, 18, ...)
    bill_no: str = ""  # e.g. "HB00002"
    bill_no_f: str = ""  # final/mother number e.g. "HB06518"
    session_no: str = ""  # e.g. "19-1RS-002"
    significance: int | None = None  # raw significance code
    significance_desc: str = ""  # "National" | "Local"
    title_full: str = ""
    title_short: str = ""
    abstract: str = ""  # explanatory note — primary RAG text
    status: str = ""
    status_order: float | None = None
    date_filed: str | None = None
    mother_bill_no: str = ""
    mother_status: str = ""
    text_as_filed: str = ""  # direct PDF URL
    author: str = ""  # principal author_id code
    authors: list[BillAuthor] = []
    coauthors: list[BillCoauthor] = []
    congress_desc: str = ""

    @field_validator(
        "bill_no",
        "bill_no_f",
        "session_no",
        "title_full",
        "abstract",
        "status",
        "mother_bill_no",
        "mother_status",
        "text_as_filed",
        mode="before",
    )
    @classmethod
    def empty_none(cls, v):
        """Convert None to empty string for text fields."""
        return v or ""

    @property
    def rag_text(self) -> str:
        """Text used for embedding — title + abstract."""
        parts = []
        if self.bill_no:
            parts.append(self.bill_no)
        if self.title_full:
            parts.append(self.title_full)
        if self.abstract:
            parts.append(self.abstract)
        return " ".join(parts).strip()

    @property
    def has_rag_content(self) -> bool:
        """True if there is enough text to embed."""
        return len(self.rag_text) > 20


class BillSearchResponse(BaseModel):
    """Wrapper for POST /bills/search response.data."""

    pageCount: int = 0
    count: int = 0
    rows: list[HrepBill] = []
