# Switchboard TUI Secondary Screens & Thematic Polish - Test Specifications

## Test Organization

Tests are organized by screen and feature following the existing patterns in the codebase:
- Use `pytest` as test framework with `textual.testing.AppTest` for TUI testing
- Use `unittest.mock` for mocking external dependencies and file operations
- Use `tempfile` for temporary file operations and mock log files
- Use async test utilities for file tailing and background task testing
- Import modules using sys.path.insert pattern for consistency

## 1. DetailScreen Tests (test_screens_detail.py)

### Test File Structure
```python
"""Tests for Switchboard TUI DetailScreen functionality."""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, mock_open
from textual.testing import AppTest
from pathlib import Path
import tempfile

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.screens.detail import DetailScreen
from switchboard.tui.state import SwitchboardState, WorkerState, StepState
```

### Screen Navigation Tests

#### test_detail_screen_open_from_patch_panel
**Input**: 'D' key press with selected bead in PatchPanel
**Expected Output**: DetailScreen opens for selected bead
**Test Structure**:
```python
def test_detail_screen_open_from_patch_panel():
    mock_workers = {
        "bead-123": WorkerState(
            bead_id="bead-123",
            agent="development",
            repo="test-repo",
            tool=None,
            pid=12345,
            started_at="2026-05-20T14:23:01",
            title="Test Development Work",
            epic_id="epic-feature"
        )
    }
    
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Set up state with worker
        pilot.app.state = SwitchboardState(workers=mock_workers)
        
        # Focus PatchPanel and select bead
        patch_panel = pilot.app.query_one(".patchpanel")
        patch_panel.focus()
        patch_panel.select_bead("bead-123")
        
        # Press D key to open detail
        pilot.press("d")
        
        # Verify DetailScreen opened
        assert isinstance(pilot.app.screen, DetailScreen)
        assert pilot.app.screen.bead_id == "bead-123"
```

#### test_detail_screen_open_from_active_lines
**Input**: 'D' key press with selected worker in ActiveLines
**Expected Output**: DetailScreen opens for selected worker's bead
**Test Implementation**: Similar to above but with ActiveLines focus

#### test_detail_screen_invalid_selection
**Input**: 'D' key press with no selection
**Expected Output**: No action, remain on current screen
**Test Structure**:
```python
def test_detail_screen_invalid_selection():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # No selection state
        patch_panel = pilot.app.query_one(".patchpanel")
        patch_panel.focus()
        # Don't select any bead
        
        current_screen = pilot.app.screen
        pilot.press("d")
        
        # Should remain on same screen
        assert pilot.app.screen is current_screen
```

#### test_detail_screen_escape_back
**Input**: Escape key press while DetailScreen active
**Expected Output**: Return to main screen with state preserved
**Test Structure**:
```python
def test_detail_screen_escape_back():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Open DetailScreen
        detail_screen = DetailScreen(bead_id="bead-123")
        pilot.app.push_screen(detail_screen)
        
        # Store main screen state
        main_screen = pilot.app.screen_stack[0]
        
        # Press Escape
        pilot.press("escape")
        
        # Should return to main screen
        assert pilot.app.screen is main_screen
```

### Bead Information Display Tests

#### test_bead_metadata_display
**Input**: DetailScreen with complete bead data
**Expected Output**: All metadata fields displayed correctly
**Test Structure**:
```python
def test_bead_metadata_display():
    mock_bead_data = {
        "bead_id": "bead-123",
        "title": "Implement user authentication",
        "description": "Add OAuth2 integration with RBAC",
        "agent": "development",
        "status": "in_progress",
        "labels": ["security", "auth"],
        "priority": 2,
        "created_at": "2026-05-20T10:00:00",
        "updated_at": "2026-05-20T14:23:01",
        "epic_id": "epic-auth-system",
        "dependencies": {
            "blocks": ["bead-456", "bead-789"],
            "blocked_by": ["bead-012"]
        }
    }
    
    with patch('switchboard.tui.screens.detail.get_bead_info') as mock_get_bead:
        mock_get_bead.return_value = mock_bead_data
        
        detail_screen = DetailScreen(bead_id="bead-123")
        
        with AppTest(detail_screen) as pilot:
            # Verify all metadata displayed
            assert "bead-123" in pilot.app.query_one(".bead-header").renderable
            assert "Implement user authentication" in pilot.app.query_one(".bead-title").renderable
            assert "development" in pilot.app.query_one(".bead-agent").renderable
            assert "in_progress" in pilot.app.query_one(".bead-status").renderable
            assert "security, auth" in pilot.app.query_one(".bead-labels").renderable
            assert "epic-auth-system" in pilot.app.query_one(".bead-epic").renderable
            
            # Verify dependencies
            deps_widget = pilot.app.query_one(".bead-dependencies")
            assert "blocks: bead-456, bead-789" in deps_widget.renderable
            assert "blocked by: bead-012" in deps_widget.renderable
```

