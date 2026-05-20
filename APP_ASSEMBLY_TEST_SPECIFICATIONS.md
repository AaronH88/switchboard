# Switchboard TUI App Assembly - Test Specifications

## Test Organization

Tests are organized by functional area following the existing patterns in the codebase:
- Use `pytest` as test framework with `textual.testing.AppTest` for TUI testing
- Use `unittest.mock` for mocking external dependencies and widget interactions
- Use `tempfile` for temporary file operations and mock artifacts directories
- Use async test utilities for polling and background task testing
- Import modules using sys.path.insert pattern for consistency

## 1. App Layout Integration Tests (test_app_assembly_layout.py)

### Test File Structure
```python
"""Tests for Switchboard TUI app assembly layout integration."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from textual.testing import AppTest
from pathlib import Path
import tempfile

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.state import SwitchboardState
```

### Widget Mounting Tests

#### test_app_compose_widget_hierarchy
**Input**: SwitchboardApp initialization
**Expected Output**: All required widgets mounted in correct DOM order
**Test Structure**:
```python
def test_app_compose_widget_hierarchy():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Verify widget presence and order
        expected_widgets = [
            "SwitchboardHeader",
            "OperatorPanel", 
            "ProjectsPanel",
            "PatchPanel",
            "ActiveLines",
            "PartyLine", 
            "Footer"
        ]
        
        for widget_name in expected_widgets:
            assert pilot.app.query_one(f".{widget_name.lower()}")
```
**Edge Cases**:
- Widget creation failure for individual widgets
- Missing CSS classes for layout
- Memory constraints preventing all widget instantiation

#### test_app_compose_widget_positioning
**Input**: Mounted widgets in terminal size 80x24
**Expected Output**: Widgets positioned according to layout specification
**Layout Verification**:
- SwitchboardHeader: top row, full width
- Sidebars: left and right, correct height allocation
- PatchPanel: main area, scrollable
- ActiveLines: tabular layout below main area
- PartyLine: log area with proper boundaries  
- Footer: bottom row, status bar format

#### test_app_layout_terminal_resize
**Input**: Terminal resize events during operation
**Expected Output**: Layout adapts correctly to new dimensions
**Test Cases**:
```python
# Test resize scenarios
resize_scenarios = [
    (120, 40),  # Large terminal
    (80, 24),   # Standard terminal  
    (60, 20),   # Narrow terminal (sidebar collapse)
    (200, 50),  # Wide terminal
]
```
**Verification**:
- No widget overlap after resize
- Scrollable areas remain functional
- Sidebar behavior on narrow terminals

### Widget State Integration Tests

#### test_app_shared_state_initialization
**Input**: SwitchboardApp startup
**Expected Output**: All widgets share same SwitchboardState instance
**Verification**:
```python
def test_app_shared_state_initialization():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Get state references from each widget
        header_state = pilot.app.query_one(".header").state
        patch_panel_state = pilot.app.query_one(".patchpanel").state
        party_line_state = pilot.app.query_one(".partyline").state
        
        # All should reference same object
        assert header_state is patch_panel_state
        assert patch_panel_state is party_line_state
```

#### test_app_widget_state_propagation
**Input**: State update through app's state management
**Expected Output**: All relevant widgets reflect the change
**Test Flow**:
1. Capture initial widget state
2. Trigger state update (add worker)
3. Verify widgets show updated information
4. Verify update timing (< 50ms)

## 2. Keybinding System Tests (test_app_assembly_keybindings.py)

### Test File Structure  
```python
"""Tests for Switchboard TUI keybinding system integration."""

import pytest
from textual.testing import AppTest
from textual.keys import Keys
import asyncio

from switchboard.tui.app import SwitchboardApp
```

### Primary Navigation Tests

#### test_quit_keybinding
**Input**: 'Q' or 'q' key press
**Expected Output**: Application exits immediately
**Test Implementation**:
```python
def test_quit_keybinding():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Test lowercase
        pilot.press("q")
        assert pilot.app.is_running is False
        
    # Test uppercase
    app2 = SwitchboardApp()
    with AppTest(app2) as pilot:
        pilot.press("Q")
        assert pilot.app.is_running is False
```

