"""ProjectScreen for displaying project pipeline overview."""

from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Static
from textual.app import ComposeResult
from rich.text import Text
from typing import List

from ..state import SwitchboardState, PipelineState


class EpicGroup(Static):
    """Widget for displaying a group of epics by status."""

    def __init__(self, title: str, group_class: str):
        super().__init__()
        self.title = title
        self.add_class(group_class)
        self.add_class("epic-group")
        self.epics = []
        self.selected_epic = None

    def update_epics(self, epics: List[PipelineState]) -> None:
        """Update the epics displayed in this group."""
        self.epics = epics
        if epics and not self.selected_epic:
            self.selected_epic = epics[0].epic_id
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Refresh the group content."""
        lines = []

        # Group title
        lines.append(Text(f"■ {self.title.upper()}", style="bold white"))
        lines.append(Text("─" * (len(self.title) + 2), style="dim"))

        if not self.epics:
            lines.append(Text(f"  No {self.title.lower()} epics", style="dim"))
        else:
            for epic in self.epics:
                # Calculate progress
                total_steps = len(epic.steps)
                completed_steps = sum(1 for step in epic.steps if step.status == "closed")
                progress_text = f"{completed_steps}/{total_steps} steps"

                # Format epic line
                epic_line = f"  {epic.epic_id}: {epic.title} ({progress_text})"

                # Highlight selected epic
                style = "reverse" if epic.epic_id == self.selected_epic else "white"
                lines.append(Text(epic_line, style=style))

        lines.append("")  # Spacing

        # Combine all lines
        content_text = Text()
        for i, line in enumerate(lines):
            if i > 0:
                content_text.append("\n")
            content_text.append(line)

        self.update(content_text)

    def get_epic_list(self) -> List[str]:
        """Get list of epic IDs for testing."""
        return [epic.epic_id for epic in self.epics]

    def get_empty_state_message(self) -> str:
        """Get empty state message."""
        return f"No {self.title.lower()} epics"

    def select_epic(self, epic_id: str) -> None:
        """Select an epic."""
        if any(epic.epic_id == epic_id for epic in self.epics):
            self.selected_epic = epic_id
            self._refresh_content()

    def select_next_epic(self) -> None:
        """Select the next epic in the list."""
        if not self.epics or not self.selected_epic:
            return

        current_index = next(
            (i for i, epic in enumerate(self.epics) if epic.epic_id == self.selected_epic),
            0
        )

        next_index = (current_index + 1) % len(self.epics)
        self.selected_epic = self.epics[next_index].epic_id
        self._refresh_content()

    def select_previous_epic(self) -> None:
        """Select the previous epic in the list."""
        if not self.epics or not self.selected_epic:
            return

        current_index = next(
            (i for i, epic in enumerate(self.epics) if epic.epic_id == self.selected_epic),
            0
        )

        prev_index = (current_index - 1) % len(self.epics)
        self.selected_epic = self.epics[prev_index].epic_id
        self._refresh_content()


class ProjectScreen(Screen):
    """Screen for displaying project pipeline overview."""

    BINDINGS = [
        Binding('escape', 'app.pop_screen', 'Back'),
        Binding('d', 'show_epic_detail', 'Epic Detail'),
        Binding('up', 'select_previous_epic', 'Previous Epic'),
        Binding('down', 'select_next_epic', 'Next Epic'),
        Binding('tab', 'focus_next', 'Next Group'),
    ]

    def __init__(self, project_name: str):
        super().__init__()
        self.project_name = project_name

    def compose(self) -> ComposeResult:
        """Compose the project screen layout."""
        with Vertical():
            # Project header
            header_text = f"PROJECT: {self.project_name.upper()}"
            yield Static(Text(header_text, style="bold yellow"))
            yield Static(Text("═" * len(header_text), style="dim"))

            # Epic groups
            with Horizontal():
                with Vertical():
                    yield EpicGroup("Active", "active-epics-group")
                    yield EpicGroup("Queued", "queued-epics-group")
                with Vertical():
                    yield EpicGroup("Completed", "completed-epics-group")

    def on_mount(self) -> None:
        """Initialize the screen on mount."""
        self._update_epic_groups()

        # Focus the active group
        active_group = self.query_one(".active-epics-group")
        active_group.focus()

    def _update_epic_groups(self) -> None:
        """Update epic groups with current state."""
        state = getattr(self.app, 'state', SwitchboardState())

        # Filter pipelines by project
        project_pipelines = [
            pipeline for pipeline in state.pipelines.values()
            if pipeline.project == self.project_name
        ]

        # Group epics by status
        active_epics = []
        completed_epics = []
        queued_epics = []

        for pipeline in project_pipelines:
            # Determine status based on steps
            if not pipeline.steps:
                queued_epics.append(pipeline)
            elif all(step.status == "closed" for step in pipeline.steps):
                completed_epics.append(pipeline)
            elif any(step.status in ["in_progress", "open"] for step in pipeline.steps):
                active_epics.append(pipeline)
            else:
                # All steps are blocked
                queued_epics.append(pipeline)

        # Update groups
        active_group = self.query_one(".active-epics-group")
        completed_group = self.query_one(".completed-epics-group")
        queued_group = self.query_one(".queued-epics-group")

        active_group.update_epics(active_epics)
        completed_group.update_epics(completed_epics)
        queued_group.update_epics(queued_epics)

    def action_show_epic_detail(self) -> None:
        """Show detail for the selected epic."""
        focused_group = self.app.focused
        if isinstance(focused_group, EpicGroup) and focused_group.selected_epic:
            # Import here to avoid circular import
            from .detail import DetailScreen
            detail_screen = DetailScreen(focused_group.selected_epic)
            self.app.push_screen(detail_screen)

    def action_select_next_epic(self) -> None:
        """Select next epic in focused group."""
        focused_group = self.app.focused
        if isinstance(focused_group, EpicGroup):
            focused_group.select_next_epic()

    def action_select_previous_epic(self) -> None:
        """Select previous epic in focused group."""
        focused_group = self.app.focused
        if isinstance(focused_group, EpicGroup):
            focused_group.select_previous_epic()

    def on_focus(self) -> None:
        """Refresh data when screen gains focus."""
        self._update_epic_groups()