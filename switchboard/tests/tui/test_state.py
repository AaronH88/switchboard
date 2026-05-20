"""Tests for TUI state management dataclasses."""

from datetime import datetime
from collections import deque
import pytest
from switchboard.tui.state import (
    WorkerState, StepState, PipelineState, LogEvent,
    StatsSnapshot, ProjectInfo, SwitchboardState
)


class TestWorkerState:
    """Tests for WorkerState dataclass."""

    def test_worker_state_creation(self):
        """Test WorkerState instance creation with valid fields."""
        worker = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Implement user authentication",
            epic_id="epic-xyz"
        )

        assert worker.bead_id == "mol-2hn"
        assert worker.agent == "development"
        assert worker.repo == "nexus"
        assert worker.tool is None
        assert worker.pid == 12345
        assert worker.started_at == "2026-05-20T14:23:01"
        assert worker.title == "Implement user authentication"
        assert worker.epic_id == "epic-xyz"

    def test_worker_state_creation_edge_cases(self):
        """Test WorkerState creation with edge case values."""
        # Empty string for title
        worker = WorkerState(
            bead_id="mol-abc",
            agent="tests",
            repo="ui",
            tool="pytest",
            pid=98765,
            started_at="2026-05-20T15:30:00",
            title="",
            epic_id="epic-123"
        )
        assert worker.title == ""

        # Future timestamp
        worker = WorkerState(
            bead_id="mol-future",
            agent="review",
            repo="api",
            tool=None,
            pid=11111,
            started_at="2027-01-01T00:00:00",
            title="Future task",
            epic_id=None
        )
        assert worker.started_at == "2027-01-01T00:00:00"
        assert worker.epic_id is None

    def test_worker_state_update(self):
        """Test WorkerState update functionality."""
        original = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Original title",
            epic_id="epic-xyz"
        )

        # Should be able to update fields (assuming dataclass replace method)
        updated = original.update(title="Updated title", tool="pytest")
        assert updated.title == "Updated title"
        assert updated.tool == "pytest"
        assert updated.bead_id == "mol-2hn"  # Other fields unchanged

    def test_worker_state_update_with_none_values(self):
        """Test WorkerState update with None values."""
        original = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool="pytest",
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test title",
            epic_id="epic-xyz"
        )

        updated = original.update(tool=None, epic_id=None)
        assert updated.tool is None
        assert updated.epic_id is None

    def test_worker_state_update_nonexistent_field(self):
        """Test WorkerState update with non-existent field raises error."""
        worker = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test title",
            epic_id="epic-xyz"
        )

        with pytest.raises(AttributeError):
            worker.update(nonexistent_field="value")

    def test_worker_state_equality(self):
        """Test WorkerState equality comparison."""
        worker1 = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test title",
            epic_id="epic-xyz"
        )

        worker2 = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test title",
            epic_id="epic-xyz"
        )

        worker3 = WorkerState(
            bead_id="mol-different",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test title",
            epic_id="epic-xyz"
        )

        # Identical states should be equal
        assert worker1 == worker2

        # Different bead_id should not be equal
        assert worker1 != worker3


class TestStepState:
    """Tests for StepState dataclass."""

    @pytest.mark.parametrize("status", ["open", "in_progress", "closed", "blocked"])
    def test_step_state_valid_statuses(self, status):
        """Test StepState with each valid status value."""
        step = StepState(
            bead_id="mol-2hn",
            agent="development",
            status=status
        )
        assert step.status == status

    @pytest.mark.parametrize("status", ["pending", "failed", "unknown", None, 123])
    def test_step_state_invalid_status(self, status):
        """Test StepState with invalid status values raises error."""
        with pytest.raises((ValueError, TypeError)):
            StepState(
                bead_id="mol-2hn",
                agent="development",
                status=status
            )

    def test_step_state_status_transition_valid(self):
        """Test valid status transitions."""
        # open → in_progress
        step = StepState(bead_id="mol-1", agent="dev", status="open")
        step = step.transition_to("in_progress")
        assert step.status == "in_progress"

        # in_progress → closed
        step = step.transition_to("closed")
        assert step.status == "closed"

        # blocked → any status (after unblock)
        step = StepState(bead_id="mol-2", agent="dev", status="blocked")
        step = step.transition_to("in_progress")
        assert step.status == "in_progress"

    def test_step_state_status_transition_invalid(self):
        """Test invalid status transitions raise error."""
        # closed → in_progress (invalid)
        step = StepState(bead_id="mol-1", agent="dev", status="closed")
        with pytest.raises(ValueError):
            step.transition_to("in_progress")


