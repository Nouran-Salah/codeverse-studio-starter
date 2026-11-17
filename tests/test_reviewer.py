from codeverse.agents.planner import template_plan
from codeverse.agents.reviewer import review_lesson
from codeverse.agents.reviser import template_revision
from codeverse.agents.scriptwriter import template_script
from codeverse.agents.storyboarder import create_storyboard
from codeverse.models.schemas import Audience, Severity


def _lesson():
    plan = template_plan("Queues", Audience.BEGINNER)
    script = template_script(plan)
    return plan, script, create_storyboard(plan, script)


def _codes(review):
    return {issue.code for issue in review.issues}


def test_clean_lesson_is_approved_with_full_score():
    review = review_lesson(*_lesson())
    assert review.approved
    assert review.score == 100
    assert review.issues == []


def test_short_narration_is_a_warning_with_target():
    plan, script, _ = _lesson()
    sections = list(script.sections)
    sections[1] = sections[1].model_copy(update={"narration": "Too short."})
    script = script.model_copy(update={"sections": sections})
    review = review_lesson(plan, script, create_storyboard(plan, script))

    [issue] = [i for i in review.issues if i.code == "SECTION_TOO_SHORT"]
    assert issue.severity is Severity.WARNING
    assert issue.target == plan.outline[1]
    assert review.score < 100


def test_outline_mismatch_blocks_approval():
    plan, script, _ = _lesson()
    script = script.model_copy(update={"sections": script.sections[:2]})
    review = review_lesson(plan, script, create_storyboard(plan, script))
    assert not review.approved
    assert "SCRIPT_OUTLINE_MISMATCH" in _codes(review)
    assert review.blocking_issues


def test_missing_recap_scene_blocks_approval():
    plan, script, board = _lesson()
    board = board.model_copy(update={"scenes": board.scenes[:-1]})
    review = review_lesson(plan, script, board)
    assert not review.approved
    assert "STORYBOARD_COVERAGE" in _codes(review)


def test_many_warnings_fall_below_threshold():
    plan, script, _ = _lesson()
    sections = [
        s.model_copy(update={"narration": "Short.", "key_terms": []}) for s in script.sections
    ]
    script = script.model_copy(update={"sections": sections})
    review = review_lesson(plan, script, create_storyboard(plan, script), approval_threshold=80)
    assert not review.blocking_issues
    assert not review.approved  # warnings alone can still fail the quality bar


def test_template_revision_fixes_mechanical_issues():
    plan, script, _ = _lesson()
    sections = [
        s.model_copy(update={"narration": "Short.", "key_terms": []}) for s in script.sections
    ]
    broken = script.model_copy(update={"sections": sections})
    review = review_lesson(plan, broken, create_storyboard(plan, broken))

    fixed = template_revision(plan, broken, review)
    re_review = review_lesson(plan, fixed, create_storyboard(plan, fixed))
    assert re_review.approved, re_review.issues
    assert [s.heading for s in fixed.sections] == plan.outline