#### test_tab_focus_cycling
**Input**: Tab and Shift+Tab key presses
**Expected Output**: Focus cycles through interactive widgets in correct order
**Expected Cycle Order**:
1. OperatorPanel
2. ProjectsPanel  
3. PatchPanel
4. ActiveLines
5. PartyLine
6. Back to OperatorPanel

**Test Implementation**:
```python
def test_tab_focus_cycling():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        # Track focus progression
        focus_sequence = []
        
        for i in range(6):  # Complete cycle
            pilot.press("tab")
            focused_widget = pilot.app.focused
            focus_sequence.append(focused_widget.__class__.__name__)
            
        # Verify expected sequence
        expected_sequence = [
            "OperatorPanel", "ProjectsPanel", "PatchPanel", 
            "ActiveLines", "PartyLine", "OperatorPanel"
        ]
        assert focus_sequence == expected_sequence
```

#### test_reverse_tab_cycling
**Input**: Shift+Tab key presses
**Expected Output**: Focus cycles backward through widgets
**Verification**: Reverse of normal Tab order

### Action Keybinding Tests

#### test_detail_view_keybinding
**Input**: 'D' or Enter key when item selected
**Expected Output**: Detail screen opens for selected item
**Test Scenarios**:
- PatchPanel focused with pipeline selected
- ActiveLines focused with worker selected  
- No selection (should be ignored)
- Invalid selection (should be ignored)

#### test_refresh_keybinding
**Input**: 'R' key press
**Expected Output**: All polling systems trigger immediate refresh
**Mock Setup**: Mock all polling functions
**Verification**: All poll functions called immediately

#### test_log_focus_toggle_keybinding
**Input**: 'L' or 'F' key press
**Expected Output**: PartyLine toggles fullscreen mode (placeholder)
**Test Implementation**:
```python
def test_log_focus_toggle_keybinding():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
        initial_layout = pilot.app.query_one(".partyline").styles.height
        
        # Toggle focus mode
        pilot.press("l")
        
        # Should change layout (placeholder behavior)
        # Exact implementation depends on final design
        assert pilot.app.focused.__class__.__name__ == "PartyLine"
```

### PartyLine Source Switching Tests

#### test_worker_source_switching
**Input**: Number keys 1-9
**Expected Output**: PartyLine switches to corresponding worker output
**Test Setup**:
```python
def test_worker_source_switching():
    # Mock workers in state
    mock_workers = {
        "bead-1": WorkerState(bead_id="bead-1", agent="development", ...),
        "bead-2": WorkerState(bead_id="bead-2", agent="tests", ...),
        "bead-3": WorkerState(bead_id="bead-3", agent="review", ...)
    }
    
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
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
```

#### test_daemon_log_switching
**Input**: '0' key press
**Expected Output**: PartyLine returns to daemon log source
**Test Implementation**: Verify source switches back to daemon after using worker sources

#### test_invalid_worker_switching
**Input**: Number keys for non-existent workers
**Expected Output**: No action, PartyLine source unchanged
**Test Cases**: Keys 1-9 when fewer workers exist

### Navigation Keybinding Tests

#### test_scrollable_widget_navigation
**Input**: Arrow keys when scrollable widget focused
**Expected Output**: Content scrolls appropriately
**Test Widgets**: PatchPanel, ActiveLines, PartyLine
**Test Keys**: Up, Down, Page Up, Page Down, Home, End

#### test_keybinding_context_sensitivity
**Input**: Same key in different widget contexts
**Expected Output**: Context-appropriate behavior
**Example**: Enter key behavior differs between PatchPanel (details) and PartyLine (no action)

## 3. Polling Integration Tests (test_app_assembly_polling.py)

### Test File Structure
```python
"""Tests for Switchboard TUI polling system integration."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from pathlib import Path
import tempfile

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.polling import poll_workers, poll_stats, tail_file
```

