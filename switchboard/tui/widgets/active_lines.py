"""Active lines widget for showing active workers."""

from textual.widgets import Static
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class ActiveLines(Static):
    """Widget showing active worker lines."""

    def __init__(self):
        super().__init__()
        self.add_class("activelines")
        self.state: SwitchboardState = SwitchboardState()

    @property
    def can_focus(self) -> bool:
        """Make the widget focusable."""
        return True

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Refresh the widget content based on current state."""
        content_lines = []
        content_lines.append("Active Lines")
        content_lines.append("=" * 20)

        if not self.state.workers:
            content_lines.append("No active workers")
        else:
            for i, (bead_id, worker) in enumerate(sorted(self.state.workers.items()), 1):
                line = f"Line {i}: {worker.epic_id} ({worker.agent})"
                content_lines.append(line)

        try:
            self.update(Text("\n".join(content_lines)))
        except Exception:
            # Handle case when widget is not in app context (during testing)
            pass

    def get_worker_list(self) -> list:
        """Get list of worker bead_ids (for testing)."""
        return list(self.state.workers.keys())