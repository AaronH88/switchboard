"""Tests for Switchboard TUI thematic messaging system and edge case handling."""

import pytest
import asyncio
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from textual.testing import AppTest
from collections import deque

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.state import SwitchboardState, WorkerState, LogEvent, StatsSnapshot

# These imports may fail until Interface agent creates the screen modules
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


def create_epic_completion_event():
    """Create mock epic completion event."""
    return LogEvent(
        timestamp="2026-05-20 14:23:01",
        level="INFO",
        message="epic completed: epic-test-system",
        parsed_event_type="epic_completed"
    )


async def simulate_file_append(file_path, content):
    """Simulate appending content to a file during test."""
    with open(file_path, "a") as f:
        f.write(content)
    # Give file watchers time to detect change
    await asyncio.sleep(0.1)


# =============================================================================
# Thematic Messaging Tests
# =============================================================================

class TestThematicMessages:
    """Tests for thematic messaging system."""

    @pytest.mark.asyncio
    async def test_startup_message_display(self):
        """Test startup message appears briefly on app initialization."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            # Mock async iterator for log tailing
            async def mock_log_iter():
                yield "2026-05-20 14:23:01 [INFO] Test log"
                return
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                # Should show startup message immediately
                startup_overlay = pilot.app.query_one(".startup-overlay")
                assert "SWITCHBOARD ONLINE · PATCHING IN..." in startup_overlay.renderable

                # Wait for startup sequence
                await asyncio.sleep(3.0)

                # Startup message should be gone
                overlays = pilot.app.query(".startup-overlay")
                assert len(overlays) == 0

    @pytest.mark.asyncio
    async def test_startup_message_timing(self):
        """Test startup message displays for 2-3 seconds."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                yield "2026-05-20 14:23:01 [INFO] Test log"
                return
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                start_time = time.perf_counter()

                # Wait for message to appear
                startup_overlay = pilot.app.query_one(".startup-overlay")
                assert startup_overlay is not None

                # Wait for message to disappear
                while pilot.app.query(".startup-overlay"):
                    await asyncio.sleep(0.1)
                    if time.perf_counter() - start_time > 5:
                        break

                elapsed = time.perf_counter() - start_time
                assert 2.0 <= elapsed <= 4.0, f"Startup message duration {elapsed:.1f}s should be 2-3s"

    @pytest.mark.asyncio
    async def test_no_dial_tone_message(self):
        """Test 'NO DIAL TONE' appears when daemon is offline."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                return
                yield  # Make it a generator
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                # Set daemon offline
                pilot.app.state = SwitchboardState(daemon_online=False)

                header = pilot.app.query_one(".switchboardheader")
                assert "NO DIAL TONE" in header.get_daemon_status()

                # Verify warning styling
                assert "warning" in header.get_daemon_status_classes()

    @pytest.mark.asyncio
    async def test_daemon_status_transition(self):
        """Test header status updates when daemon state changes."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                return
                yield
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                header = pilot.app.query_one(".switchboardheader")

                # Start online
                pilot.app.state = SwitchboardState(daemon_online=True)
                assert "ONLINE" in header.get_daemon_status()

                # Transition to offline
                pilot.app.state = SwitchboardState(daemon_online=False)
                assert "NO DIAL TONE" in header.get_daemon_status()

                # Return to online
                pilot.app.state = SwitchboardState(daemon_online=True)
                assert "ONLINE" in header.get_daemon_status()

    @pytest.mark.asyncio
    async def test_all_quiet_message(self):
        """Test 'ALL QUIET ON THE BOARD' appears when no activity."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                return
                yield
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                # Set completely empty state
                pilot.app.state = SwitchboardState(
                    workers={},
                    pipelines={},
                    daemon_online=True
                )

                patch_panel = pilot.app.query_one(".patchpanel")
                assert "ALL QUIET ON THE BOARD" in patch_panel.get_empty_state_message()

    @pytest.mark.asyncio
    async def test_all_quiet_conditions(self):
        """Test 'ALL QUIET' message only appears when truly idle."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail, \
             patch('switchboard.tui.polling.get_ready_beads') as mock_ready:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                return
                yield
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                patch_panel = pilot.app.query_one(".patchpanel")
                mock_worker = create_mock_worker("w1")

                test_cases = [
                    # (workers, ready_beads, should_show_quiet)
                    ({}, [], True),                    # Completely empty
                    ({"w1": mock_worker}, [], False),  # Has workers
                    ({}, ["bead1"], False),            # Has ready beads
                    ({"w1": mock_worker}, ["bead1"], False)  # Has both
                ]

                for workers, ready_beads, should_show in test_cases:
                    mock_ready.return_value = ready_beads
                    pilot.app.state = SwitchboardState(
                        workers=workers,
                        daemon_online=True
                    )

                    quiet_message_shown = "ALL QUIET ON THE BOARD" in patch_panel.get_content()
                    assert quiet_message_shown == should_show

    @pytest.mark.asyncio
    async def test_all_lines_busy_message(self):
        """Test 'ALL LINES BUSY' appears when all worker slots occupied."""
        # Create max workers (assume 9 max)
        max_workers = {f"worker-{i}": create_mock_worker(f"bead-{i}") for i in range(9)}

        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail, \
             patch('switchboard.tui.polling.get_ready_beads') as mock_ready:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                return
                yield
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                # Mock ready beads waiting
                mock_ready.return_value = ["bead-waiting-1", "bead-waiting-2", "bead-waiting-3"]

                pilot.app.state = SwitchboardState(workers=max_workers)

                operator_panel = pilot.app.query_one(".operatorpanel")
                capacity_message = operator_panel.get_capacity_message()

                assert "ALL LINES BUSY · 3 CALLS HOLDING" in capacity_message

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_epic_completion_flash(self):
        """Test brief screen flash animation on epic completion."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                return
                yield
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                # Mock epic completion event
                completion_event = LogEvent(
                    timestamp="2026-05-20 14:23:01",
                    level="INFO",
                    message="epic completed: epic-auth-system",
                    parsed_event_type="epic_completed"
                )

                # Trigger epic completion
                pilot.app.state = pilot.app.state.add_log_event(completion_event)

                # Should trigger flash effect
                flash_overlay = pilot.app.query_one(".completion-flash")
                assert flash_overlay is not None
                assert "flash-animation" in flash_overlay.classes

                # Wait for flash to complete
                await asyncio.sleep(0.5)

                # Flash should be gone
                flash_overlays = pilot.app.query(".completion-flash")
                assert len(flash_overlays) == 0

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_flash_timing(self):
        """Test epic completion flash duration is 200-300ms."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                return
                yield
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                start_time = time.perf_counter()

                # Trigger flash
                completion_event = create_epic_completion_event()
                pilot.app.state = pilot.app.state.add_log_event(completion_event)

                # Wait for flash to complete
                while pilot.app.query(".completion-flash"):
                    await asyncio.sleep(0.01)

                flash_duration = (time.perf_counter() - start_time) * 1000
                assert 200 <= flash_duration <= 400, f"Flash duration {flash_duration:.1f}ms should be 200-300ms"