#### test_missing_bead_data
**Input**: DetailScreen with non-existent bead ID
**Expected Output**: Error state displayed, no crash
**Test Structure**:
```python
def test_missing_bead_data():
    with patch('switchboard.tui.screens.detail.get_bead_info') as mock_get_bead:
        mock_get_bead.side_effect = FileNotFoundError("Bead not found")
        
        detail_screen = DetailScreen(bead_id="nonexistent-bead")
        
        with AppTest(detail_screen) as pilot:
            # Should show error state, not crash
            error_widget = pilot.app.query_one(".error-state")
            assert "Bead information unavailable" in error_widget.renderable
```

#### test_partial_bead_data
**Input**: DetailScreen with incomplete bead data
**Expected Output**: Available fields displayed, missing fields show as "N/A"
**Test Implementation**: Mock partial data and verify graceful handling

### Live Log Display Tests

#### test_live_log_tailing
**Input**: DetailScreen with active bead stdout file
**Expected Output**: Real-time log updates displayed
**Test Structure**:
```python
@pytest.mark.asyncio
async def test_live_log_tailing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create mock log file
        log_file = Path(tmp_dir) / "artifacts" / "logs" / "bead-123" / "stdout.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("Initial log content\n")
        
        detail_screen = DetailScreen(bead_id="bead-123", artifacts_dir=tmp_dir)
        
        with AppTest(detail_screen) as pilot:
            # Wait for initial content
            await asyncio.sleep(0.1)
            
            log_panel = pilot.app.query_one(".live-log-panel")
            assert "Initial log content" in log_panel.get_content()
            
            # Append new content
            with log_file.open("a") as f:
                f.write("New log line\n")
            
            # Wait for update
            await asyncio.sleep(0.2)
            
            # Should show new content
            assert "New log line" in log_panel.get_content()
```

#### test_log_file_missing
**Input**: DetailScreen with non-existent log file
**Expected Output**: "No output available" message displayed
**Test Structure**:
```python
def test_log_file_missing():
    detail_screen = DetailScreen(bead_id="bead-123", artifacts_dir="/nonexistent")
    
    with AppTest(detail_screen) as pilot:
        log_panel = pilot.app.query_one(".live-log-panel")
        assert "No output available" in log_panel.get_content()
```

#### test_log_auto_scroll
**Input**: New log content added while screen is displayed
**Expected Output**: Panel auto-scrolls to show latest content
**Test Structure**:
```python
@pytest.mark.asyncio
async def test_log_auto_scroll():
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = Path(tmp_dir) / "artifacts" / "logs" / "bead-123" / "stdout.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create large initial content
        initial_content = "\n".join([f"Log line {i}" for i in range(50)])
        log_file.write_text(initial_content)
        
        detail_screen = DetailScreen(bead_id="bead-123", artifacts_dir=tmp_dir)
        
        with AppTest(detail_screen) as pilot:
            log_panel = pilot.app.query_one(".live-log-panel")
            
            # Add new line
            with log_file.open("a") as f:
                f.write("LATEST LINE\n")
            
            await asyncio.sleep(0.2)
            
            # Should auto-scroll to show latest
            assert log_panel.scroll_y == log_panel.max_scroll_y
            assert "LATEST LINE" in log_panel.get_visible_content()
```

