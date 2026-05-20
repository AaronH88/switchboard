"""Tests for Switchboard TUI secondary screens functionality."""

import pytest
import asyncio
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from textual.testing import AppTest
from collections import deque

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.state import SwitchboardState, WorkerState, StepState, PipelineState, LogEvent

# These imports will fail until Interface agent creates the screen modules
try:
    from switchboard.tui.screens.detail import DetailScreen
    from switchboard.tui.screens.log_focus import LogFocusScreen
    from switchboard.tui.screens.project import ProjectScreen
    SCREENS_AVAILABLE = True
except ImportError:
    # Expected to fail until Interface agent creates screen modules
    SCREENS_AVAILABLE = False
    DetailScreen = None
    LogFocusScreen = None
    ProjectScreen = None


# Test fixtures
@pytest.fixture
def mock_bead_data():
    """Complete mock bead data for testing."""
    return {
        "bead_id": "bead-test-123",
        "title": "Test Feature Implementation",
        "description": "Implement comprehensive test feature with full functionality",
        "agent": "development",
        "status": "in_progress",
        "labels": ["feature", "test"],
        "priority": 2,
        "created_at": "2026-05-20T10:00:00",
        "updated_at": "2026-05-20T14:23:01",
        "epic_id": "epic-test-system",
        "dependencies": {
            "blocks": ["bead-456", "bead-789"],
            "blocked_by": ["bead-012"]
        }
    }


@pytest.fixture
def mock_workers_state():
    """Mock workers state for testing."""
    return {
        "bead-1": WorkerState(
            bead_id="bead-1",
            agent="development",
            repo="test-repo",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test Development Work",
            epic_id="epic-1"
        ),
        "bead-2": WorkerState(
            bead_id="bead-2",
            agent="tests",
            repo="test-repo",
            tool=None,
            pid=12346,
            started_at="2026-05-20T14:23:02",
            title="Test Testing Work",
            epic_id="epic-2"
        )
    }


@pytest.fixture
def mock_log_events():
    """Mock log events for testing."""
    return deque([
        LogEvent(
            timestamp="2026-05-20 14:23:01",
            level="INFO",
            message="Switchboard started",
            parsed_event_type="daemon_started"
        ),
        LogEvent(
            timestamp="2026-05-20 14:23:15",
            level="INFO",
            message="claimed mol-feature-xyz (agent: development, repo: nexus)",
            parsed_event_type="claimed"
        ),
        LogEvent(
            timestamp="2026-05-20 14:23:45",
            level="INFO",
            message="completed mol-test-abc (agent: tests)",
            parsed_event_type="completed"
        )
    ])


