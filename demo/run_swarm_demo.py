"""TR-OS Swarm Live Demo.

Demonstrates the decentralized Agent Swarm in action:
1. Ingests a flight cancellation event (PNR: BA-7782, BA117 LHR -> JFK).
2. Deploys concurrent scout agents (Direct, Alliance Codeshare, Intermodal).
3. Reduces and aggregates state using operator.add.
4. Ranks candidate routes using multi-criteria critic evaluation.
5. Evaluates human consensus requirements.
6. Simulates traveler approval and issues confirmed rebooking receipt.
"""

import asyncio
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from tros.swarm import SwarmOrchestrator, DisruptionEvent


async def main() -> None:
    console = Console(force_terminal=True, highlight=False)
    console.print(
        Panel.fit(
            "[bold cyan]TR-OS: Multi-Agent Travel Recovery Swarm[/bold cyan]\n"
            "[italic white]Autonomous Decentralized Route Discovery, State Reduction & Consensus[/italic white]",
            border_style="cyan",
        )
    )

    disruption: DisruptionEvent = {
        "pnr": "LON-9824X",
        "original_flight": "BA117",
        "disruption_type": "CANCELLED",
        "delay_minutes": 360,
        "affected_passengers": ["Dr. Samantha Vance", "Marcus Vance"],
    }

    console.print(
        Panel(
            f"[bold red]DISRUPTION DETECTED[/bold red]\n"
            f"- PNR: [yellow]{disruption['pnr']}[/yellow]\n"
            f"- Flight: [bold]{disruption['original_flight']}[/bold] (LHR -> JFK)\n"
            f"- Status: [bold red]{disruption['disruption_type']}[/bold red]\n"
            f"- Passengers: [white]{', '.join(disruption['affected_passengers'])}[/white]",
            title="Incoming Disruption Trigger",
            border_style="red",
        )
    )

    orchestrator = SwarmOrchestrator()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Initializing Swarm Agents & Scouts...", total=None)
        await asyncio.sleep(0.5)
        
        progress.update(task, description="[yellow]Fan-out: Direct, Alliance, and Intermodal Scouts searching...")
        state = await orchestrator.execute(disruption, auto_execute_if_approved=False)
        await asyncio.sleep(0.4)

    # Display Swarm Candidate Table
    table = Table(title="[bold green]Swarm Route Candidates (operator.add Aggregated)[/bold green]")
    table.add_column("Flight / Mode", style="cyan")
    table.add_column("Carrier", style="magenta")
    table.add_column("Departure", style="white")
    table.add_column("Arrival", style="white")
    table.add_column("Price Delta", style="yellow")
    table.add_column("Composite Score", style="green")

    for cand in state["inventory_candidates"]:
        diff_str = f"+${cand['price_differential']:.2f}" if cand['price_differential'] > 0 else f"-${abs(cand['price_differential']):.2f}" if cand['price_differential'] < 0 else "$0.00"
        is_selected = (
            state["selected_solution"] and cand["flight_number"] == state["selected_solution"]["flight_number"]
        )
        prefix = "[TOP] " if is_selected else "      "
        table.add_row(
            f"{prefix}{cand['flight_number']}",
            cand["carrier"],
            cand["departure_time"],
            cand["arrival_time"],
            diff_str,
            f"{cand['score']:.3f}",
        )

    console.print(table)

    # Display Selected Solution & Consensus
    selected = state["selected_solution"]
    if selected:
        console.print(
            Panel(
                f"[bold green]Top Recommendation:[/bold green] {selected['flight_number']} ({selected['carrier']})\n"
                f"Score: [bold]{selected['score']:.3f}[/bold] | Price Delta: [yellow]${selected['price_differential']:.2f}[/yellow]\n"
                f"Consensus Status: [bold yellow]{state['human_consensus_status']}[/bold yellow]",
                title="Critic Agent Selection",
                border_style="green",
            )
        )

    # Human-in-the-Loop Consensus Simulation
    if state["human_consensus_status"] == "PENDING":
        console.print("[bold yellow]> Human-in-the-Loop:[/bold yellow] Requesting passenger sign-off on cost delta...")
        await asyncio.sleep(0.8)
        console.print("[bold green][OK] Passenger CONFIRMED approval via mobile app![/bold green]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]ExecutionWorker issuing e-ticket & updating PNR...", total=None)
            final_state = await orchestrator.approve_and_execute(state)
            await asyncio.sleep(0.6)
    else:
        final_state = state

    # Final Execution Receipt
    receipt = final_state.get("execution_receipt")
    if receipt:
        console.print(
            Panel(
                f"[bold green]BOOKING CONFIRMED & TICKETED[/bold green]\n"
                f"- Receipt ID: [cyan]{receipt['receipt_id']}[/cyan]\n"
                f"- E-Ticket: [cyan]{receipt['e_ticket_number']}[/cyan]\n"
                f"- Rebooked Flight: [bold white]{receipt['rebooked_flight']} ({receipt['carrier']})[/bold white]\n"
                f"- Departure: [white]{receipt['departure_time']}[/white]\n"
                f"- Incurred Cost: [yellow]${receipt['cost_incurred']:.2f}[/yellow]\n"
                f"- Timestamp: [white]{receipt['booked_at']}[/white]",
                title="Execution Worker Receipt",
                border_style="bold green",
            )
        )

    # Swarm Agent Reasoning Logs
    console.print("\n[bold]Swarm Agent Audit Logs (operator.add Trace):[/bold]")
    for log in final_state["agent_logs"]:
        console.print(f"  - {log}")


if __name__ == "__main__":
    asyncio.run(main())