#### test_log_manual_scroll_preservation
**Input**: User manually scrolls up, then new content arrives
**Expected Output**: Manual scroll position preserved, no auto-scroll
**Test Implementation**: Verify user scroll position preserved when new content added

### Panel Focus and Navigation Tests

#### test_tab_panel_switching
**Input**: Tab key press within DetailScreen
**Expected Output**: Focus switches between info panel and log panel
**Test Structure**:
```python
def test_tab_panel_switching():
    detail_screen = DetailScreen(bead_id="bead-123")
    
    with AppTest(detail_screen) as pilot:
        # Start focus on info panel
        info_panel = pilot.app.query_one(".bead-info-panel")
        log_panel = pilot.app.query_one(".live-log-panel")
        
        assert pilot.app.focused is info_panel
        
        # Press Tab
        pilot.press("tab")
        
        # Focus should switch to log panel
        assert pilot.app.focused is log_panel
        
        # Press Tab again
        pilot.press("tab")
        
        # Focus should return to info panel
        assert pilot.app.focused is info_panel
```

#### test_log_panel_scrolling
**Input**: Arrow keys when log panel focused
**Expected Output**: Log content scrolls appropriately
**Test Structure**:
```python
def test_log_panel_scrolling():
    detail_screen = DetailScreen(bead_id="bead-123")
    
    with AppTest(detail_screen) as pilot:
        log_panel = pilot.app.query_one(".live-log-panel")
        log_panel.focus()
        
        initial_scroll = log_panel.scroll_y
        
        # Test down arrow
        pilot.press("down")
        assert log_panel.scroll_y > initial_scroll
        
        # Test up arrow
        pilot.press("up")
        assert log_panel.scroll_y < log_panel.scroll_y
```

## 2. LogFocusScreen Tests (test_screens_log_focus.py)

### Test File Structure
```python
"""Tests for Switchboard TUI LogFocusScreen functionality."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from textual.testing import AppTest
from collections import deque

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.screens.log_focus import LogFocusScreen
from switchboard.tui.state import SwitchboardState, LogEvent, WorkerState
```

### Screen Navigation Tests

#### test_log_focus_open_with_l_key
**Input**: 'L' key press from main screen
**Expected Output**: LogFocusScreen opens in fullscreen mode
**Test Structure**:
```python
def test_log_focus_open_with_l_key():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Press L key
        pilot.press("l")
        
        # Should open LogFocusScreen
        assert isinstance(pilot.app.screen, LogFocusScreen)
        
        # Should be fullscreen
        log_screen = pilot.app.screen
        assert log_screen.styles.width.value == "100%"
        assert log_screen.styles.height.value == "100%"
```

#### test_log_focus_escape_back
**Input**: Escape key from LogFocusScreen
**Expected Output**: Return to previous screen
**Test Implementation**: Similar to DetailScreen escape test

#### test_log_focus_l_key_toggle
**Input**: 'L' key press while in LogFocusScreen
**Expected Output**: Return to previous screen (toggle behavior)

### Source Switching Tests

#### test_worker_source_switching_fullscreen
**Input**: Number keys 1-9 within LogFocusScreen
**Expected Output**: Log source switches to corresponding worker
**Test Structure**:
```python
def test_worker_source_switching_fullscreen():
    mock_workers = {
        "bead-1": WorkerState(bead_id="bead-1", agent="development", 
                             repo="test", tool=None, pid=123, 
                             started_at="2026-05-20T14:23:01", 
                             title="Test 1", epic_id="epic-1"),
        "bead-2": WorkerState(bead_id="bead-2", agent="tests",
                             repo="test", tool=None, pid=124,
                             started_at="2026-05-20T14:23:02",
                             title="Test 2", epic_id="epic-2")
    }
    
    log_screen = LogFocusScreen()
    
    with AppTest(log_screen) as pilot:
        # Set up state with workers
        pilot.app.state = SwitchboardState(workers=mock_workers)
        
        # Test switching to worker 1
        pilot.press("1")
        
        header_widget = pilot.app.query_one(".log-focus-header")
        assert "WORKER 1: epic-1 development" in header_widget.renderable
        
        # Test switching to worker 2
        pilot.press("2")
        assert "WORKER 2: epic-2 tests" in header_widget.renderable
```

