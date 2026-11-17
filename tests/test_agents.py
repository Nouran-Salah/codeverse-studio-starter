import pytest

from codeverse.agents.planner import clean_topic, template_plan
from codeverse.agents.rubric import MIN_SECTION_WORDS
from codeverse.agents.scriptwriter import template_script
from codeverse.agents.storyboarder import create_storyboard, narration_seconds
from codeverse.models.schemas import Audience


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Binary   search?  ", "Binary search"),
        ("How do pointers work in C++?", "pointers in C++"),
        ("What is a hash table?", "hash table"),
        ("Explain recursion", "recursion"),
        ("How does", "How does"),  # never strip down to nothing
    ],
)
def test_clean_topic(raw, expected):
    assert clean_topic(raw) == expected


def test_plan_is_audience_aware():
    beginner = template_plan("Recursion", Audience.BEGINNER)
    advanced = template_plan("Recursion", Audience.ADVANCED)
    assert beginner.learning_objectives != advanced.learning_objectives
    assert advanced.learning_objectives[0].startswith("Analyze")
    assert beginner.prerequisites and advanced.prerequisites


def test_script_has_one_section_per_outline_item():
    plan = template_plan("Hash tables", Audience.INTERMEDIATE)
    script = template_script(plan)
    assert [s.heading for s in script.sections] == plan.outline
    assert all(s.word_count >= MIN_SECTION_WORDS for s in script.sections)
    assert all(s.key_terms for s in script.sections)


def test_script_handles_longer_llm_outlines():
    plan = template_plan("Graphs", Audience.BEGINNER).model_copy(
        update={"outline": [f"Part {i}" for i in range(1, 7)]}
    )
    assert len(template_script(plan).sections) == 6


def test_storyboard_brackets_sections_with_intro_and_recap():
    plan = template_plan("Stacks", Audience.BEGINNER)
    script = template_script(plan)
    board = create_storyboard(plan, script)
    refs = [s.narration_reference for s in board.scenes]
    assert refs[0] == "introduction" and refs[-1] == "conclusion"
    assert refs[1:-1] == [f"sections[{i}]" for i in range(len(script.sections))]
    assert [s.scene_number for s in board.scenes] == list(range(1, len(board.scenes) + 1))


def test_scene_duration_tracks_narration_length():
    assert narration_seconds("word " * 100) > narration_seconds("word " * 10)
    assert narration_seconds("") >= 3
    assert narration_seconds("word " * 10_000) == 120
