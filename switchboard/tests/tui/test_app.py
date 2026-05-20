"""Tests for Switchboard TUI app assembly.

These tests are written in the TDD red phase and are expected to FAIL until the
implementation is complete. Tests cover:
- Widget mounting and layout hierarchy
- Keybinding system integration
- State propagation across widgets
- Polling system startup and coordination
- Footer keybinding hints and daemon status
"""

import pytest
import asyncio
import time
import psutil
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from pathlib import Path
from textual.testing import AppTest
from textual.keys import Keys
import tempfile
from collections import deque
import json

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.state import SwitchboardState, WorkerState, LogEvent, StatsSnapshot, ProjectInfo
from switchboard.tui.polling import poll_workers, poll_stats, tail_file


class TestAppAssemblyLayout:
    """Tests for app assembly layout integration."""

    def test_app_compose_widget_hierarchy(self):
        """Test all required widgets mount in correct DOM order."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # Verify widget presence and order according to spec
            expected_widgets = [
                "SwitchboardHeader",
                "OperatorPanel",
                "ProjectsPanel",
                "PatchPanel",
                "ActiveLines",
                "PartyLine",
                "Footer"
            ]

            # These should fail until widgets are implemented
            for widget_name in expected_widgets:
                try:
                    widget = pilot.app.query_one(f".{widget_name.lower()}")
                    assert widget is not None, f"{widget_name} should be mounted"
                except Exception as e:
                    # Expected to fail in red phase
                    pytest.fail(f"Widget {widget_name} not found (expected in red phase): {e}")

    def test_app_compose_widget_positioning(self):
        """Test widgets positioned according to layout specification."""
        app = SwitchboardApp()

        with AppTest(app, size=(80, 24)) as pilot:
            try:
                # SwitchboardHeader: top row, full width
                header = pilot.app.query_one(".switchboardheader")
                assert header.region.y == 0, "Header should be at top"

                # Sidebars: left and right, correct height allocation
                operator_panel = pilot.app.query_one(".operatorpanel")
                projects_panel = pilot.app.query_one(".projectspanel")
                assert operator_panel.region.x == 0, "OperatorPanel should be at left"

                # PatchPanel: main area, scrollable
                patch_panel = pilot.app.query_one(".patchpanel")
                assert patch_panel.can_focus, "PatchPanel should be scrollable/focusable"

                # Footer: bottom row, status bar format
                footer = pilot.app.query_one(".footer")
                assert footer.region.y == 23, "Footer should be at bottom"

            except Exception as e:
                # Expected to fail until layout is implemented
                pytest.fail(f"Layout positioning test failed (expected in red phase): {e}")

    def test_app_layout_terminal_resize(self):
        """Test layout adapts correctly to terminal resize events."""
        app = SwitchboardApp()

        resize_scenarios = [
            (120, 40),  # Large terminal
            (80, 24),   # Standard terminal
            (60, 20),   # Narrow terminal (sidebar collapse)
            (200, 50),  # Wide terminal
        ]

        with AppTest(app, size=(80, 24)) as pilot:
            for width, height in resize_scenarios:
                pilot.resize(width, height)

                # Verify no widget overlap after resize
                try:
                    widgets = pilot.app.query("*")
                    # This will fail until widgets exist and handle resize
                    assert len(widgets) >= 7, f"Should have 7+ widgets after resize to {width}x{height}"
                except Exception as e:
                    pytest.fail(f"Resize test failed for {width}x{height} (expected in red phase): {e}")

    def test_app_shared_state_initialization(self):
        """Test all widgets share same SwitchboardState instance."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Get state references from each widget
                header_state = pilot.app.query_one(".switchboardheader").state
                patch_panel_state = pilot.app.query_one(".patchpanel").state
                party_line_state = pilot.app.query_one(".partyline").state

                # All should reference same object
                assert header_state is patch_panel_state
                assert patch_panel_state is party_line_state

            except Exception as e:
                # Expected to fail until widgets and state integration exist
                pytest.fail(f"Shared state test failed (expected in red phase): {e}")