class TestPipelineState:
    """Tests for PipelineState dataclass."""

    def test_pipeline_state_empty_steps(self):
        """Test PipelineState with empty steps list."""
        pipeline = PipelineState(
            epic_id="epic-xyz",
            title="Test Pipeline",
            project="myapp",
            repo="api",
            steps=[]
        )
        assert pipeline.steps == []
        assert isinstance(pipeline.steps, list)

    def test_pipeline_state_steps_ordering(self):
        """Test PipelineState maintains steps order."""
        step1 = StepState(bead_id="mol-1", agent="tdd", status="closed")
        step2 = StepState(bead_id="mol-2", agent="interface", status="open")
        step3 = StepState(bead_id="mol-3", agent="tests", status="open")

        pipeline = PipelineState(
            epic_id="epic-xyz",
            title="Test Pipeline",
            project="myapp",
            repo="api",
            steps=[step1, step2, step3]
        )

        assert pipeline.steps[0].bead_id == "mol-1"
        assert pipeline.steps[1].bead_id == "mol-2"
        assert pipeline.steps[2].bead_id == "mol-3"

    def test_pipeline_state_duplicate_bead_ids(self):
        """Test PipelineState handling of duplicate bead_ids."""
        step1 = StepState(bead_id="mol-1", agent="tdd", status="closed")
        step2 = StepState(bead_id="mol-1", agent="interface", status="open")  # duplicate

        # Should handle duplicate bead_ids gracefully
        pipeline = PipelineState(
            epic_id="epic-xyz",
            title="Test Pipeline",
            project="myapp",
            repo="api",
            steps=[step1, step2]
        )
        assert len(pipeline.steps) == 2

    def test_pipeline_state_add_step(self):
        """Test adding step to pipeline."""
        pipeline = PipelineState(
            epic_id="epic-xyz",
            title="Test Pipeline",
            project="myapp",
            repo="api",
            steps=[]
        )

        new_step = StepState(bead_id="mol-1", agent="tdd", status="open")
        updated_pipeline = pipeline.add_step(new_step)

        assert len(updated_pipeline.steps) == 1
        assert updated_pipeline.steps[0].bead_id == "mol-1"

    def test_pipeline_state_add_step_update_existing(self):
        """Test adding step updates existing step with same bead_id."""
        existing_step = StepState(bead_id="mol-1", agent="tdd", status="open")
        pipeline = PipelineState(
            epic_id="epic-xyz",
            title="Test Pipeline",
            project="myapp",
            repo="api",
            steps=[existing_step]
        )

        updated_step = StepState(bead_id="mol-1", agent="tdd", status="closed")
        updated_pipeline = pipeline.add_step(updated_step)

        assert len(updated_pipeline.steps) == 1
        assert updated_pipeline.steps[0].status == "closed"


