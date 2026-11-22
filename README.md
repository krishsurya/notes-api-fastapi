# Notes API

A small REST API built with **FastAPI**, **SQLAlchemy** and **SQLite**, with an optional endpoint that uses an **LLM API** to summarize a note.

## Endpoints
| Method | Path | What it does |
|---|---|---|
| GET | /health | Health check |
| POST | /notes | Create a note (title, content) |
| GET | /notes | List notes |
| GET | /notes/{id} | Get one note |
| DELETE | /notes/{id} | Delete a note |
| POST | /notes/{id}/summarize | Summarize the note with an LLM and save the summary |

## Run it
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs for the interactive API docs.

For the summarize endpoint, set your key first: `export ANTHROPIC_API_KEY=your-key` (optional `LLM_MODEL`).

## Test it
```bash
pytest
```

## Tech
Python, FastAPI, Pydantic, SQLAlchemy, SQLite, httpx, pytest.
The database URL is read from `DATABASE_URL`, so the same code can point to PostgreSQL.