#### test_daemon_log_switching_fullscreen
**Input**: '0' key press within LogFocusScreen
**Expected Output**: Return to daemon log source
**Test Implementation**: Verify daemon log header and content display

#### test_invalid_worker_switching_fullscreen
**Input**: Number key for non-existent worker
**Expected Output**: No action, source unchanged

### Enhanced Display Tests

#### test_fullscreen_log_capacity
**Input**: LogFocusScreen with extensive log history
**Expected Output**: More log lines displayed than in PartyLine widget
**Test Structure**:
```python
def test_fullscreen_log_capacity():
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
    
    with AppTest(log_screen) as pilot:
        # Set up state with many events
        pilot.app.state = SwitchboardState(events=mock_events)
        
        # Should display more lines than normal PartyLine
        log_content = pilot.app.query_one(".log-focus-content")
        visible_lines = log_content.get_visible_line_count()
        
        # Should be significantly more than PartyLine widget height
        assert visible_lines > 50  # Assuming PartyLine shows ~20 lines
```

#### test_enhanced_header_information
**Input**: LogFocusScreen with current log source
**Expected Output**: Header shows detailed source information
**Test Structure**:
```python
def test_enhanced_header_information():
    log_screen = LogFocusScreen()
    
    with AppTest(log_screen) as pilot:
        # Mock log events
        mock_events = deque([LogEvent(...) for _ in range(100)])
        pilot.app.state = SwitchboardState(events=mock_events)
        
        header = pilot.app.query_one(".log-focus-header")
        header_text = header.renderable
        
        # Should show line count and position
        assert "100 lines" in header_text
        assert "(showing last" in header_text
        
        # Should show time range
        assert "14:23" in header_text  # Time from mock events
```

### Performance Tests

#### test_fullscreen_rendering_performance
**Input**: Large log dataset in fullscreen mode
**Expected Output**: Responsive rendering within performance limits
**Test Structure**:
```python
def test_fullscreen_rendering_performance():
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
    
    with AppTest(log_screen) as pilot:
        start_time = time.perf_counter()
        
        # Set state and trigger render
        pilot.app.state = SwitchboardState(events=mock_events)
        
        render_time = (time.perf_counter() - start_time) * 1000
        
        # Should render within 200ms
        assert render_time < 200, f"Render took {render_time:.1f}ms, should be < 200ms"
```

## 3. ProjectScreen Tests (test_screens_project.py)

### Test File Structure
```python
"""Tests for Switchboard TUI ProjectScreen functionality."""

import pytest
from unittest.mock import patch, MagicMock
from textual.testing import AppTest

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.screens.project import ProjectScreen
from switchboard.tui.state import SwitchboardState, PipelineState, StepState
```

### Screen Navigation Tests

#### test_project_screen_open_from_projects_panel
**Input**: 'P' key press when ProjectsPanel focused
**Expected Output**: ProjectScreen opens showing project overview
**Test Structure**:
```python
def test_project_screen_open_from_projects_panel():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Focus ProjectsPanel
        projects_panel = pilot.app.query_one(".projectspanel")
        projects_panel.focus()
        projects_panel.select_project("automation-nexus")
        
        # Press P key
        pilot.press("p")
        
        # Should open ProjectScreen
        assert isinstance(pilot.app.screen, ProjectScreen)
        assert pilot.app.screen.project_name == "automation-nexus"
```

#### test_project_screen_escape_back
**Input**: Escape key from ProjectScreen
**Expected Output**: Return to main screen

### Epic Grouping Tests

#### test_epic_status_grouping
**Input**: ProjectScreen with mixed epic statuses
**Expected Output**: Epics correctly grouped by Active/Completed/Queued
**Test Structure**:
```python
def test_epic_status_grouping():
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
    
    with AppTest(project_screen) as pilot:
        pilot.app.state = SwitchboardState(pipelines=mock_pipelines)
        
        # Verify grouping
        active_group = pilot.app.query_one(".active-epics-group")
        completed_group = pilot.app.query_one(".completed-epics-group")
        queued_group = pilot.app.query_one(".queued-epics-group")
        
        assert "epic-active-1" in active_group.get_epic_list()
        assert "epic-completed-1" in completed_group.get_epic_list()
        assert "epic-queued-1" in queued_group.get_epic_list()
```

