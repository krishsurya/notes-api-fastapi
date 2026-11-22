"""Notes API: a small FastAPI + SQLAlchemy REST service with an optional LLM summary endpoint."""
import os
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notes.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


Base.metadata.create_all(engine)


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1)


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    summary: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


app = FastAPI(title="Notes API", version="1.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_note_or_404(db: Session, note_id: int) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def call_llm(text: str) -> str:
    """Ask an LLM (Anthropic Messages API) for a two-sentence summary."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Set ANTHROPIC_API_KEY to use summarize")
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": os.getenv("LLM_MODEL", "claude-haiku-5-5"),
            "max_tokens": 200,
            "messages": [
                {"role": "user", "content": f"Summarize this note in two sentences:\n\n{text}"}
            ],
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="LLM request failed")
    return resp.json()["content"][0]["text"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/notes", response_model=NoteOut, status_code=201)
def create_note(payload: NoteIn, db: Session = Depends(get_db)):
    note = Note(title=payload.title, content=payload.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.get("/notes", response_model=list[NoteOut])
def list_notes(db: Session = Depends(get_db)):
    return db.scalars(select(Note).order_by(Note.id)).all()


@app.get("/notes/{note_id}", response_model=NoteOut)
def read_note(note_id: int, db: Session = Depends(get_db)):
    return get_note_or_404(db, note_id)


@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    db.delete(get_note_or_404(db, note_id))
    db.commit()


@app.post("/notes/{note_id}/summarize", response_model=NoteOut)
def summarize_note(note_id: int, db: Session = Depends(get_db)):
    note = get_note_or_404(db, note_id)
    note.summary = call_llm(note.content)
    db.commit()
    db.refresh(note)
    return note
