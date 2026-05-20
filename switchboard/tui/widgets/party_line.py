"""Party line widget for log display."""

from textual.widgets import Static
from rich.text import Text
from textual.containers import Vertical
from switchboard.tui.state import SwitchboardState, LogEvent
from collections import deque


class PartyLine(Static):
    """Widget for displaying log events with source switching."""

    def __init__(self):
        super().__init__()
        self.add_class("partyline")
        self.state: SwitchboardState = SwitchboardState()
        self.current_source = "daemon"
        self.log_entries = []
        self.log_content = ""
        self.header_text = "[DAEMON LOG]"

    @property
    def can_focus(self) -> bool:
        """Make the widget focusable for scrolling."""
        return True

    def update_state(self, state: SwitchboardState) -> None:
        """Update the widget with new state."""
        self.state = state
        self._refresh_content()

    def switch_source(self, source: str) -> None:
        """Switch log source (daemon, worker_1, worker_2, etc.)."""
        self.current_source = source
        if source == "daemon":
            self.header_text = "[DAEMON LOG]"
        elif source.startswith("worker_"):
            worker_num = source.split("_")[1]
            # Find the worker by index
            workers = list(self.state.workers.values())
            if int(worker_num) <= len(workers):
                worker = workers[int(worker_num) - 1]
                self.header_text = f"[WORKER {worker_num}: {worker.epic_id} {worker.agent}]"
            else:
                # Worker doesn't exist, don't change source
                return
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Refresh the widget content based on current state and source."""
        content_lines = []
        content_lines.append(self.header_text)
        content_lines.append("─" * len(self.header_text))

        if not self.state.events:
            if not self.state.daemon_online:
                content_lines.append("(waiting for daemon)")
            else:
                content_lines.append("(empty - waiting for events)")
        else:
            # Filter events based on current source
            filtered_events = self._filter_events_by_source()
            for event in filtered_events:
                formatted_line = self._format_log_event(event)
                content_lines.append(formatted_line)

        self.log_content = "\n".join(content_lines)
        try:
            self.update(Text(self.log_content))
        except Exception:
            # Handle case when widget is not in app context (during testing)
            pass

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
        # Extract time from timestamp
        try:
            parsed_time = event.parse_timestamp()
            time_str = parsed_time.strftime("%H:%M:%S")
        except:
            time_str = "??:??:??"

        # Translate to operator jargon based on event type
        if event.parsed_event_type:
            translated = self._translate_to_operator_jargon(event)
            return f"{time_str}  {translated}"
        else:
            # Pass through unrecognized events
            return f"{time_str}  {event.message}"

    def _translate_to_operator_jargon(self, event: LogEvent) -> str:
        """Translate events to operator jargon."""
        event_type = event.parsed_event_type

        if event_type == "daemon_started":
            return "DAEMON ONLINE"
        elif event_type == "daemon_stopped":
            return "DAEMON OFFLINE"
        elif event_type == "claimed":
            # Extract epic ID from message
            epic_id = self._extract_epic_id(event.message)
            return f"CONNECTING {epic_id}"
        elif event_type == "completed":
            epic_id = self._extract_epic_id(event.message)
            return f"LINE CLEAR ✓ ({epic_id})"
        elif event_type == "failed":
            epic_id = self._extract_epic_id(event.message)
            # Extract attempt info
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
        # Look for patterns like mol-xxx or epic-xxx
        match = re.search(r'(mol-\w+|epic-\w+)', message.lower())
        return match.group(1) if match else "unknown"

    def _extract_attempt_info(self, message: str) -> str:
        """Extract attempt information from failed message."""
        import re
        # Look for "attempt X/Y"
        match = re.search(r'attempt (\d+/\d+)', message.lower())
        return f"({match.group(1)})" if match else "(1/3)"

    def get_content(self) -> str:
        """Get current log content for testing."""
        return self.log_content