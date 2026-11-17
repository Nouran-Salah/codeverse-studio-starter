import ast
import json
from itertools import pairwise

import pytest

from codeverse.exporters import export
from codeverse.models.schemas import LessonArtifact
from codeverse.pipeline import generate_lesson


@pytest.fixture
def artifact(settings):
    return generate_lesson("Big-O notation", "intermediate", settings=settings)


def test_json_round_trips(artifact):
    restored = LessonArtifact.model_validate(json.loads(export(artifact, "json")))
    assert restored == artifact


def test_markdown_contains_every_section(artifact):
    md = export(artifact, "markdown")
    assert md.startswith(f"# {artifact.plan.title}")
    for section in artifact.script.sections:
        assert f"### {section.heading}" in md


def test_srt_has_contiguous_cues(artifact):
    blocks = export(artifact, "srt").strip().split("\n\n")
    assert len(blocks) == len(artifact.storyboard.scenes)
    times = [b.splitlines()[1].split(" --> ") for b in blocks]
    assert times[0][0] == "00:00:00,000"
    assert all(prev[1] == nxt[0] for prev, nxt in pairwise(times))


def test_manim_export_is_valid_python_with_one_class_per_scene(artifact):
    tree = ast.parse(export(artifact, "manim"))
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == [f"Scene{i:02}" for i in range(1, len(artifact.storyboard.scenes) + 1)]


def test_unknown_format_raises(artifact):
    with pytest.raises(ValueError, match="Unknown export format"):
        export(artifact, "pdf")
