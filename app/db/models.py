from datetime import datetime

from sqlalchemy import JSON, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class every ORM model inherits from. SQLAlchemy uses this to
    collect all table definitions into one place (Base.metadata) — this
    metadata object is what Alembic reads to generate migrations.
    """


class TestCaseModel(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(primary_key=True)
    category: Mapped[str]
    question: Mapped[str]
    notes: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    transcripts: Mapped[list["TranscriptModel"]] = relationship(back_populates="test_case")


class TranscriptModel(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"))
    final_answer: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    test_case: Mapped["TestCaseModel"] = relationship(back_populates="transcripts")
    tool_calls: Mapped[list["ToolCallModel"]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan"
    )
    verdicts: Mapped[list["JudgeVerdictModel"]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan"
    )


class ToolCallModel(Base):
    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"))
    tool_name: Mapped[str]
    arguments: Mapped[dict] = mapped_column(JSON)
    result: Mapped[str]

    transcript: Mapped["TranscriptModel"] = relationship(back_populates="tool_calls")


class JudgeVerdictModel(Base):
    __tablename__ = "judge_verdicts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"))
    judge_name: Mapped[str]
    passed: Mapped[bool]
    score: Mapped[float]
    reasoning: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    transcript: Mapped["TranscriptModel"] = relationship(back_populates="verdicts")
