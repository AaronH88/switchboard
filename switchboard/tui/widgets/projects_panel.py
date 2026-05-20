"""Projects panel widget for Switchboard TUI."""

from textual.widgets import Static
from rich.text import Text
from switchboard.tui.state import SwitchboardState


class ProjectsPanel(Static):
    """Panel showing project information."""

    def __init__(self):
        super().__init__()
        self.add_class("projectspanel")
        self.state: SwitchboardState = SwitchboardState()

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Refresh the widget content based on current state."""
        content_lines = []

        # Project count
        content_lines.append(f"Projects: {len(self.state.projects)}")

        # List projects
        for project_name, project_info in self.state.projects.items():
            content_lines.append(f"• {project_name} ({project_info.active_lines} lines)")

        if not self.state.projects:
            content_lines.append("No projects")

        try:
            self.update(Text("\n".join(content_lines)))
        except Exception:
            # Handle case when widget is not in app context (during testing)
            pass

    def compose(self):
        """Compose the initial content."""
        yield Static("Projects", classes="panel-title")
        yield Static("Loading...", id="content")