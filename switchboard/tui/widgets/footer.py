"""Footer widget for Switchboard TUI."""

from textual.widgets import Footer
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class Footer(Footer):
    """Footer widget with keybinding hints and daemon status."""

    def __init__(self):
        super().__init__()
        self.add_class("footer")
        self.state: SwitchboardState = SwitchboardState()
        self.hints_text = "Q:Quit  Tab:Navigate  R:Refresh  1-9:Workers  0:Daemon"
        self.status_text = "(✗) DAEMON OFFLINE"
        self.daemon_status_text = "(✗) DAEMON OFFLINE"

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        self._update_daemon_status()

    def _update_daemon_status(self) -> None:
        """Update daemon status text."""
        if self.state.daemon_online:
            self.daemon_status_text = "(*) DAEMON ONLINE"
            self.status_text = "(*) DAEMON ONLINE"
        else:
            self.daemon_status_text = "(✗) DAEMON OFFLINE"
            self.status_text = "(✗) DAEMON OFFLINE"

    def update_hints_for_focus(self, focused_widget_name: str) -> None:
        """Update hints based on focused widget."""
        focus_hint_mapping = {
            "PatchPanel": "Q:Quit  D:Details  R:Refresh  ↑↓:Scroll  Tab:Navigate",
            "PartyLine": "Q:Quit  L:Focus  1-9:Workers  0:Daemon  ↑↓:Scroll  Tab:Navigate",
            "ActiveLines": "Q:Quit  D:Details  R:Refresh  ↑↓:Scroll  Tab:Navigate"
        }

        self.hints_text = focus_hint_mapping.get(
            focused_widget_name,
            "Q:Quit  Tab:Navigate  R:Refresh  1-9:Workers  0:Daemon"
        )