### Polling System Startup Tests

#### test_polling_system_initialization
**Input**: SwitchboardApp.on_mount() execution
**Expected Output**: All 4 polling systems start correctly
**Mock Setup**: Mock all polling functions and file operations
**Verification**:
```python
async def test_polling_system_initialization():
    with patch('switchboard.tui.polling.tail_file') as mock_tail, \
         patch('switchboard.tui.polling.poll_workers') as mock_poll_workers, \
         patch('switchboard.tui.polling.poll_stats') as mock_poll_stats:
        
        app = SwitchboardApp()
        
        with AppTest(app) as pilot:
            # Wait for mount to complete
            await asyncio.sleep(0.1)
            
            # Verify all polling systems started
            assert mock_tail.called
            assert mock_poll_workers.called  
            assert mock_poll_stats.called
            
            # Verify correct intervals set
            # Implementation depends on how intervals are configured
```

#### test_log_watcher_startup
**Input**: Log file exists at startup
**Expected Output**: Log watcher begins tailing immediately
**Test Setup**: Create temporary log file with content
**Verification**: New log entries appear in PartyLine

#### test_log_watcher_missing_file
**Input**: Log file does not exist at startup
**Expected Output**: Watcher waits for file creation
**Test Flow**:
1. Start app without log file
2. Create log file after delay
3. Verify watcher begins tailing new file

#### test_polling_interval_configuration
**Input**: Custom polling intervals in app config
**Expected Output**: Pollers use specified intervals
**Test Setup**: Initialize app with custom poll_interval
**Verification**: Intervals match configuration

### Polling Error Handling Tests

#### test_bd_command_unavailable
**Input**: `bd` command not in PATH
**Expected Output**: Polling handles error gracefully, daemon status shows offline
**Mock Setup**: Mock subprocess to raise FileNotFoundError
**Verification**: App continues to function, error logged but not displayed

#### test_malformed_bd_response
**Input**: `bd` command returns invalid JSON
**Expected Output**: Polling handles error gracefully
**Mock Setup**: Mock subprocess to return non-JSON response
**Verification**: Previous state preserved, error recovery attempted

#### test_network_timeout_handling
**Input**: `bd` command times out
**Expected Output**: Polling system uses exponential backoff
**Mock Setup**: Mock subprocess to raise TimeoutExpired
**Verification**: Subsequent polls delayed appropriately

#### test_log_file_permission_error
**Input**: Log file becomes unreadable during operation
**Expected Output**: Log watcher handles gracefully, recovers when permissions restored
**Test Setup**: Change file permissions during tailing

### Polling Performance Tests

#### test_polling_ui_responsiveness
**Input**: Heavy polling load
**Expected Output**: UI remains responsive (< 100ms key response)
**Test Implementation**: Measure key press response time during active polling
**Performance Requirement**: Key actions complete within 100ms

#### test_polling_memory_stability
**Input**: Extended polling operation (simulated)
**Expected Output**: Memory usage remains stable
**Test Duration**: Simulate 1000 poll cycles
**Memory Requirement**: < 1MB increase over baseline

#### test_concurrent_polling_safety
**Input**: All pollers active simultaneously
**Expected Output**: No race conditions or state corruption
**Verification**: State consistency maintained across rapid updates

## 4. State Propagation Tests (test_app_assembly_state.py)

### Test File Structure
```python
"""Tests for Switchboard TUI state propagation system."""

import pytest
from unittest.mock import patch, MagicMock
from textual.testing import AppTest
import asyncio
from collections import deque

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.state import SwitchboardState, WorkerState, LogEvent
```

### State Update Propagation Tests

#### test_worker_state_propagation
**Input**: New worker added to state.workers
**Expected Output**: ActiveLines and OperatorPanel widgets update
**Test Implementation**:
```python
def test_worker_state_propagation():
    app = SwitchboardApp()
    
    with AppTest(app) as pilot:
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
```

