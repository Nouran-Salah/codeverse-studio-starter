from __future__ import annotations

import dataclasses
import logging
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from codeverse import __version__
from codeverse.config import Settings
from codeverse.exporters import EXTENSIONS, export
from codeverse.llm import LLMError, OllamaProvider
from codeverse.models.schemas import Audience
from codeverse.pipeline import generate_lesson

app = typer.Typer(help="Plan educational CS videos with a multi-agent LangGraph workflow.")
console = Console()


@app.command()
def run(
    topic: str = typer.Argument(..., help="The computer-science topic to teach."),
    audience: Audience = typer.Option(Audience.BEGINNER, help="Target audience."),
    provider: str = typer.Option(
        None, help="LLM provider: 'deterministic' or 'ollama'. Defaults to CODEVERSE_PROVIDER."
    ),
    model: str = typer.Option(None, help="Ollama model name, e.g. qwen3:4b."),
    max_revisions: int = typer.Option(None, min=0, max=5, help="Bound on review/revise loops."),
    formats: list[str] = typer.Option(
        ["json"], "--format", "-f", help="Export format(s): json, markdown, srt, manim."
    ),
    output_dir: Path = typer.Option(Path("artifacts"), "--output-dir", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run the workflow for TOPIC and write the requested exports."""
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    unknown = sorted(set(formats) - set(EXTENSIONS))
    if unknown:
        raise typer.BadParameter(f"Unknown format(s): {', '.join(unknown)}")

    settings = Settings.from_env()
    overrides = {
        "provider": provider,
        "ollama_model": model,
        "max_revisions": max_revisions,
    }
    settings = dataclasses.replace(
        settings, **{k: v for k, v in overrides.items() if v is not None}
    )

    try:
        with console.status(f"Running workflow ({settings.provider})..."):
            artifact = generate_lesson(topic, audience, settings=settings)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for fmt in dict.fromkeys(formats):
        path = output_dir / f"{stamp}_lesson.{EXTENSIONS[fmt]}"
        path.write_text(export(artifact, fmt), encoding="utf-8")
        written.append(path)

    _print_summary(artifact, written)
    if artifact.status != "approved":
        raise typer.Exit(code=2)


@app.command()
def doctor():
    """Check configuration and whether the configured Ollama model is available."""
    settings = Settings.from_env()
    console.print(f"codeverse {__version__} · provider = [bold]{settings.provider}[/bold]")
    ollama = OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    try:
        models = ollama.health_check()
    except LLMError as exc:
        console.print(f"[yellow]Ollama unavailable:[/yellow] {exc}")
        console.print("Deterministic mode still works without Ollama.")
        return
    found = settings.ollama_model in models
    mark = "[green]found[/green]" if found else "[red]not pulled[/red]"
    console.print(f"Ollama at {settings.ollama_base_url}: model {settings.ollama_model} {mark}")
    if not found:
        console.print(f"Run: ollama pull {settings.ollama_model}")


@app.command()
def version():
    """Print the package version."""
    console.print(__version__)


def _print_summary(artifact, written: list[Path]) -> None:
    meta = artifact.metadata
    color = "green" if artifact.status == "approved" else "yellow"
    table = Table(title=artifact.plan.title, show_header=False)
    table.add_row("Status", f"[{color}]{artifact.status}[/{color}]")
    table.add_row("Review score", f"{artifact.review.score}/100")
    table.add_row("Scenes", str(len(artifact.storyboard.scenes)))
    table.add_row("Runtime", f"~{artifact.storyboard.total_duration_seconds}s")
    table.add_row("Provider", f"{meta.provider}" + (f" ({meta.model})" if meta.model else ""))
    table.add_row("Revisions", f"{meta.revision_count}/{meta.max_revisions}")
    if meta.fallbacks:
        table.add_row("Fallbacks", ", ".join(meta.fallbacks))
    table.add_row("Total time", f"{sum(t.duration_ms for t in meta.timings):.1f} ms")
    for path in written:
        table.add_row("Saved", str(path))
    console.print(table)
    for issue in artifact.review.issues:
        console.print(f"  [{issue.severity.value}] {issue.code}: {issue.message}")


if __name__ == "__main__":
    app()
