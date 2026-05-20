"""LogFocusScreen for full-height log viewing."""

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static
from textual.app import ComposeResult
from rich.text import Text

from ..state import SwitchboardState, LogEvent
from collections import deque


class LogFocusHeader(Static):
    """Header widget for log focus screen."""

    def __init__(self):
        super().__init__()
        self.add_class("log-focus-header")
        self.current_source = "daemon"
        self.state = SwitchboardState()

    def update_source(self, source: str, state: SwitchboardState) -> None:
        """Update the header with current source information."""
        self.current_source = source
        self.state = state

        if source == "daemon":
            header_text = "DAEMON LOG"
        elif source.startswith("worker_"):
            worker_num = source.split("_")[1]
            workers = list(state.workers.values())
            worker_index = int(worker_num) - 1

            if worker_index < len(workers):
                worker = workers[worker_index]
                header_text = f"WORKER {worker_num}: {worker.epic_id or 'unknown'} {worker.agent}"
            else:
                header_text = f"WORKER {worker_num}: (not active)"
        else:
            header_text = f"LOG SOURCE: {source.upper()}"

        # Add line count and time range info
        event_count = len(state.events)
        if event_count > 0:
            header_text += f" ({event_count} lines)"

            # Show time range if available
            try:
                first_event = list(state.events)[0]
                last_event = list(state.events)[-1]
                first_time = first_event.parse_timestamp().strftime("%H:%M")
                last_time = last_event.parse_timestamp().strftime("%H:%M")
                if first_time != last_time:
                    header_text += f" (showing last from {first_time} to {last_time})"
                else:
                    header_text += f" (at {last_time})"
            except:
                pass

        self.update(Text(header_text, style="bold green"))


class LogFocusContent(Static):
    """Content area for full-height log display."""

    def __init__(self):
        super().__init__()
        self.add_class("log-focus-content")
        self.current_source = "daemon"
        self.state = SwitchboardState()

    def update_content(self, source: str, state: SwitchboardState) -> None:
        """Update content for the specified source."""
        self.current_source = source
        self.state = state

        # Filter events by source
        filtered_events = self._filter_events_by_source()

        if not filtered_events:
            content_text = Text("(no events)", style="dim")
        else:
            content_lines = []
            for event in filtered_events:
                formatted_line = self._format_log_event(event)
                content_lines.append(formatted_line)

            content_text = Text("\n".join(content_lines))

        self.update(content_text)

        # Note: Auto-scroll would require ScrollableContainer

    def _filter_events_by_source(self) -> list:
        """Filter events based on current source."""
        if self.current_source == "daemon":
            # Return all events for daemon log
            return list(self.state.events)
        elif self.current_source.startswith("worker_"):
            # For worker logs, we'd filter by worker-specific events
            # For now, return empty as worker-specific logs aren't implemented
            return []
        return []

    def _format_log_event(self, event: LogEvent) -> str:
        """Format a log event for display."""
        try:
            parsed_time = event.parse_timestamp()
            time_str = parsed_time.strftime("%H:%M:%S")
        except:
            time_str = "??:??:??"

        # Use operator jargon like PartyLine
        if event.parsed_event_type:
            translated = self._translate_to_operator_jargon(event)
            return f"{time_str}  {translated}"
        else:
            return f"{time_str}  {event.message}"

    def _translate_to_operator_jargon(self, event: LogEvent) -> str:
        """Translate events to operator jargon."""
        event_type = event.parsed_event_type

        if event_type == "daemon_started":
            return "DAEMON ONLINE"
        elif event_type == "daemon_stopped":
            return "DAEMON OFFLINE"
        elif event_type == "claimed":
            epic_id = self._extract_epic_id(event.message)
            return f"CONNECTING {epic_id}"
        elif event_type == "completed":
            epic_id = self._extract_epic_id(event.message)
            return f"LINE CLEAR ✓ ({epic_id})"
        elif event_type == "failed":
            epic_id = self._extract_epic_id(event.message)
            attempt_info = self._extract_attempt_info(event.message)
            return f"DROPPED CALL · REDIALING {attempt_info} {epic_id}"
        elif event_type == "epic_completed":
            epic_id = self._extract_epic_id(event.message)
            return f"CALL COMPLETE ✓ ({epic_id})"
        else:
            return event.message

    def _extract_epic_id(self, message: str) -> str:
        """Extract epic ID from message."""
        import re
        match = re.search(r'(mol-\w+|epic-\w+)', message.lower())
        return match.group(1) if match else "unknown"

    def _extract_attempt_info(self, message: str) -> str:
        """Extract attempt information from failed message."""
        import re
        match = re.search(r'attempt (\d+/\d+)', message.lower())
        return f"({match.group(1)})" if match else "(1/3)"

    def get_visible_line_count(self) -> int:
        """Get the number of visible lines."""
        return self.content_size.height

    def get_content(self) -> str:
        """Get current content as string."""
        return str(self.renderable) if hasattr(self, 'renderable') else ""