class TestLogEvent:
    """Tests for LogEvent dataclass."""

    @pytest.mark.parametrize("timestamp_str,expected_format", [
        ("2026-05-20T14:23:01", "ISO format"),
        ("2026-05-20 14:23:01", "Log format"),
        ("2026-05-20 14:23:01+00:00", "With timezone"),
    ])
    def test_log_event_timestamp_parsing(self, timestamp_str, expected_format):
        """Test LogEvent timestamp parsing for various formats."""
        event = LogEvent(
            timestamp=timestamp_str,
            level="INFO",
            message="Test message",
            parsed_event_type=None
        )

        parsed_timestamp = event.parse_timestamp()
        assert isinstance(parsed_timestamp, datetime)

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_log_event_level_validation_valid(self, level):
        """Test LogEvent with valid log levels."""
        event = LogEvent(
            timestamp="2026-05-20 14:23:01",
            level=level,
            message="Test message",
            parsed_event_type=None
        )
        assert event.level == level

    @pytest.mark.parametrize("level", ["TRACE", "FATAL", None, 123])
    def test_log_event_level_validation_invalid(self, level):
        """Test LogEvent with invalid log levels raises error."""
        with pytest.raises((ValueError, TypeError)):
            LogEvent(
                timestamp="2026-05-20 14:23:01",
                level=level,
                message="Test message",
                parsed_event_type=None
            )

    @pytest.mark.parametrize("message,expected_type", [
        ("Claimed mol-2hn (agent: development)", "claimed"),
        ("Completed mol-2hn (agent: development)", "completed"),
        ("Failed mol-2hn attempt 1/3", "failed"),
        ("Epic completed: epic-xyz", "epic_completed"),
        ("Switchboard started", "daemon_started"),
        ("Random log message", None),
    ])
    def test_log_event_parsed_event_type_extraction(self, message, expected_type):
        """Test LogEvent event type classification."""
        event = LogEvent(
            timestamp="2026-05-20 14:23:01",
            level="INFO",
            message=message,
            parsed_event_type=None
        )

        detected_type = event.detect_event_type()
        assert detected_type == expected_type


class TestStatsSnapshot:
    """Tests for StatsSnapshot dataclass."""

    def test_stats_snapshot_creation(self):
        """Test StatsSnapshot creation with default values."""
        stats = StatsSnapshot()
        assert stats.completed_today == 0
        assert stats.failed_today == 0
        assert stats.blocked_count == 0

    def test_stats_snapshot_with_values(self):
        """Test StatsSnapshot creation with specific values."""
        stats = StatsSnapshot(
            completed_today=5,
            failed_today=1,
            blocked_count=3
        )
        assert stats.completed_today == 5
        assert stats.failed_today == 1
        assert stats.blocked_count == 3


class TestProjectInfo:
    """Tests for ProjectInfo dataclass."""

    def test_project_info_creation(self):
        """Test ProjectInfo creation."""
        project = ProjectInfo(
            name="myapp",
            path="/path/to/project",
            active_lines=3
        )
        assert project.name == "myapp"
        assert project.path == "/path/to/project"
        assert project.active_lines == 3