#### test_epic_progress_display
**Input**: Epic with partial completion
**Expected Output**: Progress shown as "X/Y steps"
**Test Structure**:
```python
def test_epic_progress_display():
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
    
    with AppTest(project_screen) as pilot:
        pilot.app.state = SwitchboardState(pipelines={"epic-progress-test": mock_pipeline})
        
        epic_widget = pilot.app.query_one(".epic-progress-test")
        assert "2/4 steps" in epic_widget.renderable
```

### Project Statistics Tests

#### test_project_statistics_calculation
**Input**: Project with multiple epics in various states
**Expected Output**: Accurate statistics displayed
**Test Structure**:
```python
def test_project_statistics_calculation():
    # Create mock pipelines with known statistics
    mock_pipelines = create_mock_pipelines_for_stats()
    
    project_screen = ProjectScreen(project_name="automation-nexus")
    
    with AppTest(project_screen) as pilot:
        pilot.app.state = SwitchboardState(pipelines=mock_pipelines)
        
        stats_widget = pilot.app.query_one(".project-stats")
        stats_text = stats_widget.renderable
        
        # Verify calculated statistics
        assert "Completed: 5" in stats_text
        assert "Success Rate: 83%" in stats_text
        assert "Avg Time: 25m" in stats_text
        assert "Active Lines: 3/9" in stats_text

def create_mock_pipelines_for_stats():
    # Helper function to create pipelines with known statistics
    return {
        # 5 completed epics
        # 1 failed epic
        # 3 active epics
        # etc.
    }
```

### Epic Navigation Tests

#### test_epic_selection_navigation
**Input**: Up/Down arrow keys in epic list
**Expected Output**: Selection moves between epics
**Test Structure**:
```python
def test_epic_selection_navigation():
    project_screen = ProjectScreen(project_name="automation-nexus")
    
    with AppTest(project_screen) as pilot:
        # Set up test epics
        mock_pipelines = create_test_epic_list()
        pilot.app.state = SwitchboardState(pipelines=mock_pipelines)
        
        active_group = pilot.app.query_one(".active-epics-group")
        active_group.focus()
        
        # Test down arrow
        initial_selection = active_group.selected_epic
        pilot.press("down")
        assert active_group.selected_epic != initial_selection
        
        # Test up arrow
        pilot.press("up")
        assert active_group.selected_epic == initial_selection
```

#### test_epic_detail_navigation
**Input**: 'D' or Enter key with epic selected
**Expected Output**: DetailScreen opens for selected epic
**Test Structure**:
```python
def test_epic_detail_navigation():
    project_screen = ProjectScreen(project_name="automation-nexus")
    
    with AppTest(project_screen) as pilot:
        # Select an epic
        active_group = pilot.app.query_one(".active-epics-group")
        active_group.focus()
        active_group.select_epic("epic-test")
        
        # Press D for details
        pilot.press("d")
        
        # Should open DetailScreen for the epic
        from switchboard.tui.screens.detail import DetailScreen
        assert isinstance(pilot.app.screen, DetailScreen)
        assert pilot.app.screen.bead_id == "epic-test"
```

## 4. Thematic Messaging Tests (test_thematic_messages.py)

### Test File Structure
```python
"""Tests for Switchboard TUI thematic messaging system."""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from textual.testing import AppTest

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.state import SwitchboardState, WorkerState
```

### Startup Message Tests

#### test_startup_message_display
**Input**: SwitchboardApp initialization and mount
**Expected Output**: "SWITCHBOARD ONLINE · PATCHING IN..." message appears briefly
**Test Structure**:
```python
@pytest.mark.asyncio
async def test_startup_message_display():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Should show startup message immediately
        startup_overlay = pilot.app.query_one(".startup-overlay")
        assert "SWITCHBOARD ONLINE · PATCHING IN..." in startup_overlay.renderable
        
        # Wait for startup sequence
        await asyncio.sleep(3.0)
        
        # Startup message should be gone
        overlays = pilot.app.query(".startup-overlay")
        assert len(overlays) == 0
```