@pytest.fixture
def temp_artifacts_with_logs():
    """Temporary artifacts directory with sample log files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        artifacts_dir = Path(tmp_dir)

        # Create main log
        (artifacts_dir / "agent_router.log").write_text(
            "2026-05-20 14:23:01 [INFO] Test daemon log entry\n"
        )

        # Create bead logs
        bead_logs_dir = artifacts_dir / "logs" / "bead-123"
        bead_logs_dir.mkdir(parents=True)
        (bead_logs_dir / "stdout.log").write_text(
            "Starting bead execution...\nProcessing task...\nCompleted successfully.\n"
        )

        yield str(artifacts_dir)


# Helper functions
def create_mock_worker(bead_id, agent="development"):
    """Create mock WorkerState for testing."""
    return WorkerState(
        bead_id=bead_id,
        agent=agent,
        repo="test-repo",
        tool=None,
        pid=12345,
        started_at="2026-05-20T14:23:01",
        title=f"Test {agent} work",
        epic_id=f"epic-{bead_id.split('-')[-1]}"
    )


def create_test_epic_list():
    """Create list of test epics for navigation testing."""
    return {
        "epic-1": PipelineState(
            epic_id="epic-1",
            title="Epic 1",
            project="test-project",
            repo="test",
            steps=[]
        ),
        "epic-2": PipelineState(
            epic_id="epic-2",
            title="Epic 2",
            project="test-project",
            repo="test",
            steps=[]
        ),
        "epic-3": PipelineState(
            epic_id="epic-3",
            title="Epic 3",
            project="test-project",
            repo="test",
            steps=[]
        )
    }


# Skip all tests if screens aren't available yet
pytestmark = pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")


# =============================================================================
# DetailScreen Tests
# =============================================================================

class TestDetailScreen:
    """Tests for DetailScreen functionality."""

    @pytest.mark.asyncio
    async def test_detail_screen_open_from_patch_panel(self, mock_workers_state):
        """Test D key opens detail view for selected bead in PatchPanel."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # Set up state with worker
            pilot.app.state = SwitchboardState(workers=mock_workers_state)

            # Focus PatchPanel and select bead
            patch_panel = pilot.app.query_one(".patchpanel")
            patch_panel.focus()
            # This would be implemented by the patch_panel widget
            # patch_panel.select_bead("bead-1")

            # Press D key to open detail
            await pilot.press("d")

            # Verify DetailScreen opened
            assert isinstance(pilot.app.screen, DetailScreen)
            assert pilot.app.screen.bead_id == "bead-1"

    @pytest.mark.asyncio
    async def test_detail_screen_open_from_active_lines(self, mock_workers_state):
        """Test D key opens detail view for selected worker in ActiveLines."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # Set up state with worker
            pilot.app.state = SwitchboardState(workers=mock_workers_state)

            # Focus ActiveLines and select worker
            active_lines = pilot.app.query_one(".activelines")
            active_lines.focus()
            # This would be implemented by the active_lines widget
            # active_lines.select_worker("bead-1")

            # Press D key to open detail
            await pilot.press("d")

            # Verify DetailScreen opened
            assert isinstance(pilot.app.screen, DetailScreen)
            assert pilot.app.screen.bead_id == "bead-1"

    @pytest.mark.asyncio
    async def test_detail_screen_invalid_selection(self):
        """Test D key with no selection - no action taken."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # No selection state
            patch_panel = pilot.app.query_one(".patchpanel")
            patch_panel.focus()
            # Don't select any bead

            current_screen = pilot.app.screen
            await pilot.press("d")

            # Should remain on same screen
            assert pilot.app.screen is current_screen

    @pytest.mark.asyncio
    async def test_detail_screen_escape_back(self):
        """Test Escape key returns to main screen from DetailScreen."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # Open DetailScreen
            detail_screen = DetailScreen(bead_id="bead-123")
            pilot.app.push_screen(detail_screen)

            # Store main screen state
            main_screen = pilot.app.screen_stack[0]

            # Press Escape
            await pilot.press("escape")

            # Should return to main screen
            assert pilot.app.screen is main_screen

    @pytest.mark.asyncio
    async def test_bead_metadata_display(self, mock_bead_data):
        """Test DetailScreen displays all bead metadata correctly."""
        with patch('switchboard.tui.screens.detail.get_bead_info') as mock_get_bead:
            mock_get_bead.return_value = mock_bead_data

            detail_screen = DetailScreen(bead_id="bead-123")

            async with detail_screen.run_test() as pilot:
                # Verify all metadata displayed
                assert "bead-123" in pilot.app.query_one(".bead-header").renderable
                assert "Test Feature Implementation" in pilot.app.query_one(".bead-title").renderable
                assert "development" in pilot.app.query_one(".bead-agent").renderable
                assert "in_progress" in pilot.app.query_one(".bead-status").renderable
                assert "feature, test" in pilot.app.query_one(".bead-labels").renderable
                assert "epic-test-system" in pilot.app.query_one(".bead-epic").renderable

                # Verify dependencies
                deps_widget = pilot.app.query_one(".bead-dependencies")
                assert "blocks: bead-456, bead-789" in deps_widget.renderable
                assert "blocked by: bead-012" in deps_widget.renderable

    @pytest.mark.asyncio
    async def test_missing_bead_data(self):
        """Test DetailScreen with non-existent bead ID shows error state."""
        with patch('switchboard.tui.screens.detail.get_bead_info') as mock_get_bead:
            mock_get_bead.side_effect = FileNotFoundError("Bead not found")

            detail_screen = DetailScreen(bead_id="nonexistent-bead")

            async with detail_screen.run_test() as pilot:
                # Should show error state, not crash
                error_widget = pilot.app.query_one(".error-state")
                assert "Bead information unavailable" in error_widget.renderable

    @pytest.mark.asyncio
    async def test_live_log_tailing(self, temp_artifacts_with_logs):
        """Test DetailScreen tails log file in real-time."""
        detail_screen = DetailScreen(bead_id="bead-123", artifacts_dir=temp_artifacts_with_logs)

        async with detail_screen.run_test() as pilot:
            # Wait for initial content
            await asyncio.sleep(0.1)

            log_panel = pilot.app.query_one(".live-log-panel")
            assert "Starting bead execution" in log_panel.get_content()

            # Append new content
            log_file = Path(temp_artifacts_with_logs) / "logs" / "bead-123" / "stdout.log"
            with log_file.open("a") as f:
                f.write("New log line\n")

            # Wait for update
            await asyncio.sleep(0.2)

            # Should show new content
            assert "New log line" in log_panel.get_content()

    @pytest.mark.asyncio
    async def test_log_file_missing(self):
        """Test DetailScreen with non-existent log file shows message."""
        detail_screen = DetailScreen(bead_id="bead-123", artifacts_dir="/nonexistent")

        async with detail_screen.run_test() as pilot:
            log_panel = pilot.app.query_one(".live-log-panel")
            assert "No output available" in log_panel.get_content()

    @pytest.mark.asyncio
    async def test_tab_panel_switching(self):
        """Test Tab key switches focus between panels."""
        detail_screen = DetailScreen(bead_id="bead-123")

        async with detail_screen.run_test() as pilot:
            # Start focus on info panel
            info_panel = pilot.app.query_one(".bead-info-panel")
            log_panel = pilot.app.query_one(".live-log-panel")

            assert pilot.app.focused is info_panel

            # Press Tab
            await pilot.press("tab")

            # Focus should switch to log panel
            assert pilot.app.focused is log_panel

            # Press Tab again
            await pilot.press("tab")

            # Focus should return to info panel
            assert pilot.app.focused is info_panel


# =============================================================================
# LogFocusScreen Tests
# =============================================================================

class TestLogFocusScreen:
    """Tests for LogFocusScreen functionality."""

    @pytest.mark.asyncio
    async def test_log_focus_open_with_l_key(self):
        """Test L key opens LogFocusScreen in fullscreen mode."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # Press L key
            await pilot.press("l")

            # Should open LogFocusScreen
            assert isinstance(pilot.app.screen, LogFocusScreen)

            # Should be fullscreen
            log_screen = pilot.app.screen
            assert log_screen.styles.width.value == "100%"
            assert log_screen.styles.height.value == "100%"

    @pytest.mark.asyncio
    async def test_log_focus_escape_back(self):
        """Test Escape key returns from LogFocusScreen."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # Open LogFocusScreen
            log_screen = LogFocusScreen()
            pilot.app.push_screen(log_screen)

            # Store previous screen
            previous_screen = pilot.app.screen_stack[0]

            # Press Escape
            await pilot.press("escape")

            # Should return to previous screen
            assert pilot.app.screen is previous_screen

    @pytest.mark.asyncio
    async def test_log_focus_l_key_toggle(self):
        """Test L key toggles LogFocusScreen."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # Open LogFocusScreen
            await pilot.press("l")
            assert isinstance(pilot.app.screen, LogFocusScreen)

            # Press L again to toggle back
            await pilot.press("l")
            # Should return to main screen
            assert not isinstance(pilot.app.screen, LogFocusScreen)

    @pytest.mark.asyncio
    async def test_worker_source_switching_fullscreen(self, mock_workers_state):
        """Test number keys switch worker sources in fullscreen."""
        log_screen = LogFocusScreen()

        async with log_screen.run_test() as pilot:
            # Set up state with workers
            pilot.app.state = SwitchboardState(workers=mock_workers_state)

            # Test switching to worker 1
            await pilot.press("1")

            header_widget = pilot.app.query_one(".log-focus-header")
            assert "WORKER 1: epic-1 development" in header_widget.renderable

            # Test switching to worker 2
            await pilot.press("2")
            assert "WORKER 2: epic-2 tests" in header_widget.renderable

    @pytest.mark.asyncio
    async def test_daemon_log_switching_fullscreen(self):
        """Test 0 key returns to daemon log source."""
        log_screen = LogFocusScreen()

        async with log_screen.run_test() as pilot:
            # Switch to daemon log
            await pilot.press("0")

            header_widget = pilot.app.query_one(".log-focus-header")
            assert "DAEMON LOG" in header_widget.renderable

    @pytest.mark.asyncio
    async def test_fullscreen_log_capacity(self, mock_log_events):
        """Test fullscreen displays more log lines than PartyLine."""
        # Create extensive log events
        mock_events = deque()
        for i in range(200):
            mock_events.append(LogEvent(
                timestamp="2026-05-20 14:23:01",
                level="INFO",
                message=f"Test log message {i}",
                parsed_event_type=None
            ))

        log_screen = LogFocusScreen()

        async with log_screen.run_test() as pilot:
            # Set up state with many events
            pilot.app.state = SwitchboardState(events=mock_events)

            # Should display more lines than normal PartyLine
            log_content = pilot.app.query_one(".log-focus-content")
            visible_lines = log_content.get_visible_line_count()

            # Should be significantly more than PartyLine widget height
            assert visible_lines > 50  # Assuming PartyLine shows ~20 lines

    @pytest.mark.asyncio
    async def test_enhanced_header_information(self, mock_log_events):
        """Test enhanced header shows detailed source information."""
        log_screen = LogFocusScreen()

        async with log_screen.run_test() as pilot:
            # Set up log events
            pilot.app.state = SwitchboardState(events=mock_log_events)

            header = pilot.app.query_one(".log-focus-header")
            header_text = header.renderable

            # Should show line count and position
            assert "lines" in header_text
            assert "(showing last" in header_text

            # Should show time range
            assert "14:23" in header_text  # Time from mock events


