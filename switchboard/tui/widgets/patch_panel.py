"""Patch panel widget for pipeline visualization."""

from textual.widgets import Static
from rich.text import Text
from textual.containers import Vertical
from switchboard.tui.state import SwitchboardState, PipelineState, StepState


class PatchPanel(Static):
    """Panel showing pipeline and step information."""

    def __init__(self):
        super().__init__()
        self.add_class("patchpanel")
        self.state: SwitchboardState = SwitchboardState()
        self.pipelines_displayed = []

    @property
    def can_focus(self) -> bool:
        """Make the panel focusable for scrolling."""
        return True

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        self.pipelines_displayed = list(state.pipelines.keys())
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Refresh the widget content based on current state."""
        if not self.state.pipelines and not self.state.workers:
            # Check for "all quiet" state
            empty_message = self.get_empty_state_message()
            try:
                self.update(Text(empty_message))
            except Exception:
                # Handle case when widget is not mounted (during testing)
                pass
            return
        elif not self.state.pipelines:
            try:
                self.update(Text("No active pipelines"))
            except Exception:
                # Handle case when widget is not mounted (during testing)
                pass
            return

        # Build all pipeline text and update in one call
        lines = []
        for epic_id in sorted(self.state.pipelines.keys()):
            pipeline = self.state.pipelines[epic_id]
            lines.append(self._render_pipeline_text(pipeline))

        try:
            self.update(Text("\n\n".join(lines)))
        except Exception:
            pass

    def _render_pipeline_text(self, pipeline: PipelineState) -> str:
        """Render a single pipeline as text."""
        title = f"{pipeline.project} / {pipeline.repo}  #{pipeline.epic_id}"
        completed_count = len([s for s in pipeline.steps if s.status == "closed"])
        total_count = len(pipeline.steps)
        progress = f"{completed_count}/{total_count} done"

        PIPELINE_ORDER = ["tdd", "tests", "development", "verify", "review", "integrate"]
        sorted_steps = sorted(pipeline.steps,
            key=lambda s: PIPELINE_ORDER.index(s.agent) if s.agent in PIPELINE_ORDER else 99)

        step_display = []
        for step in sorted_steps:
            label = self._get_step_label(step.agent)
            status_symbol = self._get_status_symbol(step.status)
            step_display.append(f"{label} {status_symbol}")

        step_row = " │ ".join(step_display)
        width = len(step_row) + 4
        lines = [
            f"{title}  {progress}",
            "┌" + "─" * (width - 2) + "┐",
            "│ " + step_row + " │",
            "└" + "─" * (width - 2) + "┘",
        ]

        worker_info = self._get_worker_info_for_pipeline(pipeline)
        if worker_info:
            lines.append(worker_info)

        return "\n".join(lines)

    def _get_step_label(self, agent: str) -> str:
        """Get abbreviated label for step agent."""
        label_mappings = {
            "tdd": "TDD",
            "tests": "TEST",
            "development": "DEV",
            "verify": "VRFY",
            "review": "REVW",
            "integrate": "INTG"
        }
        return label_mappings.get(agent, agent[:4].upper())

    def _get_status_symbol(self, status: str) -> str:
        """Get symbol for step status."""
        status_symbols = {
            "open": "( )",
            "in_progress": "(*)",
            "closed": "(✓)",
            "blocked": "(✗)"
        }
        return status_symbols.get(status, "(?)")

    def _get_worker_info_for_pipeline(self, pipeline: PipelineState) -> str:
        """Get worker info string if there's an active worker."""
        # Find in-progress step
        in_progress_step = next(
            (s for s in pipeline.steps if s.status == "in_progress"),
            None
        )
        if not in_progress_step:
            return ""

        # Find matching worker
        worker = self.state.workers.get(in_progress_step.bead_id)
        if not worker:
            return ""

        # Calculate elapsed time (simplified for now)
        tool = worker.tool or "claude"
        return f"                  └── {tool} · working"

    def get_empty_state_message(self) -> str:
        """Get empty state message when no activity."""
        # Check if we truly have no activity
        if not self.state.workers and not self.state.pipelines:
            return "ALL QUIET ON THE BOARD · OPERATOR STANDING BY"
        return "No active pipelines"

    def get_content(self) -> str:
        """Get current panel content for testing."""
        if hasattr(self, 'renderable') and hasattr(self.renderable, 'plain'):
            return self.renderable.plain
        return ""