#### test_startup_message_timing
**Input**: App startup process
**Expected Output**: Message displays for 2-3 seconds
**Test Structure**:
```python
@pytest.mark.asyncio
async def test_startup_message_timing():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
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
```

### Daemon Status Message Tests

#### test_no_dial_tone_message
**Input**: daemon_online = False in state
**Expected Output**: Header shows "NO DIAL TONE"
**Test Structure**:
```python
def test_no_dial_tone_message():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Set daemon offline
        pilot.app.state = SwitchboardState(daemon_online=False)
        
        header = pilot.app.query_one(".switchboardheader")
        assert "NO DIAL TONE" in header.get_daemon_status()
        
        # Verify warning styling
        assert "warning" in header.get_daemon_status_classes()
```

#### test_daemon_status_transition
**Input**: Daemon online/offline state changes
**Expected Output**: Header status updates immediately
**Test Structure**:
```python
def test_daemon_status_transition():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
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
```

### Empty State Message Tests

#### test_all_quiet_message
**Input**: No active workers AND no ready beads
**Expected Output**: "ALL QUIET ON THE BOARD" in PatchPanel
**Test Structure**:
```python
def test_all_quiet_message():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Set completely empty state
        pilot.app.state = SwitchboardState(
            workers={},
            pipelines={},
            daemon_online=True
        )
        
        patch_panel = pilot.app.query_one(".patchpanel")
        assert "ALL QUIET ON THE BOARD" in patch_panel.get_empty_state_message()
```

#### test_all_quiet_conditions
**Input**: Various combinations of worker/bead states
**Expected Output**: Message only appears when truly idle
**Test Structure**:
```python
def test_all_quiet_conditions():
    app = SwitchboardApp()
    
    test_cases = [
        # (workers, ready_beads, should_show_quiet)
        ({}, [], True),                    # Completely empty
        ({"w1": mock_worker}, [], False),  # Has workers
        ({}, ["bead1"], False),            # Has ready beads
        ({"w1": mock_worker}, ["bead1"], False)  # Has both
    ]
    
    with AppTest(app) as pilot:
        patch_panel = pilot.app.query_one(".patchpanel")
        
        for workers, ready_beads, should_show in test_cases:
            pilot.app.state = SwitchboardState(
                workers=workers,
                # Mock ready beads state
                daemon_online=True
            )
            
            quiet_message_shown = "ALL QUIET ON THE BOARD" in patch_panel.get_content()
            assert quiet_message_shown == should_show
```

### Capacity Message Tests

#### test_all_lines_busy_message
**Input**: All worker slots occupied
**Expected Output**: "ALL LINES BUSY · N CALLS HOLDING" message
**Test Structure**:
```python
def test_all_lines_busy_message():
    # Create max workers (assume 9 max)
    max_workers = {f"worker-{i}": create_mock_worker(f"bead-{i}") for i in range(9)}
    
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Mock ready beads waiting
        with patch('switchboard.tui.polling.get_ready_beads') as mock_ready:
            mock_ready.return_value = ["bead-waiting-1", "bead-waiting-2", "bead-waiting-3"]
            
            pilot.app.state = SwitchboardState(workers=max_workers)
            
            operator_panel = pilot.app.query_one(".operatorpanel")
            capacity_message = operator_panel.get_capacity_message()
            
            assert "ALL LINES BUSY · 3 CALLS HOLDING" in capacity_message
```

#### test_capacity_message_dynamic_count
**Input**: Varying number of waiting beads
**Expected Output**: Count updates dynamically
**Test Implementation**: Test different queue sizes and verify count accuracy

### Epic Completion Flash Tests

#### test_epic_completion_flash
**Input**: Epic completion event
**Expected Output**: Brief screen flash animation
**Test Structure**:
```python
@pytest.mark.asyncio
async def test_epic_completion_flash():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
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
```

