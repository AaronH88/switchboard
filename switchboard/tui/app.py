"""Switchboard TUI Textual application.

Dependencies:
- textual: Required for TUI framework
"""

import asyncio
from pathlib import Path
from typing import Optional, Any
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from .widgets import (
    SwitchboardHeader,
    OperatorPanel,
    ProjectsPanel,
    PatchPanel,
    ActiveLines,
    PartyLine,
    Footer
)
from .state import SwitchboardState
from .polling import poll_workers, poll_stats, tail_file


class SwitchboardApp(App):
    """Switchboard TUI application."""

# CSS_PATH = Path(__file__).parent / "switchboard.tcss"
    TITLE = "Switchboard TUI"
    SUB_TITLE = "Agent Pipeline Monitor"

    BINDINGS = [
        Binding('q', 'quit', 'Quit'),
        Binding('tab', 'focus_next', 'Next'),
        Binding('shift+tab', 'focus_previous', 'Previous'),
        Binding('d', 'show_detail', 'Detail'),
        Binding('l', 'toggle_log_focus', 'Log Focus'),
        Binding('r', 'force_refresh', 'Refresh'),
        Binding('0', 'switch_daemon_log', 'Daemon'),
        Binding('1', 'switch_worker_1', 'Worker 1'),
        Binding('2', 'switch_worker_2', 'Worker 2'),
        Binding('3', 'switch_worker_3', 'Worker 3'),
        Binding('4', 'switch_worker_4', 'Worker 4'),
        Binding('5', 'switch_worker_5', 'Worker 5'),
        Binding('6', 'switch_worker_6', 'Worker 6'),
        Binding('7', 'switch_worker_7', 'Worker 7'),
        Binding('8', 'switch_worker_8', 'Worker 8'),
        Binding('9', 'switch_worker_9', 'Worker 9'),
    ]

    def __init__(self, **kwargs: Any):
        """Initialize the app with optional configuration."""
        super().__init__()
        self.config = kwargs

        # Store configuration
        self.artifacts_dir = kwargs.get('artifacts_dir', 'artifacts/')
        self.poll_interval = kwargs.get('poll_interval', 10)

        # Initialize state
        self.state = SwitchboardState()

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        # Header
        yield SwitchboardHeader()

        # Main content: Horizontal container with sidebars
        with Horizontal():
            yield OperatorPanel()
            yield ProjectsPanel()

        # PatchPanel with scrollable container
        yield PatchPanel()

        # ActiveLines
        yield ActiveLines()

        # PartyLine
        yield PartyLine()

        # Footer
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize app after mounting."""
        # Initialize SwitchboardState
        self.state = SwitchboardState()

        # Start background worker for log tailing
        self.run_worker(self._watch_daemon_log())

        # Start polling timers
        self.set_interval(10, self._poll_workers)
        self.set_interval(15, self._poll_pipelines)
        self.set_interval(60, self._poll_stats)

    async def _poll_workers(self) -> None:
        """Poll workers and update state."""
        try:
            workers = await poll_workers()
            self.state = self.state.reconcile_workers(workers)

            # Refresh relevant widgets
            active_lines = self.query_one(ActiveLines)
            active_lines.update_state(self.state)

            operator_panel = self.query_one(OperatorPanel)
            operator_panel.update_state(self.state)
        except Exception as e:
            # Handle polling errors gracefully
            pass

    async def _poll_pipelines(self) -> None:
        """Poll pipelines and update state."""
        try:
            # Note: Pipeline polling logic would go here
            # For now, just refresh the PatchPanel
            patch_panel = self.query_one(PatchPanel)
            patch_panel.update_state(self.state)
        except Exception as e:
            # Handle polling errors gracefully
            pass

    async def _poll_stats(self) -> None:
        """Poll stats and update state."""
        try:
            stats_data = await poll_stats()
            # Update stats in state
            operator_panel = self.query_one(OperatorPanel)
            operator_panel.update_state(self.state)
        except Exception as e:
            # Handle polling errors gracefully
            pass

    async def _watch_daemon_log(self) -> None:
        """Watch daemon log and add events to PartyLine."""
        try:
            log_path = Path(self.artifacts_dir) / "agent_router.log"
            async for line in tail_file(log_path):
                # Parse and add log event
                from .polling import parse_log_line
                event = parse_log_line(line)
                if event:
                    self.state = self.state.add_log_event(event)

                    # Update PartyLine
                    party_line = self.query_one(PartyLine)
                    party_line.update_state(self.state)

                    # Update daemon status if needed
                    if event.parsed_event_type in ["daemon_started", "daemon_stopped"]:
                        self.state = self.state._replace(
                            daemon_online=event.parsed_event_type == "daemon_started"
                        )
                        footer = self.query_one(Footer)
                        footer.update_state(self.state)
        except Exception as e:
            # Handle log watching errors gracefully
            pass

    def action_show_detail(self) -> None:
        """Show detail screen (placeholder)."""
        # Placeholder for DetailScreen
        pass

    def action_toggle_log_focus(self) -> None:
        """Toggle log focus screen (placeholder)."""
        # Placeholder for LogFocusScreen
        pass

    def action_force_refresh(self) -> None:
        """Force refresh all data."""
        asyncio.create_task(self._poll_workers())
        asyncio.create_task(self._poll_pipelines())
        asyncio.create_task(self._poll_stats())

    def action_switch_daemon_log(self) -> None:
        """Switch PartyLine to daemon log."""
        party_line = self.query_one(PartyLine)
        party_line.switch_source("daemon")

    def action_switch_worker_1(self) -> None:
        """Switch PartyLine to worker 1."""
        self._switch_to_worker("worker_1")

    def action_switch_worker_2(self) -> None:
        """Switch PartyLine to worker 2."""
        self._switch_to_worker("worker_2")

    def action_switch_worker_3(self) -> None:
        """Switch PartyLine to worker 3."""
        self._switch_to_worker("worker_3")

    def action_switch_worker_4(self) -> None:
        """Switch PartyLine to worker 4."""
        self._switch_to_worker("worker_4")

    def action_switch_worker_5(self) -> None:
        """Switch PartyLine to worker 5."""
        self._switch_to_worker("worker_5")

    def action_switch_worker_6(self) -> None:
        """Switch PartyLine to worker 6."""
        self._switch_to_worker("worker_6")

    def action_switch_worker_7(self) -> None:
        """Switch PartyLine to worker 7."""
        self._switch_to_worker("worker_7")

    def action_switch_worker_8(self) -> None:
        """Switch PartyLine to worker 8."""
        self._switch_to_worker("worker_8")

    def action_switch_worker_9(self) -> None:
        """Switch PartyLine to worker 9."""
        self._switch_to_worker("worker_9")

    def _switch_to_worker(self, worker_source: str) -> None:
        """Switch to specified worker if it exists."""
        worker_num = int(worker_source.split("_")[1])
        if worker_num <= len(self.state.workers):
            party_line = self.query_one(PartyLine)
            party_line.switch_source(worker_source)

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

# CSS loading will be handled by textual framework