#### test_pipeline_state_propagation
**Input**: Pipeline data changes in state.pipelines
**Expected Output**: PatchPanel and ProjectsPanel widgets update
**Verification**:
- Pipeline rows appear/disappear in PatchPanel
- Project counts update in ProjectsPanel
- Progress indicators reflect current status

#### test_log_event_propagation
**Input**: New LogEvent added to state.events
**Expected Output**: PartyLine displays new log entry
**Test Timing**: Verify update occurs within 50ms

#### test_daemon_status_propagation
**Input**: daemon_online boolean changes
**Expected Output**: Footer status indicator updates
**Test Cases**:
- Online → Offline transition
- Offline → Online transition
- Multiple rapid status changes

### State Consistency Tests

#### test_atomic_state_updates
**Input**: Multiple rapid state changes
**Expected Output**: No partial updates visible to widgets
**Test Implementation**: Rapid state mutations with verification between each

#### test_state_rollback_on_error
**Input**: State update that causes widget error
**Expected Output**: State reverts to previous known-good state
**Mock Setup**: Mock widget update to raise exception

#### test_concurrent_state_access
**Input**: Simultaneous state reads and writes
**Expected Output**: No race conditions or state corruption
**Test Setup**: Async tasks performing concurrent state operations

### Widget Update Timing Tests

#### test_update_propagation_timing
**Input**: State change event
**Expected Output**: Widget updates complete within 50ms
**Measurement**: Time from state change to widget render completion

#### test_batch_update_optimization
**Input**: Multiple rapid state changes
**Expected Output**: Widget updates are batched for performance
**Verification**: Widget update count < state change count

#### test_focus_preservation_during_updates
**Input**: State update while widget has focus
**Expected Output**: Focus and cursor position preserved
**Test Widgets**: Scrollable widgets with user focus

## 5. Footer Integration Tests (test_app_assembly_footer.py)

### Test File Structure
```python
"""Tests for Switchboard TUI footer integration."""

import pytest
from textual.testing import AppTest

from switchboard.tui.app import SwitchboardApp
from switchboard.tui.state import SwitchboardState
```

### Keybinding Hints Tests

#### test_default_keybinding_hints
**Input**: App startup with no focus
**Expected Output**: Default keybinding hints displayed
**Expected Text**: `Q:Quit  Tab:Navigate  R:Refresh  1-9:Workers  0:Daemon`

#### test_context_sensitive_hints
**Input**: Focus changes between widgets
**Expected Output**: Hints update to match focused widget
**Test Cases**:
```python
focus_hint_mapping = {
    "PatchPanel": "Q:Quit  D:Details  R:Refresh  ↑↓:Scroll  Tab:Navigate",
    "PartyLine": "Q:Quit  L:Focus  1-9:Workers  0:Daemon  ↑↓:Scroll  Tab:Navigate",
    "ActiveLines": "Q:Quit  D:Details  R:Refresh  ↑↓:Scroll  Tab:Navigate"
}
```

#### test_hints_layout_responsiveness
**Input**: Terminal resize events
**Expected Output**: Hints remain visible and readable
**Test Cases**: Various terminal widths, text truncation on narrow screens

### Daemon Status Tests

#### test_daemon_online_indicator
**Input**: daemon_online = True in state
**Expected Output**: `(*) DAEMON ONLINE` with active color
**Color Verification**: Uses theme's active/success color

#### test_daemon_offline_indicator  
**Input**: daemon_online = False in state
**Expected Output**: `(✗) DAEMON OFFLINE` with error color
**Color Verification**: Uses theme's error/red color

#### test_daemon_unknown_indicator
**Input**: Initial state before first poll
**Expected Output**: `(?) DAEMON STATUS` with muted color
**Color Verification**: Uses theme's muted/inactive color

#### test_daemon_status_update_timing
**Input**: daemon_online state change
**Expected Output**: Status updates within 5 seconds
**Test Implementation**: Measure time from state change to visual update

### Footer Layout Tests

#### test_footer_positioning
**Input**: App with full layout
**Expected Output**: Footer at bottom, full width, single row
**Layout Verification**: No overlap with other widgets

