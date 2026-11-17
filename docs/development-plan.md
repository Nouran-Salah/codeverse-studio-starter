# Development plan

## Milestone 1: Content-planning prototype ✅
- [x] LangGraph orchestration
- [x] Typed agent outputs
- [x] CLI and JSON artifact
- [x] Basic tests

## Milestone 2: Local LLM integration ✅
- [x] Provider protocol and Ollama client with JSON-schema structured outputs
- [x] Structured outputs for plan, script, and revisions
- [x] Timeouts, retries with validation feedback, malformed-output handling
- [x] Deterministic mode for tests and offline use; per-stage fallback
- [x] `codeverse doctor` health check

## Milestone 3: Review and iteration (mostly done)
- [x] Typed reviewer issues with severity and score
- [x] Bounded reviewer → reviser → storyboarder loop
- [x] Review history, timings, and fallbacks in run metadata
- [x] Versioned prompts (`PROMPT_VERSION`)
- [ ] Human edits and approval step (LangGraph interrupt)
- [ ] Optional LLM-as-judge accuracy signal

## Milestone 4: Media generation
- [x] SRT subtitles timed from narration
- [ ] Text-to-speech provider interface (e.g. Piper, Coqui)
- [ ] Generate and cache media assets with provenance

## Milestone 5: Video rendering
- [x] Manim scene skeleton export
- [ ] Render scenes with Manim
- [ ] Align narration audio and subtitles
- [ ] Assemble output with FFmpeg

## Milestone 6: Product interface
- [x] FastAPI endpoints and Dockerfile
- [ ] Persist runs (SQLite)
- [ ] React dashboard: history, preview, approval, export