class TestSwitchboardState:
    """Tests for SwitchboardState dataclass."""

    def test_switchboard_state_initialization(self):
        """Test SwitchboardState default initialization."""
        state = SwitchboardState()

        assert state.workers == {}
        assert state.pipelines == {}
        assert state.projects == {}
        assert isinstance(state.stats, StatsSnapshot)
        assert state.daemon_online is False
        assert isinstance(state.events, deque)
        assert len(state.events) == 0

    def test_switchboard_state_add_worker(self):
        """Test adding worker to SwitchboardState."""
        state = SwitchboardState()

        worker = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test work",
            epic_id="epic-xyz"
        )

        updated_state = state.add_worker(worker)
        assert "mol-2hn" in updated_state.workers
        assert updated_state.workers["mol-2hn"] == worker

    def test_switchboard_state_add_worker_overwrite(self):
        """Test adding worker overwrites existing worker."""
        worker1 = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Original title",
            epic_id="epic-xyz"
        )

        worker2 = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Updated title",
            epic_id="epic-xyz"
        )

        state = SwitchboardState()
        state = state.add_worker(worker1)
        state = state.add_worker(worker2)

        assert state.workers["mol-2hn"].title == "Updated title"

    def test_switchboard_state_add_worker_none_bead_id(self):
        """Test adding worker with None bead_id raises error."""
        state = SwitchboardState()

        worker = WorkerState(
            bead_id=None,
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test work",
            epic_id="epic-xyz"
        )

        with pytest.raises((ValueError, TypeError)):
            state.add_worker(worker)

    def test_switchboard_state_remove_worker(self):
        """Test removing worker from SwitchboardState."""
        worker = WorkerState(
            bead_id="mol-2hn",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test work",
            epic_id="epic-xyz"
        )

        state = SwitchboardState()
        state = state.add_worker(worker)
        assert "mol-2hn" in state.workers

        state = state.remove_worker("mol-2hn")
        assert "mol-2hn" not in state.workers

    def test_switchboard_state_remove_nonexistent_worker(self):
        """Test removing non-existent worker does not error."""
        state = SwitchboardState()

        # Should not raise error
        updated_state = state.remove_worker("nonexistent")
        assert updated_state.workers == {}

    def test_switchboard_state_remove_worker_empty_dict(self):
        """Test removing worker from empty workers dict."""
        state = SwitchboardState()
        assert state.workers == {}

        # Should not raise error
        updated_state = state.remove_worker("mol-2hn")
        assert updated_state.workers == {}

    def test_switchboard_state_update_stats(self):
        """Test updating stats in SwitchboardState."""
        state = SwitchboardState()

        new_stats = StatsSnapshot(
            completed_today=10,
            failed_today=2,
            blocked_count=1
        )

        updated_state = state.update_stats(new_stats)
        assert updated_state.stats.completed_today == 10
        assert updated_state.stats.failed_today == 2
        assert updated_state.stats.blocked_count == 1

    def test_switchboard_state_update_stats_with_none(self):
        """Test updating stats with None value."""
        state = SwitchboardState()

        with pytest.raises((ValueError, TypeError)):
            state.update_stats(None)

    def test_switchboard_state_add_log_event(self):
        """Test adding log event to SwitchboardState."""
        state = SwitchboardState()

        event = LogEvent(
            timestamp="2026-05-20 14:23:01",
            level="INFO",
            message="Test event",
            parsed_event_type="claimed"
        )

        updated_state = state.add_log_event(event)
        assert len(updated_state.events) == 1
        assert updated_state.events[0] == event

    def test_switchboard_state_add_log_event_max_size(self):
        """Test log events deque maintains max 1000 entries."""
        state = SwitchboardState()

        # Add 1001 events
        for i in range(1001):
            event = LogEvent(
                timestamp=f"2026-05-20 14:23:{i:02d}",
                level="INFO",
                message=f"Event {i}",
                parsed_event_type=None
            )
            state = state.add_log_event(event)

        # Should keep only last 1000 events
        assert len(state.events) == 1000
        assert "Event 1000" in state.events[-1].message
        assert "Event 0" not in [e.message for e in state.events]

    def test_switchboard_state_reconcile_workers(self):
        """Test reconciling workers with current state."""
        existing_worker = WorkerState(
            bead_id="mol-1",
            agent="development",
            repo="nexus",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Existing work",
            epic_id="epic-1"
        )

        state = SwitchboardState()
        state = state.add_worker(existing_worker)

        # Current workers include existing + new, but not removed
        current_workers = [
            {
                "bead_id": "mol-1",
                "agent": "development",
                "repo": "nexus",
                "tool": None,
                "pid": 12345,
                "started_at": "2026-05-20T14:23:01",
                "title": "Updated existing work",  # Updated title
                "epic_id": "epic-1"
            },
            {
                "bead_id": "mol-2",
                "agent": "tests",
                "repo": "ui",
                "tool": "pytest",
                "pid": 54321,
                "started_at": "2026-05-20T14:25:01",
                "title": "New work",
                "epic_id": "epic-2"
            }
        ]

        updated_state = state.reconcile_workers(current_workers)

        # Should have 2 workers
        assert len(updated_state.workers) == 2

        # Existing worker updated with new data
        assert updated_state.workers["mol-1"].title == "Updated existing work"

        # New worker added
        assert "mol-2" in updated_state.workers
        assert updated_state.workers["mol-2"].agent == "tests"