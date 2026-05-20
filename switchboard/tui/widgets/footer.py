"""Footer widget for Switchboard TUI."""

from textual.widgets import Static
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class SwitchboardFooter(Static):
    """Footer with keybinding hints and daemon status."""

    def __init__(self):
        super().__init__("Q:Quit  Tab:Navigate  R:Refresh  1-9:Workers  0:Daemon")
        self.add_class("footer")
        self.state: SwitchboardState = SwitchboardState()

    def update_state(self, state: SwitchboardState) -> None:
        self.state = state
        lamp = "(*)" if state.daemon_online else "(x)"
        status = "ONLINE" if state.daemon_online else "OFFLINE"
        hints = "Q:Quit  Tab:Navigate  R:Refresh  1-9:Workers  0:Daemon"
        try:
            self.update(Text(f"{hints}     daemon: {lamp} {status}"))
        except Exception:
            pass
