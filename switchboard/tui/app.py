"""Switchboard TUI Textual application.

Dependencies:
- textual: Required for TUI framework
"""

from pathlib import Path
from typing import Optional, Any
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static


class SwitchboardApp(App):
    """Switchboard TUI application."""

    CSS_PATH = Path(__file__).parent / "switchboard.tcss"
    TITLE = "Switchboard TUI"
    SUB_TITLE = "Agent Pipeline Monitor"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(self, **kwargs: Any):
        """Initialize the app with optional configuration."""
        super().__init__()
        self.config = kwargs

        # Store configuration
        self.artifacts_dir = kwargs.get('artifacts_dir', 'artifacts/')
        self.poll_interval = kwargs.get('poll_interval', 10)

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Static("Switchboard TUI - Press 'q' to quit", classes="placeholder")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    @property
    def css_path(self) -> Optional[Path]:
        """Return CSS path if file exists."""
        if hasattr(self, 'CSS_PATH') and self.CSS_PATH and self.CSS_PATH.exists():
            return self.CSS_PATH
        return None