"""Operator panel widget for Switchboard TUI."""

from textual.widgets import Static
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class OperatorPanel(Static):
    """Panel showing operator and worker information."""

    def __init__(self):
        super().__init__("Operator Panel\nLoading...")
        self.add_class("operatorpanel")
        self.state: SwitchboardState = SwitchboardState()

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        workers = len(state.workers)
        stats = state.stats
        lines = [
            f"Workers: {workers}",
            f"Completed: {stats.completed_today}  Failed: {stats.failed_today}  Blocked: {stats.blocked_count}",
        ]
        if workers >= 3:
            lines.append("ALL LINES BUSY")
        try:
            self.update(Text("\n".join(lines)))
        except Exception:
            pass
