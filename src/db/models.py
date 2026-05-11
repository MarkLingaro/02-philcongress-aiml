import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.core.database import Base


def _now():
    return datetime.utcnow()


class Congress(Base):
    __tablename__ = "congresses"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    number = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    members = relationship("CongressMembership", back_populates="congress")
    bills = relationship("Bill", back_populates="congress")


class Party(Base):
    __tablename__ = "parties"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    abbreviation = Column(String(20))
    wikidata_id = Column(String(20))
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    memberships = relationship("CongressMembership", back_populates="party")


class Legislator(Base):
    __tablename__ = "legislators"

    id = Column(String(50), primary_key=True)
    full_name = Column(String(300), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    nick_name = Column(String(100))
    birth_date = Column(Date)
    gender = Column(String(20))
    district = Column(String(200))
    province = Column(String(100))
    chamber = Column(String(20))
    wikidata_id = Column(String(20))
    image_url = Column(Text)
    extra = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    congress_memberships = relationship(
        "CongressMembership", back_populates="legislator"
    )
    bill_authorships = relationship("BillAuthorship", back_populates="legislator")
    votes = relationship("Vote", back_populates="legislator")


class CongressMembership(Base):
    __tablename__ = "congress_memberships"
    __table_args__ = (
        UniqueConstraint("legislator_id", "congress_id", name="uq_member_congress"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legislator_id = Column(String(50), ForeignKey("legislators.id"), nullable=False)
    congress_id = Column(Integer, ForeignKey("congresses.id"), nullable=False)
    party_id = Column(String(50), ForeignKey("parties.id"))
    chamber = Column(String(20), nullable=False)
    role = Column(String(100))
    created_at = Column(DateTime, default=_now, nullable=False)

    legislator = relationship("Legislator", back_populates="congress_memberships")
    congress = relationship("Congress", back_populates="members")
    party = relationship("Party", back_populates="memberships")


class Bill(Base):
    __tablename__ = "bills"

    id = Column(String(50), primary_key=True)
    bill_no = Column(String(50))
    bill_no_f = Column(String(50))
    session_no = Column(String(50))
    title_full = Column(Text, nullable=False)
    title_short = Column(Text)
    abstract = Column(Text)
    chamber = Column(String(20))
    congress_id = Column(Integer, ForeignKey("congresses.id"), nullable=False)
    significance_code = Column(Integer)
    significance_desc = Column(String(50))
    status = Column(Text)
    status_order = Column(Numeric)
    date_filed = Column(Date)
    date_signed = Column(Date)
    date_vetoed = Column(Date)
    mother_bill_no = Column(String(50))
    mother_status = Column(Text)
    text_as_filed = Column(Text)
    committee = Column(String(200))
    topic_tags = Column(JSONB, default=list)
    source_url = Column(Text)
    has_pdf = Column(Boolean, default=False)
    pdf_version = Column(String(20))
    pdf_word_count = Column(Integer)
    pdf_parsed_at = Column(DateTime)
    extra = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    congress = relationship("Congress", back_populates="bills")
    authorships = relationship("BillAuthorship", back_populates="bill")
    votes = relationship("Vote", back_populates="bill")


class BillAuthorship(Base):
    __tablename__ = "bill_authorships"
    __table_args__ = (
        UniqueConstraint(
            "bill_id", "legislator_id", "is_coauthor", name="uq_bill_author"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id = Column(String(50), ForeignKey("bills.id"), nullable=False)
    legislator_id = Column(String(50), ForeignKey("legislators.id"), nullable=False)
    is_coauthor = Column(Boolean, default=False)
    sequence_no = Column(Integer)
    journal_no = Column(String(50))
    name_code = Column(String(100))
    date = Column(Date)
    created_at = Column(DateTime, default=_now, nullable=False)

    bill = relationship("Bill", back_populates="authorships")
    legislator = relationship("Legislator", back_populates="bill_authorships")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("bill_id", "legislator_id", "vote_stage", name="uq_vote"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id = Column(String(50), ForeignKey("bills.id"), nullable=False)
    legislator_id = Column(String(50), ForeignKey("legislators.id"), nullable=False)
    vote = Column(String(20), nullable=False)
    vote_stage = Column(String(50))
    vote_date = Column(Date)
    created_at = Column(DateTime, default=_now, nullable=False)

    bill = relationship("Bill", back_populates="votes")
    legislator = relationship("Legislator", back_populates="votes")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=_now, nullable=False)
    last_active = Column(DateTime, default=_now, nullable=False)

    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSONB, default=list)
    feedback = Column(Integer)
    created_at = Column(DateTime, default=_now, nullable=False)

    session = relationship("ChatSession", back_populates="messages")
