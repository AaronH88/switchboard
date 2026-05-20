"""Switchboard header widget."""

from textual.widgets import Header
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class SwitchboardHeader(Header):
    """Header widget for Switchboard TUI."""

    def __init__(self):
        super().__init__(show_clock=True)
        self.add_class("switchboardheader")
        self.state: SwitchboardState = SwitchboardState()

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        self._update_daemon_status()

    def _update_daemon_status(self) -> None:
        """Update daemon status in header."""
        if not self.state.daemon_online:
            # Override the title to show daemon offline status
            self.title = "NO DIAL TONE · DAEMON UNREACHABLE"
            self.sub_title = "Connection Lost"
        else:
            self.title = "Switchboard TUI"
            self.sub_title = "Agent Pipeline Monitor"

    def get_daemon_status(self) -> str:
        """Get daemon status text for testing."""
        if self.state.daemon_online:
            return "ONLINE"
        else:
            return "NO DIAL TONE · DAEMON UNREACHABLE"

    def get_daemon_status_classes(self) -> list:
        """Get CSS classes for daemon status."""
        if self.state.daemon_online:
            return ["online"]
        else:
            return ["warning", "offline"]