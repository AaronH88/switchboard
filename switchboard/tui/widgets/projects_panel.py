"""Projects panel widget for Switchboard TUI."""

from textual.widgets import Static
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class ProjectsPanel(Static):
    """Panel showing project information."""

    def __init__(self):
        super().__init__("Projects\nLoading...")
        self.add_class("projectspanel")
        self.state: SwitchboardState = SwitchboardState()

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        lines = ["PROJECTS"]
        if state.projects:
            for name, info in state.projects.items():
                lamp = "(*)" if info.active_lines > 0 else "( )"
                lines.append(f"{lamp} {name}  {info.active_lines} active")
        else:
            workers_by_project = {}
            for w in state.workers.values():
                p = w.repo or "unknown"
                workers_by_project[p] = workers_by_project.get(p, 0) + 1
            if workers_by_project:
                for name, count in workers_by_project.items():
                    lines.append(f"(*) {name}  {count} active")
            else:
                lines.append("( ) No active projects")
        try:
            self.update(Text("\n".join(lines)))
        except Exception:
            pass