class LogFocusScreen(Screen):
    """Full-screen log focus view."""

    BINDINGS = [
        Binding('escape', 'app.pop_screen', 'Back'),
        Binding('l', 'app.pop_screen', 'Back'),
        Binding('0', 'switch_daemon_log', 'Daemon'),
        Binding('1', 'switch_worker_1', 'Worker 1'),
        Binding('2', 'switch_worker_2', 'Worker 2'),
        Binding('3', 'switch_worker_3', 'Worker 3'),
        Binding('4', 'switch_worker_4', 'Worker 4'),
        Binding('5', 'switch_worker_5', 'Worker 5'),
        Binding('6', 'switch_worker_6', 'Worker 6'),
        Binding('7', 'switch_worker_7', 'Worker 7'),
        Binding('8', 'switch_worker_8', 'Worker 8'),
        Binding('9', 'switch_worker_9', 'Worker 9'),
    ]

    def __init__(self):
        super().__init__()
        self.current_source = "daemon"
        self.header_widget = LogFocusHeader()
        self.content_widget = LogFocusContent()

    def compose(self) -> ComposeResult:
        """Compose the full-screen log layout."""
        with Vertical():
            yield self.header_widget
            yield self.content_widget

    def on_mount(self) -> None:
        """Initialize the screen on mount."""
        # Set fullscreen styles
        self.styles.width = "100%"
        self.styles.height = "100%"

        # Get state from app and update content
        if hasattr(self.app, 'state'):
            self._update_display()

    def _update_display(self) -> None:
        """Update the display with current state."""
        state = getattr(self.app, 'state', SwitchboardState())
        self.header_widget.update_source(self.current_source, state)
        self.content_widget.update_content(self.current_source, state)

    def action_switch_daemon_log(self) -> None:
        """Switch to daemon log."""
        self.current_source = "daemon"
        self._update_display()

    def action_switch_worker_1(self) -> None:
        """Switch to worker 1."""
        self._switch_to_worker("worker_1")

    def action_switch_worker_2(self) -> None:
        """Switch to worker 2."""
        self._switch_to_worker("worker_2")

    def action_switch_worker_3(self) -> None:
        """Switch to worker 3."""
        self._switch_to_worker("worker_3")

    def action_switch_worker_4(self) -> None:
        """Switch to worker 4."""
        self._switch_to_worker("worker_4")

    def action_switch_worker_5(self) -> None:
        """Switch to worker 5."""
        self._switch_to_worker("worker_5")

    def action_switch_worker_6(self) -> None:
        """Switch to worker 6."""
        self._switch_to_worker("worker_6")

    def action_switch_worker_7(self) -> None:
        """Switch to worker 7."""
        self._switch_to_worker("worker_7")

    def action_switch_worker_8(self) -> None:
        """Switch to worker 8."""
        self._switch_to_worker("worker_8")

    def action_switch_worker_9(self) -> None:
        """Switch to worker 9."""
        self._switch_to_worker("worker_9")

    def _switch_to_worker(self, worker_source: str) -> None:
        """Switch to specified worker if it exists."""
        worker_num = int(worker_source.split("_")[1])
        state = getattr(self.app, 'state', SwitchboardState())

        if worker_num <= len(state.workers):
            self.current_source = worker_source
            self._update_display()