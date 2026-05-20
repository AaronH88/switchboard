"""Switchboard TUI Textual application.

Dependencies:
- textual: Required for TUI framework
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, Any
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from rich.text import Text

from .widgets import (
    SwitchboardHeader,
    OperatorPanel,
    ProjectsPanel,
    PatchPanel,
    ActiveLines,
    PartyLine,
    SwitchboardFooter
)
from .state import SwitchboardState
from .polling import poll_workers, poll_stats, tail_file
from .screens import DetailScreen, LogFocusScreen, ProjectScreen


class SwitchboardApp(App):
    """Switchboard TUI application."""

    CSS_PATH = Path(__file__).parent / "switchboard.tcss"
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
        yield SwitchboardFooter()

    async def on_mount(self) -> None:
        """Initialize app after mounting."""
        # Initialize SwitchboardState
        self.state = SwitchboardState()

        # Show startup splash
        await self._show_startup_splash()

        # Start daemon online detection
        self.set_interval(15, self._check_daemon_status)

        # Start background worker for log tailing
        self.run_worker(self._watch_daemon_log())

        # Start polling timers
        self.set_interval(5, self._poll_workers)
        self.set_interval(5, self._poll_pipelines)
        self.set_interval(30, self._poll_stats)

    async def _poll_workers(self) -> None:
        """Poll workers and update state."""
        try:
            workers = await poll_workers()
            self.state = self.state.reconcile_workers(workers)

            self.query_one(ActiveLines).update_state(self.state)
            self.query_one(OperatorPanel).update_state(self.state)
            self.query_one(ProjectsPanel).update_state(self.state)
            self.query_one(SwitchboardHeader).update_state(self.state)
        except Exception:
            pass

    async def _poll_pipelines(self) -> None:
        """Poll pipelines and update state."""
        try:
            from .polling import poll_pipelines
            pipeline_data = await poll_pipelines()
            self.state = self.state.reconcile_pipelines(pipeline_data)

            patch_panel = self.query_one(PatchPanel)
            patch_panel.update_state(self.state)
        except Exception:
            pass

    async def _poll_stats(self) -> None:
        """Poll stats and update state."""
        try:
            stats_data = await poll_stats()
            summary = stats_data.get("summary", stats_data) if isinstance(stats_data, dict) else {}
            from .state import StatsSnapshot
            self.state = self.state.update_stats(StatsSnapshot(
                completed_today=int(summary.get("closed_issues", 0)),
                failed_today=int(summary.get("blocked_issues", 0)),
                blocked_count=int(summary.get("blocked_issues", 0)),
            ))
            self.query_one(OperatorPanel).update_state(self.state)
        except Exception:
            pass

    async def _watch_daemon_log(self) -> None:
        """Watch daemon log and add events to PartyLine."""
        try:
            log_path = Path(self.artifacts_dir) / "switchboard.log"
            async for line in tail_file(log_path):
                # Parse and add log event
                from .polling import parse_log_line
                event = parse_log_line(line)
                if event:
                    self.state = self.state.add_log_event(event)

                    # Update PartyLine
                    party_line = self.query_one(PartyLine)
                    party_line.update_state(self.state)

                    if event.parsed_event_type in ["daemon_started", "daemon_stopped"]:
                        from dataclasses import replace
                        self.state = replace(self.state,
                            daemon_online=event.parsed_event_type == "daemon_started"
                        )
                        self.query_one(SwitchboardFooter).update_state(self.state)
        except Exception as e:
            # Handle log watching errors gracefully
            pass

    async def _show_startup_splash(self) -> None:
        """Show startup splash message."""
        startup_text = Text("SWITCHBOARD ONLINE · PATCHING IN...", style="bold green")
        startup_overlay = Static(startup_text)
        startup_overlay.add_class("startup-overlay")

        # Add overlay to the app
        await self.mount(startup_overlay)

        # Auto-dismiss after 2-3 seconds
        await asyncio.sleep(2.5)

        # Remove overlay
        try:
            startup_overlay.remove()
        except:
            pass  # Handle case where overlay is already gone

    def _check_daemon_status(self) -> None:
        """Check if daemon is online by looking at log file modification time."""
        try:
            log_path = Path(self.artifacts_dir) / "switchboard.log"

            if not log_path.exists():
                daemon_online = False
            else:
                # Check if file was modified in the last 30 seconds
                mtime = log_path.stat().st_mtime
                current_time = time.time()
                daemon_online = (current_time - mtime) < 30

            if self.state.daemon_online != daemon_online:
                self.state = self.state._replace(daemon_online=daemon_online)

                # Update header
                header = self.query_one(SwitchboardHeader)
                header.update_state(self.state)

                # Update footer
                footer = self.query_one(SwitchboardFooter)
                footer.update_state(self.state)

        except Exception:
            # Handle file access errors gracefully
            pass

    def action_show_detail(self) -> None:
        """Show detail screen for selected bead."""
        # Get selected bead from focused widget
        focused_widget = self.focused

        selected_bead_id = None

        # Check PatchPanel for selection
        if hasattr(focused_widget, 'add_class') and 'patchpanel' in str(focused_widget.classes):
            # PatchPanel selection logic would go here
            # For now, get first bead from workers if available
            if self.state.workers:
                selected_bead_id = list(self.state.workers.keys())[0]

        # Check ActiveLines for selection
        elif hasattr(focused_widget, 'add_class') and 'activelines' in str(focused_widget.classes):
            # ActiveLines selection logic would go here
            if self.state.workers:
                selected_bead_id = list(self.state.workers.keys())[0]

        if selected_bead_id:
            detail_screen = DetailScreen(selected_bead_id, artifacts_dir=self.artifacts_dir)
            self.push_screen(detail_screen)

    def action_toggle_log_focus(self) -> None:
        """Toggle log focus screen."""
        # Check if we're already on LogFocusScreen
        if isinstance(self.screen, LogFocusScreen):
            # Pop back to main screen
            self.pop_screen()
        else:
            # Push LogFocusScreen
            log_focus_screen = LogFocusScreen()
            self.push_screen(log_focus_screen)

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