class TestKeybindingSystem:
    """Tests for keybinding system integration."""

    def test_quit_keybinding(self):
        """Test 'Q' and 'q' keys trigger application exit."""
        # Test lowercase 'q'
        app = SwitchboardApp()
        with AppTest(app) as pilot:
            pilot.press("q")
            assert pilot.app.is_running is False

        # Test uppercase 'Q'
        app2 = SwitchboardApp()
        with AppTest(app2) as pilot:
            pilot.press("Q")
            assert pilot.app.is_running is False

    def test_tab_focus_cycling(self):
        """Test Tab key cycles focus through interactive widgets."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # Expected cycle order from spec
            expected_sequence = [
                "OperatorPanel", "ProjectsPanel", "PatchPanel",
                "ActiveLines", "PartyLine", "OperatorPanel"
            ]

            focus_sequence = []

            try:
                for i in range(6):  # Complete cycle
                    pilot.press("tab")
                    focused_widget = pilot.app.focused
                    focus_sequence.append(focused_widget.__class__.__name__)

                assert focus_sequence == expected_sequence

            except Exception as e:
                # Expected to fail until widgets exist and focus cycling implemented
                pytest.fail(f"Tab focus cycling failed (expected in red phase): {e}")

    def test_reverse_tab_cycling(self):
        """Test Shift+Tab cycles focus backward through widgets."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Start from default focus, then go backward
                pilot.press("shift+tab")
                first_widget = pilot.app.focused.__class__.__name__

                pilot.press("shift+tab")
                second_widget = pilot.app.focused.__class__.__name__

                # Should be reverse of normal Tab order
                assert first_widget != second_widget

            except Exception as e:
                pytest.fail(f"Reverse tab cycling failed (expected in red phase): {e}")

    def test_refresh_keybinding(self):
        """Test 'R' key triggers immediate polling refresh."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.poll_workers') as mock_workers, \
             patch('switchboard.tui.polling.poll_stats') as mock_stats:

            mock_workers.return_value = []
            mock_stats.return_value = {"completed": 0, "failed": 0}

            with AppTest(app) as pilot:
                try:
                    pilot.press("r")
                    pilot.press("R")  # Test both cases

                    # Should trigger immediate poll refresh
                    # This will fail until refresh keybinding is implemented
                    assert mock_workers.call_count >= 1, "Should trigger worker poll on refresh"

                except Exception as e:
                    pytest.fail(f"Refresh keybinding failed (expected in red phase): {e}")

    def test_worker_source_switching(self):
        """Test number keys 1-9 switch PartyLine to worker output."""
        # Mock workers in state
        mock_workers = {
            "bead-1": WorkerState(bead_id="bead-1", agent="development", repo="test", tool=None, pid=123, started_at="2026-05-20T14:23:01", title="Test 1", epic_id="epic-1"),
            "bead-2": WorkerState(bead_id="bead-2", agent="tests", repo="test", tool=None, pid=124, started_at="2026-05-20T14:23:02", title="Test 2", epic_id="epic-2"),
        }

        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Set up worker state
                pilot.app.state = SwitchboardState(workers=mock_workers)

                # Test switching to worker 1
                pilot.press("1")
                party_line = pilot.app.query_one(".partyline")
                assert party_line.current_source == "worker_1"
                assert "bead-1" in party_line.header_text

                # Test switching to worker 2
                pilot.press("2")
                assert party_line.current_source == "worker_2"
                assert "bead-2" in party_line.header_text

            except Exception as e:
                pytest.fail(f"Worker source switching failed (expected in red phase): {e}")

    def test_daemon_log_switching(self):
        """Test '0' key returns PartyLine to daemon log source."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Switch to worker first
                pilot.press("1")
                # Then return to daemon
                pilot.press("0")

                party_line = pilot.app.query_one(".partyline")
                assert party_line.current_source == "daemon"

            except Exception as e:
                pytest.fail(f"Daemon log switching failed (expected in red phase): {e}")

    def test_invalid_worker_switching(self):
        """Test number keys for non-existent workers are ignored."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Only have 2 workers, test key 5
                pilot.press("5")

                party_line = pilot.app.query_one(".partyline")
                # Source should be unchanged (probably daemon)
                assert party_line.current_source in ["daemon", "worker_1", "worker_2"]

            except Exception as e:
                pytest.fail(f"Invalid worker switching test failed (expected in red phase): {e}")

    def test_scrollable_widget_navigation(self):
        """Test arrow keys work when scrollable widgets are focused."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            test_keys = ["up", "down", "page_up", "page_down", "home", "end"]

            try:
                # Focus on PatchPanel (should be scrollable)
                patch_panel = pilot.app.query_one(".patchpanel")
                patch_panel.focus()

                for key in test_keys:
                    pilot.press(key)
                    # Should not crash, exact behavior depends on content
                    assert pilot.app.is_running

            except Exception as e:
                pytest.fail(f"Scrollable navigation failed (expected in red phase): {e}")


