"""Active lines widget for showing active workers."""

from textual.widgets import Static
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class ActiveLines(Static):
    """Widget showing active worker lines."""

    def __init__(self):
        super().__init__("Active Lines\nNo active workers")
        self.add_class("activelines")
        self.state: SwitchboardState = SwitchboardState()

    @property
    def can_focus(self) -> bool:
        return True

    def update_state(self, state: SwitchboardState) -> None:
        self.state = state
        lines = ["ACTIVE LINES"]
        if not state.workers:
            lines.append("  ( ) No active workers")
        else:
            for i, (bead_id, w) in enumerate(sorted(state.workers.items()), 1):
                tool = w.tool or "claude"
                lines.append(
                    f"  (*) {i}  {w.bead_id}  {w.agent:<12} {w.repo:<10} {tool:<8} CONNECTED"
                )
        try:
            self.update(Text("\n".join(lines)))
        except Exception:
            pass
