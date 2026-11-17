"""Reviewer agent: deterministic, explainable quality gate.

Each check emits a typed `ReviewIssue` with a stable code and a severity, rather than
free-text strings, so routing (approve vs. revise) never depends on message wording.
This reviewer checks structure and pacing; it is NOT a technical fact-checker, so a
human should still verify accuracy before publishing.
"""

from __future__ import annotations

from codeverse.agents import rubric
from codeverse.models.schemas import (
    LessonPlan,
    LessonScript,
    ReviewIssue,
    ReviewResult,
    Severity,
    Storyboard,
)


def review_lesson(
    plan: LessonPlan,
    script: LessonScript,
    storyboard: Storyboard,
    approval_threshold: int = 80,
) -> ReviewResult:
    issues: list[ReviewIssue] = []
    issues += _check_plan(plan)
    issues += _check_script(plan, script)
    issues += _check_storyboard(script, storyboard)

    blocking = sum(i.severity is Severity.BLOCKING for i in issues)
    warnings = len(issues) - blocking
    score = max(0, 100 - blocking * rubric.BLOCKING_PENALTY - warnings * rubric.WARNING_PENALTY)
    approved = blocking == 0 and score >= approval_threshold

    if not issues:
        summary = "All structural and pacing checks passed. Verify technical accuracy manually."
    else:
        summary = f"{blocking} blocking issue(s), {warnings} warning(s)."
    return ReviewResult(approved=approved, score=score, issues=issues, summary=summary)


def _check_plan(plan: LessonPlan) -> list[ReviewIssue]:
    issues = []
    if len(plan.learning_objectives) < rubric.MIN_OBJECTIVES:
        issues.append(
            ReviewIssue(
                code="PLAN_FEW_OBJECTIVES",
                severity=Severity.BLOCKING,
                message=f"Lesson needs at least {rubric.MIN_OBJECTIVES} learning objectives.",
                target="plan.learning_objectives",
            )
        )
    if len({h.lower() for h in plan.outline}) != len(plan.outline):
        issues.append(
            ReviewIssue(
                code="PLAN_DUPLICATE_SECTIONS",
                severity=Severity.WARNING,
                message="Outline contains duplicate section headings.",
                target="plan.outline",
            )
        )
    return issues


def _check_script(plan: LessonPlan, script: LessonScript) -> list[ReviewIssue]:
    issues = []
    headings = [s.heading for s in script.sections]
    if len(headings) != len(plan.outline):
        issues.append(
            ReviewIssue(
                code="SCRIPT_OUTLINE_MISMATCH",
                severity=Severity.BLOCKING,
                message=(
                    f"Script has {len(headings)} sections but the outline has {len(plan.outline)}."
                ),
                target="script.sections",
            )
        )
    elif headings != plan.outline:
        issues.append(
            ReviewIssue(
                code="SCRIPT_HEADING_ORDER",
                severity=Severity.WARNING,
                message="Script section headings differ from the outline order or wording.",
                target="script.sections",
            )
        )

    for section in script.sections:
        if section.word_count < rubric.MIN_SECTION_WORDS:
            issues.append(
                ReviewIssue(
                    code="SECTION_TOO_SHORT",
                    severity=Severity.WARNING,
                    message=(
                        f"Narration for '{section.heading}' has {section.word_count} words; "
                        f"aim for at least {rubric.MIN_SECTION_WORDS}."
                    ),
                    target=section.heading,
                )
            )
        if not section.key_terms:
            issues.append(
                ReviewIssue(
                    code="SECTION_NO_KEY_TERMS",
                    severity=Severity.WARNING,
                    message=f"Section '{section.heading}' lists no key terms.",
                    target=section.heading,
                )
            )
    return issues


def _check_storyboard(script: LessonScript, storyboard: Storyboard) -> list[ReviewIssue]:
    issues = []
    refs = [scene.narration_reference for scene in storyboard.scenes]
    expected = (
        ["introduction"] + [f"sections[{i}]" for i in range(len(script.sections))] + ["conclusion"]
    )
    if refs != expected:
        issues.append(
            ReviewIssue(
                code="STORYBOARD_COVERAGE",
                severity=Severity.BLOCKING,
                message=(
                    "Storyboard needs an intro, one scene per section, and a recap, in order."
                ),
                target="storyboard.scenes",
            )
        )

    numbers = [scene.scene_number for scene in storyboard.scenes]
    if numbers != list(range(1, len(numbers) + 1)):
        issues.append(
            ReviewIssue(
                code="STORYBOARD_NUMBERING",
                severity=Severity.WARNING,
                message="Scene numbers should be consecutive starting at 1.",
                target="storyboard.scenes",
            )
        )

    total = storyboard.total_duration_seconds
    if not rubric.MIN_TOTAL_SECONDS <= total <= rubric.MAX_TOTAL_SECONDS:
        issues.append(
            ReviewIssue(
                code="DURATION_OUT_OF_RANGE",
                severity=Severity.WARNING,
                message=(
                    f"Estimated runtime {total}s is outside "
                    f"{rubric.MIN_TOTAL_SECONDS}-{rubric.MAX_TOTAL_SECONDS}s."
                ),
                target="storyboard",
            )
        )
    return issues
