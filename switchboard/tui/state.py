"""State management dataclasses for Switchboard TUI."""

from dataclasses import dataclass, field, replace
from typing import Optional, List, Dict, Any
from collections import deque
from datetime import datetime
import re


@dataclass
class WorkerState:
    """State for a worker process."""
    bead_id: str
    agent: str
    repo: str
    tool: Optional[str]
    pid: int
    started_at: str
    title: str
    epic_id: Optional[str]

    def update(self, **kwargs) -> 'WorkerState':
        """Update worker state with new field values."""
        # Check for non-existent fields
        for key in kwargs:
            if not hasattr(self, key):
                raise AttributeError(f"WorkerState has no field '{key}'")

        return replace(self, **kwargs)


@dataclass
class StepState:
    """State for a pipeline step."""
    bead_id: str
    agent: str
    status: str

    def __post_init__(self):
        """Validate status value."""
        valid_statuses = {"open", "in_progress", "closed", "blocked"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status '{self.status}'. Must be one of: {valid_statuses}")

    def transition_to(self, new_status: str) -> 'StepState':
        """Transition to a new status with validation."""
        valid_statuses = {"open", "in_progress", "closed", "blocked"}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {valid_statuses}")

        # Prevent invalid transitions
        if self.status == "closed" and new_status == "in_progress":
            raise ValueError("Cannot transition from 'closed' to 'in_progress'")

        return replace(self, status=new_status)


@dataclass
class PipelineState:
    """State for a complete pipeline."""
    epic_id: str
    title: str
    project: str
    repo: str
    steps: List[StepState] = field(default_factory=list)

    def add_step(self, step: StepState) -> 'PipelineState':
        """Add or update a step in the pipeline."""
        new_steps = []
        step_found = False

        for existing_step in self.steps:
            if existing_step.bead_id == step.bead_id:
                # Update existing step
                new_steps.append(step)
                step_found = True
            else:
                new_steps.append(existing_step)

        if not step_found:
            # Add new step
            new_steps.append(step)

        return replace(self, steps=new_steps)


@dataclass
class LogEvent:
    """A log event from agent_router.log."""
    timestamp: str
    level: str
    message: str
    parsed_event_type: Optional[str] = None

    def __post_init__(self):
        """Validate level value."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level not in valid_levels:
            raise ValueError(f"Invalid log level '{self.level}'. Must be one of: {valid_levels}")

    def parse_timestamp(self) -> datetime:
        """Parse timestamp string to datetime object."""
        # Handle various timestamp formats
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S%z",
        ]

        # Remove timezone suffix if present for simpler parsing
        timestamp_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', self.timestamp)
        timestamp_clean = re.sub(r'[+-]\d{4}$', '', timestamp_clean)

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_clean, fmt)
            except ValueError:
                continue

        # Fallback - try to parse just the date part
        try:
            return datetime.strptime(timestamp_clean[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError(f"Unable to parse timestamp: {self.timestamp}")

    def detect_event_type(self) -> Optional[str]:
        """Detect event type from log message."""
        message_lower = self.message.lower()

        # Check more specific patterns first
        if "epic completed:" in message_lower:
            return "epic_completed"
        elif "switchboard started" in message_lower:
            return "daemon_started"
        elif "switchboard stopped" in message_lower:
            return "daemon_stopped"
        elif self._is_well_formed_claimed():
            return "claimed"
        elif self._is_well_formed_completed():
            return "completed"
        elif self._is_well_formed_failed():
            return "failed"

        return None

    def _is_well_formed_claimed(self) -> bool:
        """Check if message is a well-formed 'claimed' event."""
        message_lower = self.message.lower()
        if "claimed" not in message_lower:
            return False

        if not re.search(r'\w+-\w+', message_lower):
            return False

        # Check for proper format with parentheses and key parameters
        if "(" in self.message and ")" in self.message:
            # Should have agent parameter AND either repo or project parameter
            if "agent:" in message_lower and ("repo:" in message_lower or "project:" in message_lower):
                return True

        return False

    def _is_well_formed_completed(self) -> bool:
        """Check if message is a well-formed 'completed' event."""
        message_lower = self.message.lower()
        if "completed" not in message_lower:
            return False

        if not re.search(r'\w+-\w+', message_lower):
            return False

        # Check for proper format with parentheses and key parameters
        if "(" in self.message and ")" in self.message:
            # Should have agent parameter (completed events only need agent)
            if "agent:" in message_lower:
                return True

        return False

    def _is_well_formed_failed(self) -> bool:
        """Check if message is a well-formed 'failed' event."""
        message_lower = self.message.lower()
        if "failed" not in message_lower:
            return False

        if not re.search(r'\w+-\w+', message_lower):
            return False

        # Should have attempt info
        if "attempt" in message_lower:
            return True

        return False


@dataclass
class StatsSnapshot:
    """Statistics snapshot."""
    completed_today: int = 0
    failed_today: int = 0
    blocked_count: int = 0


@dataclass
class ProjectInfo:
    """Project information."""
    name: str
    path: str
    active_lines: int


@dataclass
class SwitchboardState:
    """Complete switchboard state."""
    workers: Dict[str, WorkerState] = field(default_factory=dict)
    pipelines: Dict[str, PipelineState] = field(default_factory=dict)
    projects: Dict[str, ProjectInfo] = field(default_factory=dict)
    stats: StatsSnapshot = field(default_factory=StatsSnapshot)
    daemon_online: bool = False
    events: deque = field(default_factory=lambda: deque(maxlen=1000))

    def add_worker(self, worker: WorkerState) -> 'SwitchboardState':
        """Add a worker to the state."""
        if worker.bead_id is None:
            raise ValueError("Worker bead_id cannot be None")

        new_workers = self.workers.copy()
        new_workers[worker.bead_id] = worker

        return replace(self, workers=new_workers)

    def remove_worker(self, bead_id: str) -> 'SwitchboardState':
        """Remove a worker from the state."""
        new_workers = self.workers.copy()
        new_workers.pop(bead_id, None)  # Don't error if not found

        return replace(self, workers=new_workers)

    def update_stats(self, stats: StatsSnapshot) -> 'SwitchboardState':
        """Update statistics."""
        if stats is None:
            raise ValueError("Stats cannot be None")

        return replace(self, stats=stats)

    def add_log_event(self, event: LogEvent) -> 'SwitchboardState':
        """Add a log event to the events deque."""
        new_events = self.events.copy()
        new_events.append(event)

        return replace(self, events=new_events)

    def reconcile_pipelines(self, pipeline_data: Dict[str, Dict[str, Any]]) -> 'SwitchboardState':
        """Reconcile pipelines from polling data."""
        new_pipelines = {}
        for epic_id, pdata in pipeline_data.items():
            steps = []
            for s in pdata.get("steps", []):
                status = s.get("status", "open")
                if status not in ("open", "in_progress", "closed", "blocked"):
                    status = "open"
                steps.append(StepState(
                    bead_id=s["bead_id"],
                    agent=s["agent"],
                    status=status,
                ))
            new_pipelines[epic_id] = PipelineState(
                epic_id=epic_id,
                title=pdata.get("title", ""),
                project=pdata.get("project", "unknown"),
                repo=pdata.get("repo", "unknown"),
                steps=steps,
            )
        return replace(self, pipelines=new_pipelines)

    def reconcile_workers(self, current_workers: List[Dict[str, Any]]) -> 'SwitchboardState':
        """Reconcile workers with current state from polling."""
        new_workers = {}

        for worker_data in current_workers:
            labels = worker_data.get("labels", [])
            agent = next((l.split(":", 1)[1] for l in labels if l.startswith("agent:")), "unknown")
            repo = next((l.split(":", 1)[1] for l in labels if l.startswith("repo:")), "unknown")
            tool = next((l.split(":", 1)[1] for l in labels if l.startswith("tool:")), None)

            deps = worker_data.get("dependencies", [])
            epic_id = next((d.get("depends_on_id", d.get("issue_id", "")) for d in deps if d.get("type") == "parent"), None)

            worker = WorkerState(
                bead_id=worker_data["id"],
                agent=agent,
                repo=repo,
                tool=tool,
                pid=None,
                started_at=worker_data.get("started_at", worker_data.get("created_at", "")),
                title=worker_data.get("title", ""),
                epic_id=epic_id,
            )
            new_workers[worker.bead_id] = worker

        return replace(self, workers=new_workers)