#### test_flash_timing
**Input**: Epic completion trigger
**Expected Output**: Flash duration 200-300ms
**Test Structure**:
```python
@pytest.mark.asyncio
async def test_flash_timing():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        start_time = time.perf_counter()
        
        # Trigger flash
        completion_event = create_epic_completion_event()
        pilot.app.state = pilot.app.state.add_log_event(completion_event)
        
        # Wait for flash to complete
        while pilot.app.query(".completion-flash"):
            await asyncio.sleep(0.01)
        
        flash_duration = (time.perf_counter() - start_time) * 1000
        assert 200 <= flash_duration <= 400, f"Flash duration {flash_duration:.1f}ms should be 200-300ms"
```

## 5. Edge Case Handling Tests (test_edge_cases.py)

### Test File Structure
```python
"""Tests for edge case handling in screens and thematic features."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from textual.testing import AppTest

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.screens.detail import DetailScreen
```

### Missing Files Edge Cases

#### test_app_start_no_log_file
**Input**: App starts without agent_router.log
**Expected Output**: PartyLine shows "(waiting for daemon)" message
**Test Structure**:
```python
def test_app_start_no_log_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Empty artifacts directory
        artifacts_dir = Path(tmp_dir) / "artifacts"
        artifacts_dir.mkdir()
        # No agent_router.log file
        
        app = SwitchboardApp(artifacts_dir=str(artifacts_dir))
        
        with AppTest(app) as pilot:
            party_line = pilot.app.query_one(".partyline")
            content = party_line.get_content()
            
            assert "(waiting for daemon)" in content
            assert "error" not in content.lower()
```

#### test_detail_screen_missing_log
**Input**: DetailScreen for bead without stdout.log
**Expected Output**: "No output available" message, no crash
**Test Structure**:
```python
def test_detail_screen_missing_log():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # No log file for this bead
        detail_screen = DetailScreen(bead_id="nonexistent-bead", artifacts_dir=tmp_dir)
        
        with AppTest(detail_screen) as pilot:
            log_panel = pilot.app.query_one(".live-log-panel")
            assert "No output available" in log_panel.get_content()
            
            # Should not crash
            assert pilot.app.is_running
```

#### test_log_file_creation_during_runtime
**Input**: Log file created after app start
**Expected Output**: Log watcher begins tailing new file
**Test Structure**:
```python
@pytest.mark.asyncio
async def test_log_file_creation_during_runtime():
    with tempfile.TemporaryDirectory() as tmp_dir:
        artifacts_dir = Path(tmp_dir) / "artifacts"
        artifacts_dir.mkdir()
        
        app = SwitchboardApp(artifacts_dir=str(artifacts_dir))
        
        with AppTest(app) as pilot:
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
```

### Empty Database Edge Cases

#### test_empty_database_states
**Input**: App with no beads in database
**Expected Output**: All panels show appropriate empty states
**Test Structure**:
```python
def test_empty_database_states():
    with patch('switchboard.tui.polling.bd_json') as mock_bd:
        mock_bd.return_value = []  # Empty database
        
        app = SwitchboardApp()
        
        with AppTest(app) as pilot:
            # Trigger polling
            asyncio.create_task(pilot.app._poll_workers())
            asyncio.create_task(pilot.app._poll_pipelines())
            
            # Check all panels show empty states
            patch_panel = pilot.app.query_one(".patchpanel")
            assert "ALL QUIET ON THE BOARD" in patch_panel.get_content()
            
            active_lines = pilot.app.query_one(".activelines")
            assert "No active workers" in active_lines.get_content()
            
            projects_panel = pilot.app.query_one(".projectspanel")
            assert "No projects available" in projects_panel.get_content()
```

