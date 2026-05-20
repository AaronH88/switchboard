"""Operator panel widget for Switchboard TUI."""

from textual.widgets import Static
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class OperatorPanel(Static):
    """Panel showing operator and worker information."""

    def __init__(self):
        super().__init__()
        self.add_class("operatorpanel")
        self.state: SwitchboardState = SwitchboardState()
        self.worker_count = 0

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        self.worker_count = len(state.workers)
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Refresh the widget content based on current state."""
        content_lines = []

        # Worker count
        content_lines.append(f"Workers: {self.worker_count}")

        # Stats
        content_lines.append(f"Completed: {self.state.stats.completed_today}")
        content_lines.append(f"Failed: {self.state.stats.failed_today}")
        content_lines.append(f"Blocked: {self.state.stats.blocked_count}")

        try:
            self.update(Text("\n".join(content_lines)))
        except Exception:
            # Handle case when widget is not in app context (during testing)
            pass

    def compose(self):
        """Compose the initial content."""
        yield Static("Operator Panel", classes="panel-title")
        yield Static("Loading...", id="content")