#### test_status_text_alignment
**Input**: Footer with hints and daemon status
**Expected Output**: No text overlap, proper spacing
**Test Cases**: Various terminal widths

#### test_footer_theme_consistency
**Input**: App with loaded theme
**Expected Output**: Footer colors match overall theme
**Theme Verification**: Background, text, and accent colors consistent

## 6. Integration Performance Tests (test_app_assembly_performance.py)

### Test File Structure
```python
"""Performance tests for Switchboard TUI app assembly."""

import pytest
import time
import psutil
import asyncio
from textual.testing import AppTest

from switchboard.tui.app import SwitchboardApp
```

### Startup Performance Tests

#### test_app_assembly_startup_timing
**Input**: SwitchboardApp initialization and mount
**Expected Output**: Complete assembly within 2 seconds
**Measurement**: Time from instantiation to full widget mount
**Performance Requirement**: < 2000ms

#### test_initial_state_loading_performance
**Input**: App startup with mock state data
**Expected Output**: State propagation within startup time budget
**Mock Data**: 10 workers, 5 pipelines, 100 log events

### Runtime Performance Tests

#### test_state_update_performance
**Input**: State changes during operation
**Expected Output**: Widget updates within 50ms
**Test Cases**:
- Single worker addition
- Multiple workers added simultaneously  
- Large log event batch
- Pipeline status changes

#### test_keybinding_response_performance
**Input**: Key press events
**Expected Output**: Actions complete within 100ms
**Test Keys**: All defined keybindings
**Measurement**: Time from key press to action completion

#### test_polling_system_performance
**Input**: All polling systems active
**Expected Output**: No UI blocking, consistent response times
**Monitoring**: UI responsiveness during heavy polling

### Memory Usage Tests

#### test_baseline_memory_usage
**Input**: Freshly started application
**Expected Output**: Baseline memory usage measurement
**Baseline Requirement**: < 50MB initial allocation

#### test_extended_operation_memory_stability
**Input**: Simulated 24-hour operation
**Expected Output**: Memory growth < 1MB/hour
**Test Implementation**: Rapid polling cycles with memory measurement

#### test_state_buffer_memory_management
**Input**: Log events buffer at capacity (1000 entries)
**Expected Output**: Memory usage remains stable
**Verification**: Old entries properly discarded

## Test Utilities and Fixtures

### Common Test Fixtures

```python
@pytest.fixture
async def app_with_mock_state():
    """App with populated mock state for testing."""
    mock_workers = {
        "bead-1": WorkerState(bead_id="bead-1", agent="development", ...),
        "bead-2": WorkerState(bead_id="bead-2", agent="tests", ...)
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
```

### Mock Helper Functions

```python
def async_generator_mock():
    """Create mock async generator for file tailing."""
    async def mock_generator():
        test_lines = [
            "2026-05-20 14:23:01 [INFO] Test log line 1\n",
            "2026-05-20 14:23:02 [INFO] Test log line 2\n"
        ]
        for line in test_lines:
            yield line
            await asyncio.sleep(0.01)
    
    return mock_generator()

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
    # Add other update types as needed
```

## Coverage Requirements

- **Line Coverage**: Minimum 95% for app assembly module
- **Branch Coverage**: Minimum 90% for conditional logic
- **Function Coverage**: 100% for public API methods
- **Integration Coverage**: All widget interactions tested

## Performance Testing Requirements

### Response Time Limits
- App assembly startup: < 2000ms
- State update propagation: < 50ms
- Keybinding response: < 100ms
- Polling operations: < 5000ms timeout

### Memory Usage Limits  
- Initial startup: < 50MB baseline
- Extended operation: < 1MB/hour growth
- State buffer: < 10MB for 1000 log events

### Stress Testing Scenarios
- **Rapid State Updates**: 100+ state changes per second
- **High Log Volume**: 1000+ log entries per minute
- **Extended Operation**: 24+ hour continuous running
- **Resource Constraints**: Limited memory/CPU environments