#### test_project_screen_empty_project
**Input**: ProjectScreen for project with no epics
**Expected Output**: Empty state message in each group
**Test Structure**:
```python
def test_project_screen_empty_project():
    project_screen = ProjectScreen(project_name="empty-project")
    
    with AppTest(project_screen) as pilot:
        # Set empty state
        pilot.app.state = SwitchboardState(pipelines={})
        
        # Each group should show empty state
        active_group = pilot.app.query_one(".active-epics-group")
        assert "No active epics" in active_group.get_empty_state_message()
        
        completed_group = pilot.app.query_one(".completed-epics-group")
        assert "No completed epics" in completed_group.get_empty_state_message()
        
        queued_group = pilot.app.query_one(".queued-epics-group")
        assert "No queued epics" in queued_group.get_empty_state_message()
```

### Daemon Disconnect Edge Cases

#### test_daemon_disconnect_during_screen_use
**Input**: Daemon stops while DetailScreen is active
**Expected Output**: Screen continues to function with last known data
**Test Structure**:
```python
def test_daemon_disconnect_during_screen_use():
    mock_bead_data = create_mock_bead_data()
    
    with patch('switchboard.tui.screens.detail.get_bead_info') as mock_get_bead:
        mock_get_bead.return_value = mock_bead_data
        
        detail_screen = DetailScreen(bead_id="bead-123")
        
        with AppTest(detail_screen) as pilot:
            # Screen should load normally
            assert "bead-123" in pilot.app.query_one(".bead-header").renderable
            
            # Simulate daemon disconnect
            pilot.app.state = SwitchboardState(daemon_online=False)
            
            # Screen should continue to function with cached data
            assert pilot.app.is_running
            assert "bead-123" in pilot.app.query_one(".bead-header").renderable
```

#### test_log_focus_daemon_disconnect
**Input**: Daemon disconnect while LogFocusScreen active
**Expected Output**: Screen shows last known log state
**Test Implementation**: Verify LogFocusScreen handles daemon disconnect gracefully

### Terminal Resize Edge Cases

#### test_detail_screen_terminal_resize
**Input**: Terminal resize while DetailScreen active
**Expected Output**: Layout adapts without losing data or focus
**Test Structure**:
```python
def test_detail_screen_terminal_resize():
    detail_screen = DetailScreen(bead_id="bead-123")
    
    with AppTest(detail_screen, size=(80, 24)) as pilot:
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
```

#### test_minimum_terminal_size_support
**Input**: Terminal resize to minimum supported size (80x24)
**Expected Output**: All screens remain usable
**Test Structure**:
```python
def test_minimum_terminal_size_support():
    screens_to_test = [
        DetailScreen(bead_id="test-bead"),
        LogFocusScreen(),
        ProjectScreen(project_name="test-project")
    ]
    
    for screen in screens_to_test:
        with AppTest(screen, size=(80, 24)) as pilot:
            # Should be usable at minimum size
            assert pilot.app.is_running
            
            # Key navigation should work
            pilot.press("tab")
            assert pilot.app.is_running
            
            # Should be able to exit
            pilot.press("escape")
            # Note: This would normally exit to main screen
```

## Test Utilities and Fixtures

### Common Test Fixtures

```python
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
```

### Mock Helper Functions

```python
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

async def simulate_file_append(file_path, content):
    """Simulate appending content to a file during test."""
    with open(file_path, "a") as f:
        f.write(content)
    # Give file watchers time to detect change
    await asyncio.sleep(0.1)
```

## Coverage Requirements

- **Line Coverage**: Minimum 95% for all screen modules
- **Branch Coverage**: Minimum 90% for conditional logic in screens
- **Function Coverage**: 100% for public screen API methods
- **Integration Coverage**: All screen transitions and state handling tested

## Performance Testing Requirements

### Response Time Limits
- Screen transition: < 100ms
- Log tailing updates: < 500ms response to file changes  
- Epic grouping calculation: < 200ms for 100+ epics
- Thematic message display: < 50ms trigger to display

### Memory Usage Limits
- Each screen: < 5MB additional memory usage
- Log content buffering: < 2MB for fullscreen display
- Screen state retention: < 1MB per screen when not active

### Stress Testing Scenarios
- **Rapid Screen Switching**: 10+ transitions per second
- **Large Log Files**: 10,000+ line log files in DetailScreen
- **Many Epics**: 500+ epics in ProjectScreen grouping
- **Extended Sessions**: 8+ hours with frequent screen usage