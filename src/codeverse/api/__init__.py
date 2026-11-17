"""Optional HTTP API. Install with `pip install -e ".[api]"` and run:

uvicorn codeverse.api:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from codeverse import __version__
from codeverse.exporters import ExportFormat, export
from codeverse.models.schemas import Audience, LessonArtifact
from codeverse.pipeline import MAX_TOPIC_LENGTH, generate_lesson

app = FastAPI(title="Codeverse Studio", version=__version__)


class LessonRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=MAX_TOPIC_LENGTH, examples=["Binary search"])
    audience: Audience = Audience.BEGINNER


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.post("/lessons", response_model=LessonArtifact)
def create_lesson(request: LessonRequest) -> LessonArtifact:
    try:
        return generate_lesson(request.topic, request.audience)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/lessons/export/{fmt}", response_class=PlainTextResponse)
def export_lesson(fmt: ExportFormat, request: LessonRequest) -> str:
    return export(create_lesson(request), fmt)
