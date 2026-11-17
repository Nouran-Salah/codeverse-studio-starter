# Architecture

## Workflow graph

```text
START -> planner -> scriptwriter -> storyboarder -> reviewer --approved / limit--> END
                                         ^              |
                                         |          not approved
                                         +-- reviser <--+
```

`build_workflow(settings, ctx)` compiles the graph. The routing function after the reviewer
ends the run when the review is approved or `revision_count >= max_revisions`; otherwise it
routes to the reviser. `generate_lesson` also sets LangGraph's `recursion_limit` from
`max_revisions` as a second safety bound.

## State

`LessonState` is a `TypedDict` shared by all nodes. Nodes return only the keys they update.
Three keys are append-only channels with an `operator.add` reducer:

| Key | Written by | Purpose |
|---|---|---|
| `timings` | every node (via `_timed`) | per-stage latency |
| `review_history` | reviewer | every review in the loop, for auditing improvement |
| `fallbacks` | LLM-backed nodes | stages that used the deterministic template |

## LLM layer

```text
agent --> run_with_fallback --> generate_structured --> LLMProvider.complete_json
             |                       |  validate with Pydantic
             |                       |  on error: retry with the error in the prompt
             +-- on LLMError: deterministic template, stage recorded in `fallbacks`
```

- `LLMProvider` is a `Protocol`; `OllamaProvider` calls `/api/chat` with the model's JSON
  schema in `format` (structured outputs) using only the standard library.
- `generate_structured` strips Markdown fences, validates, and retries up to `max_retries`.
- Agents add guardrails on top: the planner pins `topic` and `audience` to the request; the
  scriptwriter and reviser reject output whose headings drift from the outline.

## Reviewer rubric

Constants live in `agents/rubric.py`.

| Code | Severity | Rule |
|---|---|---|
| `PLAN_FEW_OBJECTIVES` | blocking | at least 2 learning objectives |
| `SCRIPT_OUTLINE_MISMATCH` | blocking | one script section per outline item |
| `STORYBOARD_COVERAGE` | blocking | intro, one scene per section, recap, in order |
| `PLAN_DUPLICATE_SECTIONS` | warning | outline headings are unique |
| `SCRIPT_HEADING_ORDER` | warning | headings match outline wording and order |
| `SECTION_TOO_SHORT` | warning | at least 35 words of narration per section |
| `SECTION_NO_KEY_TERMS` | warning | every section lists key terms |
| `STORYBOARD_NUMBERING` | warning | scenes numbered 1..n |
| `DURATION_OUT_OF_RANGE` | warning | total runtime 60–600 s |

Score = 100 − 30 × blocking − 6 × warnings. Approved when there are no blocking issues and
the score is at least `approval_threshold` (default 80).

## Extension points

1. **New LLM backend:** implement `complete_json` and register it in `llm.build_provider`.
2. **New export:** add a function to `exporters.EXPORTERS`.
3. **New review rule:** add a check to `agents/reviewer.py` with a stable code; the reviser can
   handle it in `template_revision` and the LLM reviser receives it automatically.
4. **Media stages:** add TTS and render nodes after approval, consuming the storyboard and SRT.