# =============================================================================
# ProjectScreen Tests
# =============================================================================

class TestProjectScreen:
    """Tests for ProjectScreen functionality."""

    @pytest.mark.asyncio
    async def test_project_screen_open_from_projects_panel(self):
        """Test P key opens ProjectScreen from ProjectsPanel."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # Focus ProjectsPanel
            projects_panel = pilot.app.query_one(".projectspanel")
            projects_panel.focus()
            # This would be implemented by the projects_panel widget
            # projects_panel.select_project("automation-nexus")

            # Press P key
            await pilot.press("p")

            # Should open ProjectScreen
            assert isinstance(pilot.app.screen, ProjectScreen)
            assert pilot.app.screen.project_name == "automation-nexus"

    @pytest.mark.asyncio
    async def test_project_screen_escape_back(self):
        """Test Escape key returns from ProjectScreen to main screen."""
        app = SwitchboardApp()

        async with app.run_test() as pilot:
            # Open ProjectScreen
            project_screen = ProjectScreen(project_name="automation-nexus")
            pilot.app.push_screen(project_screen)

            # Store main screen
            main_screen = pilot.app.screen_stack[0]

            # Press Escape
            await pilot.press("escape")

            # Should return to main screen
            assert pilot.app.screen is main_screen

    @pytest.mark.asyncio
    async def test_epic_status_grouping(self):
        """Test epics are correctly grouped by status."""
        mock_pipelines = {
            "epic-active-1": PipelineState(
                epic_id="epic-active-1",
                title="Active Epic 1",
                project="automation-nexus",
                repo="nexus",
                steps=[
                    StepState(bead_id="step-1", agent="development", status="in_progress"),
                    StepState(bead_id="step-2", agent="tests", status="open")
                ]
            ),
            "epic-completed-1": PipelineState(
                epic_id="epic-completed-1",
                title="Completed Epic 1",
                project="automation-nexus",
                repo="nexus",
                steps=[
                    StepState(bead_id="step-3", agent="development", status="closed"),
                    StepState(bead_id="step-4", agent="tests", status="closed")
                ]
            ),
            "epic-queued-1": PipelineState(
                epic_id="epic-queued-1",
                title="Queued Epic 1",
                project="automation-nexus",
                repo="nexus",
                steps=[
                    StepState(bead_id="step-5", agent="development", status="blocked")
                ]
            )
        }

        project_screen = ProjectScreen(project_name="automation-nexus")

        async with project_screen.run_test() as pilot:
            pilot.app.state = SwitchboardState(pipelines=mock_pipelines)

            # Verify grouping
            active_group = pilot.app.query_one(".active-epics-group")
            completed_group = pilot.app.query_one(".completed-epics-group")
            queued_group = pilot.app.query_one(".queued-epics-group")

            assert "epic-active-1" in active_group.get_epic_list()
            assert "epic-completed-1" in completed_group.get_epic_list()
            assert "epic-queued-1" in queued_group.get_epic_list()

    @pytest.mark.asyncio
    async def test_epic_progress_display(self):
        """Test epic progress shown as 'X/Y steps'."""
        mock_pipeline = PipelineState(
            epic_id="epic-progress-test",
            title="Progress Test Epic",
            project="automation-nexus",
            repo="nexus",
            steps=[
                StepState(bead_id="step-1", agent="development", status="closed"),
                StepState(bead_id="step-2", agent="tests", status="closed"),
                StepState(bead_id="step-3", agent="review", status="in_progress"),
                StepState(bead_id="step-4", agent="verify", status="open")
            ]
        )

        project_screen = ProjectScreen(project_name="automation-nexus")

        async with project_screen.run_test() as pilot:
            pilot.app.state = SwitchboardState(pipelines={"epic-progress-test": mock_pipeline})

            epic_widget = pilot.app.query_one(".epic-progress-test")
            assert "2/4 steps" in epic_widget.renderable

    @pytest.mark.asyncio
    async def test_epic_selection_navigation(self):
        """Test Up/Down arrow keys navigate between epics."""
        project_screen = ProjectScreen(project_name="automation-nexus")

        async with project_screen.run_test() as pilot:
            # Set up test epics
            mock_pipelines = create_test_epic_list()
            pilot.app.state = SwitchboardState(pipelines=mock_pipelines)

            active_group = pilot.app.query_one(".active-epics-group")
            active_group.focus()

            # Test down arrow
            initial_selection = active_group.selected_epic
            await pilot.press("down")
            assert active_group.selected_epic != initial_selection

            # Test up arrow
            await pilot.press("up")
            assert active_group.selected_epic == initial_selection

    @pytest.mark.asyncio
    async def test_epic_detail_navigation(self):
        """Test D key opens DetailScreen for selected epic."""
        project_screen = ProjectScreen(project_name="automation-nexus")

        async with project_screen.run_test() as pilot:
            # Select an epic
            active_group = pilot.app.query_one(".active-epics-group")
            active_group.focus()
            # This would be implemented by the epic group widget
            # active_group.select_epic("epic-test")

            # Press D for details
            await pilot.press("d")

            # Should open DetailScreen for the epic
            assert isinstance(pilot.app.screen, DetailScreen)
            assert pilot.app.screen.bead_id == "epic-test"