# =============================================================================
# Edge Case Handling Tests
# =============================================================================

class TestEdgeCaseHandling:
    """Tests for edge case handling in screens and thematic features."""

    @pytest.mark.asyncio
    async def test_app_start_no_log_file(self):
        """Test app starts gracefully without agent_router.log file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Empty artifacts directory
            artifacts_dir = Path(tmp_dir) / "artifacts"
            artifacts_dir.mkdir()
            # No agent_router.log file

            app = SwitchboardApp(artifacts_dir=str(artifacts_dir))

            with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
                 patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
                 patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

                mock_workers.return_value = []
                mock_stats.return_value = {"completed": 0, "failed": 0}

                async def mock_log_iter():
                    return
                    yield
                mock_tail.return_value = mock_log_iter()

                async with app.run_test() as pilot:
                    party_line = pilot.app.query_one(".partyline")
                    content = party_line.get_content()

                    assert "(waiting for daemon)" in content
                    assert "error" not in content.lower()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_detail_screen_missing_log(self):
        """Test DetailScreen gracefully handles missing log file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # No log file for this bead
            detail_screen = DetailScreen(bead_id="nonexistent-bead", artifacts_dir=tmp_dir)

            async with detail_screen.run_test() as pilot:
                log_panel = pilot.app.query_one(".live-log-panel")
                assert "No output available" in log_panel.get_content()

                # Should not crash
                assert pilot.app.is_running

    @pytest.mark.asyncio
    async def test_log_file_creation_during_runtime(self):
        """Test log watcher begins tailing when log file is created."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifacts_dir = Path(tmp_dir) / "artifacts"
            artifacts_dir.mkdir()

            app = SwitchboardApp(artifacts_dir=str(artifacts_dir))

            with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
                 patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
                 patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

                mock_workers.return_value = []
                mock_stats.return_value = {"completed": 0, "failed": 0}

                async def mock_log_iter():
                    yield "2026-05-20 14:23:01 [INFO] Daemon started"
                    return
                mock_tail.return_value = mock_log_iter()

                async with app.run_test() as pilot:
                    # Initially no log file
                    party_line = pilot.app.query_one(".partyline")
                    assert "(waiting for daemon)" in party_line.get_content()

                    # Create log file
                    log_file = artifacts_dir / "agent_router.log"
                    log_file.write_text("2026-05-20 14:23:01 [INFO] Daemon started\n")

                    # Wait for watcher to detect file
                    await asyncio.sleep(0.5)

                    # Should begin showing log content
                    assert "Daemon started" in party_line.get_content()

    @pytest.mark.asyncio
    async def test_empty_database_states(self):
        """Test all panels show appropriate empty states with no beads."""
        with patch('switchboard.tui.polling.bd_json') as mock_bd:
            mock_bd.return_value = []  # Empty database

            app = SwitchboardApp()

            with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
                 patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
                 patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

                mock_workers.return_value = []
                mock_stats.return_value = {"completed": 0, "failed": 0}

                async def mock_log_iter():
                    return
                    yield
                mock_tail.return_value = mock_log_iter()

                async with app.run_test() as pilot:
                    # Trigger polling
                    await asyncio.sleep(0.1)  # Allow polling to run

                    # Check all panels show empty states
                    patch_panel = pilot.app.query_one(".patchpanel")
                    assert "ALL QUIET ON THE BOARD" in patch_panel.get_content()

                    active_lines = pilot.app.query_one(".activelines")
                    assert "No active workers" in active_lines.get_content()

                    projects_panel = pilot.app.query_one(".projectspanel")
                    assert "No projects available" in projects_panel.get_content()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_project_screen_empty_project(self):
        """Test ProjectScreen handles project with no epics gracefully."""
        project_screen = ProjectScreen(project_name="empty-project")

        async with project_screen.run_test() as pilot:
            # Set empty state
            pilot.app.state = SwitchboardState(pipelines={})

            # Each group should show empty state
            active_group = pilot.app.query_one(".active-epics-group")
            assert "No active epics" in active_group.get_empty_state_message()

            completed_group = pilot.app.query_one(".completed-epics-group")
            assert "No completed epics" in completed_group.get_empty_state_message()

            queued_group = pilot.app.query_one(".queued-epics-group")
            assert "No queued epics" in queued_group.get_empty_state_message()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_daemon_disconnect_during_screen_use(self):
        """Test screens continue functioning when daemon stops."""
        mock_bead_data = {
            "bead_id": "bead-123",
            "title": "Test Feature",
            "agent": "development",
            "status": "in_progress"
        }

        with patch('switchboard.tui.screens.detail.get_bead_info') as mock_get_bead:
            mock_get_bead.return_value = mock_bead_data

            detail_screen = DetailScreen(bead_id="bead-123")

            async with detail_screen.run_test() as pilot:
                # Screen should load normally
                assert "bead-123" in pilot.app.query_one(".bead-header").renderable

                # Simulate daemon disconnect
                pilot.app.state = SwitchboardState(daemon_online=False)

                # Screen should continue to function with cached data
                assert pilot.app.is_running
                assert "bead-123" in pilot.app.query_one(".bead-header").renderable

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_detail_screen_terminal_resize(self):
        """Test DetailScreen layout adapts to terminal resize."""
        detail_screen = DetailScreen(bead_id="bead-123")

        async with detail_screen.run_test(size=(80, 24)) as pilot:
            # Get initial layout
            info_panel = pilot.app.query_one(".bead-info-panel")
            log_panel = pilot.app.query_one(".live-log-panel")

            initial_info_size = (info_panel.size.width, info_panel.size.height)

            # Resize terminal
            pilot.resize(120, 40)

            # Layout should adapt
            new_info_size = (info_panel.size.width, info_panel.size.height)
            assert new_info_size != initial_info_size

            # Content should still be visible
            assert "bead-123" in info_panel.get_content()

            # Focus should be preserved
            focused_before = pilot.app.focused
            assert pilot.app.focused is focused_before

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_minimum_terminal_size_support(self):
        """Test all screens remain usable at minimum terminal size."""
        screens_to_test = [
            DetailScreen(bead_id="test-bead"),
            LogFocusScreen(),
            ProjectScreen(project_name="test-project")
        ]

        for screen in screens_to_test:
            async with screen.run_test(size=(80, 24)) as pilot:
                # Should be usable at minimum size
                assert pilot.app.is_running

                # Key navigation should work
                await pilot.press("tab")
                assert pilot.app.is_running

                # Should be able to exit
                await pilot.press("escape")
                # Note: This would normally exit to main screen


# =============================================================================
# Performance and Stress Tests
# =============================================================================

class TestPerformance:
    """Tests for performance requirements."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_fullscreen_rendering_performance(self):
        """Test fullscreen rendering performance within limits."""
        # Create large dataset
        mock_events = deque()
        for i in range(1000):
            mock_events.append(LogEvent(
                timestamp=f"2026-05-20 14:23:{i:02d}",
                level="INFO",
                message=f"Performance test message {i}",
                parsed_event_type=None
            ))

        log_screen = LogFocusScreen()

        async with log_screen.run_test() as pilot:
            start_time = time.perf_counter()

            # Set state and trigger render
            pilot.app.state = SwitchboardState(events=mock_events)

            render_time = (time.perf_counter() - start_time) * 1000

            # Should render within 200ms
            assert render_time < 200, f"Render took {render_time:.1f}ms, should be < 200ms"

    @pytest.mark.asyncio
    @pytest.mark.skipif(not SCREENS_AVAILABLE, reason="Screen modules not implemented yet")
    async def test_log_auto_scroll(self):
        """Test log panels auto-scroll to show latest content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = Path(tmp_dir) / "artifacts" / "logs" / "bead-123" / "stdout.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            # Create large initial content
            initial_content = "\n".join([f"Log line {i}" for i in range(50)])
            log_file.write_text(initial_content)

            detail_screen = DetailScreen(bead_id="bead-123", artifacts_dir=tmp_dir)

            async with detail_screen.run_test() as pilot:
                log_panel = pilot.app.query_one(".live-log-panel")

                # Add new line
                with log_file.open("a") as f:
                    f.write("LATEST LINE\n")

                await asyncio.sleep(0.2)

                # Should auto-scroll to show latest
                assert log_panel.scroll_y == log_panel.max_scroll_y
                assert "LATEST LINE" in log_panel.get_visible_content()

    @pytest.mark.asyncio
    async def test_capacity_message_dynamic_count(self):
        """Test capacity message count updates dynamically."""
        # Create max workers
        max_workers = {f"worker-{i}": create_mock_worker(f"bead-{i}") for i in range(9)}

        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
             patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
             patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail, \
             patch('switchboard.tui.polling.get_ready_beads') as mock_ready:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            async def mock_log_iter():
                return
                yield
            mock_tail.return_value = mock_log_iter()

            async with app.run_test() as pilot:
                pilot.app.state = SwitchboardState(workers=max_workers)
                operator_panel = pilot.app.query_one(".operatorpanel")

                # Test different queue sizes
                for queue_size in [1, 3, 5]:
                    mock_ready.return_value = [f"bead-waiting-{i}" for i in range(queue_size)]

                    # Trigger state update
                    pilot.app.state = SwitchboardState(workers=max_workers)

                    capacity_message = operator_panel.get_capacity_message()
                    assert f"ALL LINES BUSY · {queue_size} CALLS HOLDING" in capacity_message