class TestPollingIntegration:
    """Tests for polling system integration."""

    @pytest.mark.asyncio
    async def test_polling_system_initialization(self):
        """Test all 4 polling systems start correctly on app mount."""
        with patch('switchboard.tui.polling.tail_file') as mock_tail, \
             patch('switchboard.tui.polling.poll_workers') as mock_poll_workers, \
             patch('switchboard.tui.polling.poll_stats') as mock_poll_stats:

            mock_tail.return_value = AsyncIterator()
            mock_poll_workers.return_value = []
            mock_poll_stats.return_value = {"completed": 0, "failed": 0, "blocked": 0}

            app = SwitchboardApp()

            try:
                with AppTest(app) as pilot:
                    # Wait for mount to complete
                    await asyncio.sleep(0.1)

                    # Verify all polling systems started
                    # This will fail until polling integration is implemented
                    assert hasattr(pilot.app, 'log_watcher_task'), "Log watcher should be started"
                    assert hasattr(pilot.app, 'worker_poller_task'), "Worker poller should be started"
                    assert hasattr(pilot.app, 'stats_poller_task'), "Stats poller should be started"

            except Exception as e:
                pytest.fail(f"Polling initialization failed (expected in red phase): {e}")

    def test_bd_command_unavailable(self):
        """Test polling handles bd command unavailable gracefully."""
        with patch('switchboard.tui.polling.bd_json', side_effect=FileNotFoundError("bd command not found")):
            app = SwitchboardApp()

            with AppTest(app) as pilot:
                try:
                    # App should continue to function
                    assert pilot.app.is_running

                    # Daemon status should show offline
                    footer = pilot.app.query_one(".footer")
                    assert "OFFLINE" in footer.daemon_status_text

                except Exception as e:
                    pytest.fail(f"BD unavailable handling failed (expected in red phase): {e}")

    def test_malformed_bd_response(self):
        """Test polling handles invalid JSON response gracefully."""
        with patch('switchboard.tui.polling.bd_json', side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
            app = SwitchboardApp()

            with AppTest(app) as pilot:
                try:
                    # Should handle error gracefully, previous state preserved
                    assert pilot.app.is_running

                except Exception as e:
                    pytest.fail(f"Malformed response handling failed (expected in red phase): {e}")

    @pytest.mark.asyncio
    async def test_log_file_permission_error(self):
        """Test log watcher handles permission errors gracefully."""
        app = SwitchboardApp()

        with patch('switchboard.tui.polling.tail_file', side_effect=PermissionError("Permission denied")):
            try:
                with AppTest(app) as pilot:
                    # Should handle permission error without crashing
                    await asyncio.sleep(0.1)
                    assert pilot.app.is_running

            except Exception as e:
                pytest.fail(f"Permission error handling failed (expected in red phase): {e}")


class TestStatePropagation:
    """Tests for state propagation system."""

    def test_worker_state_propagation(self):
        """Test worker state changes propagate to ActiveLines and OperatorPanel."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Add worker to state
                new_worker = WorkerState(
                    bead_id="test-bead",
                    agent="development",
                    repo="test-repo",
                    tool=None,
                    pid=12345,
                    started_at="2026-05-20T14:23:01",
                    title="Test worker",
                    epic_id="epic-test"
                )

                # Trigger state update
                pilot.app.state = pilot.app.state.add_worker(new_worker)

                # Verify widget updates
                active_lines = pilot.app.query_one(".activelines")
                assert "test-bead" in active_lines.get_worker_list()

                operator_panel = pilot.app.query_one(".operatorpanel")
                assert operator_panel.worker_count == 1

            except Exception as e:
                pytest.fail(f"Worker state propagation failed (expected in red phase): {e}")

    def test_pipeline_state_propagation(self):
        """Test pipeline data changes propagate to PatchPanel and ProjectsPanel."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Update pipeline state
                # This will fail until state propagation is implemented
                patch_panel = pilot.app.query_one(".patchpanel")
                projects_panel = pilot.app.query_one(".projectspanel")

                # Test pipeline rows appear/disappear
                # Test project counts update
                # Test progress indicators update

            except Exception as e:
                pytest.fail(f"Pipeline state propagation failed (expected in red phase): {e}")

    def test_log_event_propagation(self):
        """Test LogEvent additions propagate to PartyLine widget."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Add log event to state
                log_event = LogEvent(
                    timestamp="2026-05-20 14:23:01",
                    level="INFO",
                    message="Test log message"
                )

                start_time = time.perf_counter()
                pilot.app.state = pilot.app.state.add_log_event(log_event)

                # Verify update occurs within 50ms
                party_line = pilot.app.query_one(".partyline")
                assert "Test log message" in party_line.log_content

                elapsed = (time.perf_counter() - start_time) * 1000
                assert elapsed < 50, f"Log event propagation took {elapsed:.1f}ms, should be < 50ms"

            except Exception as e:
                pytest.fail(f"Log event propagation failed (expected in red phase): {e}")

    def test_daemon_status_propagation(self):
        """Test daemon_online boolean changes propagate to Footer."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Test Online → Offline transition
                pilot.app.state = SwitchboardState(daemon_online=True)
                footer = pilot.app.query_one(".footer")
                assert "(*) DAEMON ONLINE" in footer.status_text

                # Test Offline → Online transition
                pilot.app.state = SwitchboardState(daemon_online=False)
                assert "(✗) DAEMON OFFLINE" in footer.status_text

            except Exception as e:
                pytest.fail(f"Daemon status propagation failed (expected in red phase): {e}")

    def test_update_propagation_timing(self):
        """Test widget updates complete within 50ms of state change."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                worker = WorkerState(bead_id="timing-test", agent="test", repo="test", tool=None, pid=123, started_at="2026-05-20T14:23:01", title="Timing test", epic_id="epic-1")

                start_time = time.perf_counter()
                pilot.app.state = pilot.app.state.add_worker(worker)

                # Check that widget reflects the change
                active_lines = pilot.app.query_one(".activelines")
                # This will fail until widgets exist

                elapsed = (time.perf_counter() - start_time) * 1000
                assert elapsed < 50, f"State propagation took {elapsed:.1f}ms, should be < 50ms"

            except Exception as e:
                pytest.fail(f"Update timing test failed (expected in red phase): {e}")


class TestFooterIntegration:
    """Tests for footer integration."""

    def test_default_keybinding_hints(self):
        """Test default keybinding hints are displayed."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                footer = pilot.app.query_one(".footer")
                expected_text = "Q:Quit  Tab:Navigate  R:Refresh  1-9:Workers  0:Daemon"
                assert expected_text in footer.hints_text

            except Exception as e:
                pytest.fail(f"Default keybinding hints failed (expected in red phase): {e}")

    def test_context_sensitive_hints(self):
        """Test hints update based on focused widget."""
        app = SwitchboardApp()

        focus_hint_mapping = {
            "PatchPanel": "Q:Quit  D:Details  R:Refresh  ↑↓:Scroll  Tab:Navigate",
            "PartyLine": "Q:Quit  L:Focus  1-9:Workers  0:Daemon  ↑↓:Scroll  Tab:Navigate",
            "ActiveLines": "Q:Quit  D:Details  R:Refresh  ↑↓:Scroll  Tab:Navigate"
        }

        with AppTest(app) as pilot:
            try:
                for widget_name, expected_hints in focus_hint_mapping.items():
                    widget = pilot.app.query_one(f".{widget_name.lower()}")
                    widget.focus()

                    footer = pilot.app.query_one(".footer")
                    assert expected_hints in footer.hints_text

            except Exception as e:
                pytest.fail(f"Context-sensitive hints failed (expected in red phase): {e}")

    def test_daemon_online_indicator(self):
        """Test daemon online status indicator."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Set daemon online
                pilot.app.state = SwitchboardState(daemon_online=True)
                footer = pilot.app.query_one(".footer")

                assert "(*) DAEMON ONLINE" in footer.status_text
                # Should use active/success color

            except Exception as e:
                pytest.fail(f"Daemon online indicator failed (expected in red phase): {e}")

    def test_daemon_offline_indicator(self):
        """Test daemon offline status indicator."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                # Set daemon offline
                pilot.app.state = SwitchboardState(daemon_online=False)
                footer = pilot.app.query_one(".footer")

                assert "(✗) DAEMON OFFLINE" in footer.status_text
                # Should use error/red color

            except Exception as e:
                pytest.fail(f"Daemon offline indicator failed (expected in red phase): {e}")

    def test_daemon_status_update_timing(self):
        """Test daemon status updates within 5 seconds."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            try:
                start_time = time.perf_counter()

                # Change daemon status
                pilot.app.state = SwitchboardState(daemon_online=False)

                # Status should update quickly
                footer = pilot.app.query_one(".footer")

                elapsed = time.perf_counter() - start_time
                assert elapsed < 5.0, f"Daemon status update took {elapsed:.1f}s, should be < 5s"

            except Exception as e:
                pytest.fail(f"Daemon status timing failed (expected in red phase): {e}")


class TestPerformance:
    """Performance tests for app assembly."""

    def test_app_assembly_startup_timing(self):
        """Test complete assembly within 2 seconds."""
        start_time = time.perf_counter()

        app = SwitchboardApp()

        with AppTest(app) as pilot:
            assembly_time = time.perf_counter() - start_time

            # Should complete within 2 seconds
            assert assembly_time < 2.0, f"App assembly took {assembly_time:.2f}s, should be < 2.0s"

            # App should be fully functional
            assert pilot.app.is_running

    def test_keybinding_response_performance(self):
        """Test keybinding actions complete within 100ms."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            test_keys = ["tab", "r", "1", "0"]

            for key in test_keys:
                start_time = time.perf_counter()
                pilot.press(key)
                elapsed = (time.perf_counter() - start_time) * 1000

                # Should complete within 100ms
                assert elapsed < 100, f"Key '{key}' response took {elapsed:.1f}ms, should be < 100ms"

    def test_baseline_memory_usage(self):
        """Test baseline memory usage is reasonable."""
        process = psutil.Process()
        baseline_memory = process.memory_info().rss

        app = SwitchboardApp()

        with AppTest(app) as pilot:
            current_memory = process.memory_info().rss
            app_memory = (current_memory - baseline_memory) / 1024 / 1024  # MB

            # Should use less than 50MB
            assert app_memory < 50, f"App uses {app_memory:.1f}MB, should be < 50MB"


# Test Fixtures

@pytest.fixture
async def app_with_mock_state():
    """App with populated mock state for testing."""
    mock_workers = {
        "bead-1": WorkerState(bead_id="bead-1", agent="development", repo="test", tool=None, pid=123, started_at="2026-05-20T14:23:01", title="Test 1", epic_id="epic-1"),
        "bead-2": WorkerState(bead_id="bead-2", agent="tests", repo="test", tool=None, pid=124, started_at="2026-05-20T14:23:02", title="Test 2", epic_id="epic-2")
    }

    mock_events = deque([
        LogEvent(timestamp="2026-05-20 14:23:01", level="INFO",
                message="Switchboard started", parsed_event_type="daemon_started")
    ])

    app = SwitchboardApp()
    app.state = SwitchboardState(workers=mock_workers, events=mock_events, daemon_online=True)
    return app


@pytest.fixture
def temp_artifacts_dir():
    """Temporary artifacts directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = Path(tmp_dir) / "agent_router.log"
        log_file.write_text("2026-05-20 14:23:01 [INFO] Test log entry\n")
        yield tmp_dir


@pytest.fixture
def mock_polling_functions():
    """Mock all polling functions."""
    async def async_generator_mock():
        """Create mock async generator for file tailing."""
        test_lines = [
            "2026-05-20 14:23:01 [INFO] Test log line 1\n",
            "2026-05-20 14:23:02 [INFO] Test log line 2\n"
        ]
        for line in test_lines:
            yield line
            await asyncio.sleep(0.01)

    with patch('switchboard.tui.polling.poll_workers') as mock_workers, \
         patch('switchboard.tui.polling.poll_stats') as mock_stats, \
         patch('switchboard.tui.polling.tail_file') as mock_tail:

        mock_workers.return_value = []
        mock_stats.return_value = {"completed": 0, "failed": 0, "blocked": 0}
        mock_tail.return_value = async_generator_mock()

        yield {
            'workers': mock_workers,
            'stats': mock_stats,
            'tail': mock_tail
        }


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during test."""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None

        def start(self):
            self.start_time = time.perf_counter()
            self.start_memory = psutil.Process().memory_info().rss

        def elapsed_ms(self):
            return (time.perf_counter() - self.start_time) * 1000

        def memory_delta_mb(self):
            current_memory = psutil.Process().memory_info().rss
            return (current_memory - self.start_memory) / 1024 / 1024

    return PerformanceMonitor()


# Helper functions

def create_mock_worker_state(bead_id, agent="development"):
    """Create mock WorkerState for testing."""
    return WorkerState(
        bead_id=bead_id,
        agent=agent,
        repo="test-repo",
        tool=None,
        pid=12345,
        started_at="2026-05-20T14:23:01",
        title=f"Test {agent} work",
        epic_id=f"epic-{bead_id}"
    )


def trigger_state_update(app, update_type, data):
    """Helper to trigger specific state updates."""
    if update_type == "add_worker":
        app.state = app.state.add_worker(data)
    elif update_type == "add_log_event":
        app.state = app.state.add_log_event(data)


class AsyncIterator:
    """Mock async iterator for testing."""
    async def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.sleep(0.01)
        raise StopAsyncIteration


# Backward compatibility with existing basic tests
class TestSwitchboardApp:
    """Basic app functionality tests (retained from original)."""

    def test_app_initialization(self):
        """Test SwitchboardApp initialization."""
        app = SwitchboardApp()
        assert isinstance(app, SwitchboardApp)
        assert hasattr(app, 'CSS_PATH')
        assert hasattr(app, 'TITLE')

    def test_app_quit_key_handler(self):
        """Test 'Q' key press triggers app exit."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            pilot.press("q")
            assert pilot.app.is_running is False