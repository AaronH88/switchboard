"""Switchboard header widget."""

from textual.widgets import Header
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