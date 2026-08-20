"""TR-OS Demo Runner — executes the cancelled flight scenario.

Usage:
    python -m demo.run_demo
"""

from __future__ import annotations

import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from demo.scenarios.cancelled_flight import run_cancelled_flight_demo
from tros.config import LLM_API_KEY
from tros.schemas.mission import MissionStatus


def main() -> None:
    console = Console()

    console.print()
    console.print(Panel.fit(
        "[bold cyan]TR-OS: Travel Recovery Operating System[/bold cyan]\n"
        "[dim]Agentic AI Flight Disruption Recovery Demo[/dim]",
        border_style="cyan",
    ))
    console.print()

    # LLM mode indicator
    llm_enabled = bool(LLM_API_KEY)
    if llm_enabled:
        console.print("[bold green]● LLM Mode: ENABLED[/bold green] "
                       "(AI reasoning layer active)")
    else:
        console.print("[bold yellow]● LLM Mode: DISABLED[/bold yellow] "
                       "(deterministic fallback — set TR_OS_LLM_API_KEY to enable)")
    console.print()

    # Run the scenario
    console.print("[bold]Scenario:[/bold] Flight MH318 KUL -> NRT has been cancelled")
    console.print("[bold]Traveler:[/bold] Business traveler, budget $1000 USD")
    console.print("[bold]Mission:[/bold] Recover my trip")
    console.print()
    console.print("[dim]Initializing multi-agent recovery pipeline...[/dim]")
    console.print()

    start = time.time()
    state = run_cancelled_flight_demo()
    elapsed = time.time() - start

    # Print results
    console.print()
    console.rule("[bold green]MISSION RESULT[/bold green]")
    console.print()

    # Status summary
    status_color = "green" if state.status == MissionStatus.COMPLETED else "red"
    console.print(f"  Mission ID:  [bold]{state.mission_id}[/bold]")
    console.print(f"  Status:      [{status_color}]{state.status.value.upper()}[/{status_color}]")
    console.print(f"  Version:     {state.version}")
    console.print(f"  Duration:    {elapsed:.2f}s")
    console.print()

    # LLM thought traces (if available)
    _print_react_trace(console, state)
    _print_llm_traces(console, state)

    # Agent outputs table
    table = Table(title="Agent Execution Results", show_header=True,
                  header_style="bold cyan")
    table.add_column("Agent", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Confidence", justify="right")
    table.add_column("Summary", max_width=50)

    for agent_name, output in state.agent_outputs.items():
        status_style = {
            "completed": "green",
            "partial": "yellow",
            "failed": "red",
            "skipped": "dim",
        }.get(output.status.value, "white")

        table.add_row(
            agent_name,
            f"[{status_style}]{output.status.value}[/{status_style}]",
            f"{output.confidence:.2f}",
            output.reasoning_summary[:80],
        )

    console.print(table)
    console.print()

    # Final recommendation
    summary_output = state.agent_outputs.get("SummaryAgent")
    if summary_output and summary_output.recommendation:
        summary_text = summary_output.recommendation.get("summary", "")
        console.print(Panel(summary_text, title="[bold]Recovery Recommendation[/bold]",
                            border_style="green"))
    else:
        console.print("[red]No summary generated.[/red]")

    console.print()

    # Audit trail
    console.print(f"[dim]Audit entries: {len(state.audit)}[/dim]")
    console.print(f"[dim]Completed agents: {', '.join(state.completed_agents)}[/dim]")
    if state.failed_agents:
        console.print(f"[yellow]Failed agents: {', '.join(state.failed_agents)}[/yellow]")

    console.print()
    console.print("[dim]No booking has been made. This is a recommendation only.[/dim]")
    console.print()


def _print_react_trace(console: Console, state) -> None:
    """Print the FlightAgent ReAct trace if present."""
    llm_meta = getattr(state, "llm_metadata", None) or {}
    react_trace = llm_meta.get("react_trace")
    if not react_trace:
        return

    console.rule("[bold cyan]FLIGHT AGENT — REACT TRACE[/bold cyan]")
    console.print()

    phase_colors = {
        "THOUGHT": "yellow",
        "ACTION": "blue",
        "OBSERVATION": "green",
        "FINAL": "bold magenta",
    }

    for step in react_trace:
        phase = step.get("phase", "UNKNOWN")
        color = phase_colors.get(phase, "white")
        step_num = step.get("step_number", 0)
        thought = step.get("thought", "")
        tool_name = step.get("tool_name", "")
        tool_args = step.get("tool_arguments", {})
        observation = step.get("observation", {})
        duration = step.get("duration_ms", 0)

        header = f"Step {step_num} [{phase}]"
        lines = []

        if thought:
            lines.append(thought[:200])

        if phase == "ACTION" and tool_name:
            args_str = ", ".join(f"{k}={v}" for k, v in (tool_args or {}).items())
            lines.append(f"{tool_name}({args_str})")

        if phase == "OBSERVATION" and observation:
            cand_count = observation.get("candidate_count", 0)
            if cand_count:
                lines.append(f"Atlas returned {cand_count} ranked candidates.")
            top = observation.get("candidates", [])
            if top:
                best = top[0]
                lines.append(
                    f"Top: {best.get('flight_number', '?')} "
                    f"(score {best.get('deterministic_score', 0)}, "
                    f"${best.get('price', 0)})"
                )
            if observation.get("error_code"):
                lines.append(f"Error: {observation['error_code']} — "
                             f"{observation.get('message', '')}")

        if phase == "FINAL" and observation:
            decision = observation.get("decision", "")
            conf = observation.get("confidence", 0)
            lines.append(f"Decision: {decision} (confidence {conf})")

        if duration:
            lines.append(f"({duration}ms)")

        content = "\n".join(lines) if lines else ""
        console.print(Panel(
            content,
            title=f"[{color}]{header}[/{color}]",
            border_style=color,
            expand=False,
        ))

    # Tool call summary
    tool_calls = llm_meta.get("react_tool_calls", 0)
    if tool_calls:
        console.print(f"  [dim]Total tool calls: {tool_calls}[/dim]")
    console.print()


def _print_llm_traces(console: Console, state) -> None:
    """Print LLM thought traces if they exist in the state."""
    traces: list[tuple[str, str]] = []

    # Supervisor LLM metadata (execution plan, failure handling)
    llm_meta = getattr(state, "llm_metadata", None) or {}

    if llm_meta:
        plan = llm_meta.get("execution_plan", [])
        reasoning = llm_meta.get("reasoning", "")
        if plan:
            traces.append(("Supervisor (Orchestration)",
                           f"Execution plan: {', '.join(plan)}"))
        if reasoning:
            traces.append(("Supervisor (Reasoning)", reasoning[:200]))

        # Failure assessment
        failures = llm_meta.get("failures", {})
        if failures:
            resp = failures.get("failure_response", "")
            if resp:
                traces.append(("Supervisor (Failure Assessment)", resp[:200]))

    # Check agent outputs for LLM reasoning
    for agent_name, output in state.agent_outputs.items():
        rec = output.recommendation or {}
        llm_analysis = rec.get("llm_analysis", "")
        if llm_analysis:
            traces.append((f"{agent_name} (AI Analysis)", llm_analysis[:200]))

    if not traces:
        return

    console.rule("[bold magenta]AI REASONING TRACES[/bold magenta]")
    console.print()
    for title, content in traces:
        console.print(Panel(
            content,
            title=f"[magenta]{title}[/magenta]",
            border_style="magenta",
            expand=False,
        ))
    console.print()


if __name__ == "__main__":
    main()
