# Signature Widget Test Specifications

## Overview

This document defines test-first specifications for the two signature Switchboard TUI widgets:
- **PatchPanel**: Visual pipeline status display 
- **PartyLine**: Log display with source switching

These widgets build upon the foundation state management system defined in `switchboard/tui/state.py` and use the polling infrastructure in `switchboard/tui/polling.py`.

## Test Organization

- Use `pytest` as test framework
- Use `unittest.mock` for mocking external dependencies  
- Use `textual.testing.AppTester` for widget testing
- Mock the state management layer for consistent test data
- Test widgets in isolation from data polling

## 1. PatchPanel Widget Tests (test_patch_panel.py)

### Test File Structure

```python
"""Tests for PatchPanel signature widget."""

import pytest
from unittest.mock import MagicMock, patch
from textual.testing import AppTester
from switchboard.tui.widgets.patch_panel import PatchPanel
from switchboard.tui.state import (
    PipelineState, StepState, SwitchboardState, WorkerState
)
```

### Widget Initialization Tests

#### test_patch_panel_creation
**Input**: PatchPanel() constructor
**Expected Output**: Widget instance with correct initial state
**Verification**:
- Widget has correct CSS classes
- Internal state containers initialized
- No pipelines displayed initially

#### test_patch_panel_empty_state_display
**Input**: PatchPanel with empty SwitchboardState
**Expected Output**: Empty state message displayed
**Visual Requirements**:
- Shows "No active pipelines" or similar message
- Center-aligned placeholder text
- Consistent with overall TUI theme

#### test_patch_panel_css_classes_applied
**Input**: PatchPanel widget in rendered state  
**Expected Output**: Correct CSS classes applied
**Expected Classes**:
- `patch-panel` (main container)
- `pipeline-row` (for each pipeline)
- `step-box` (for each step)
- `signal-lamp` (for status indicators)
- `cord-pair` (for active step connectors)

### Single Pipeline Rendering Tests

#### test_single_pipeline_basic_layout
**Input**: SwitchboardState with one pipeline containing 5 steps
**Expected Output**: Single horizontal row of step boxes
**Test Data**:
```python
pipeline = PipelineState(
    epic_id="mol-2hn",
    title="Add user authentication", 
    project="nexus",
    repo="api",
    steps=[
        StepState("tdd-001", "tdd", "closed"),
        StepState("test-001", "tests", "closed"), 
        StepState("dev-001", "development", "in_progress"),
        StepState("verify-001", "verify", "open"),
        StepState("review-001", "review", "open")
    ]
)
```
**Verification**:
- 5 step boxes rendered horizontally
- Pipeline title shows: "nexus / api  #mol-2hn"
- Progress counter shows: "2/5 done"

#### test_pipeline_step_status_indicators
**Input**: Pipeline with various step statuses
**Expected Output**: Correct signal lamps for each status
**Status Mappings**:
- `open` → `( )` (empty parentheses)
- `in_progress` → `(*)` (asterisk in parentheses)  
- `closed` → `(✓)` (checkmark in parentheses)
- `blocked` → `(✗)` (X in parentheses)

#### test_pipeline_step_labels
**Input**: Pipeline with standard step sequence
**Expected Output**: Correct abbreviated step labels
**Label Mappings**:
- `tdd` → "TDD"
- `tests` → "TEST"  
- `development` → "DEV"
- `verify` → "VRFY" 
- `review` → "REVW"
- `integrate` → "INTG"

#### test_active_step_cord_pair_display
**Input**: Pipeline with one step in "in_progress" status and active worker
**Expected Output**: Cord pair connector with tool name and elapsed time
**Test Data**:
```python
worker = WorkerState(
    bead_id="dev-001",
    agent="development",
    repo="api", 
    tool="claude",
    pid=12345,
    started_at="2026-05-20T14:23:01",
    title="Implement authentication",
    epic_id="mol-2hn"
)
```
**Expected Display**:
```
┌──────┬──────┬──────┬──────┬──────┐
│ TDD  │ TEST │ DEV  │ VRFY │ REVW │
│ (✓)  │ (✓)  │ (*)  │ ( )  │ ( )  │
└──────┴──────┴──┬───┴──────┴──────┘
                 └── claude · 12m 34s
```

#### test_progress_counter_accuracy
**Input**: Pipelines with various completion states
**Expected Output**: Accurate N/M done counters
**Test Cases**:
- 0/5 done (all open)
- 2/5 done (2 closed, 3 open/in_progress)
- 5/5 done (all closed)
- 3/7 done (mixed larger pipeline)

### Multiple Pipeline Rendering Tests  

#### test_multiple_pipelines_vertical_layout
**Input**: SwitchboardState with 3 different pipelines
**Expected Output**: 3 pipeline rows stacked vertically
**Test Data**: 3 pipelines from different projects with different progress
**Verification**:
- Each pipeline rendered as separate row
- Consistent horizontal alignment
- Proper vertical spacing between rows
- No overlap between pipeline displays

#### test_pipeline_sorting_order
**Input**: Multiple pipelines with different start times
**Expected Output**: Pipelines sorted by epic_id or creation time
**Verification**:
- Consistent ordering across updates
- New pipelines appear in correct position
- Epic completion doesn't disrupt order

#### test_many_pipelines_scrolling
**Input**: 20+ pipelines in SwitchboardState
**Expected Output**: Scrollable display with all pipelines accessible
**Verification**:
- Vertical scrollbar appears when needed
- All pipelines accessible via scrolling
- Keyboard navigation works (up/down arrows)
- Page up/down navigation works

### Dynamic State Update Tests

#### test_pipeline_step_status_updates
**Input**: State update changing step status from "open" to "in_progress"
**Expected Output**: Signal lamp updates immediately
**Test Flow**:
1. Render pipeline with step in "open" status `( )`
2. Update state with step in "in_progress" status 
3. Verify signal lamp changes to `(*)`
4. No full re-render, just lamp updates

#### test_active_worker_cord_pair_updates  
**Input**: Worker starts/stops, elapsed time changes
**Expected Output**: Cord pair appears/disappears, timer updates
**Test Cases**:
- Worker starts → cord pair appears with "0m 01s"
- Timer increments → "12m 34s"  
- Worker completes → cord pair disappears
- Worker fails → cord pair shows error state

#### test_pipeline_addition_removal
**Input**: Add/remove entire pipelines from state
**Expected Output**: Rows added/removed from display
**Test Flow**:
1. Start with 2 pipelines
2. Add 3rd pipeline → new row appears
3. Remove 1st pipeline → row disappears  
4. Remaining pipelines maintain correct positions

#### test_progress_counter_real_time_updates
**Input**: Steps complete in sequence over time
**Expected Output**: Progress counter updates: 1/5, 2/5, 3/5, etc.
**Verification**:
- Counter accuracy maintained
- Updates happen immediately on state change
- No intermediate flicker or incorrect values

### Edge Cases and Error Handling Tests

#### test_pipeline_with_missing_steps
**Input**: PipelineState with empty steps list
**Expected Output**: Graceful handling, placeholder display
**Expected Display**: Pipeline title with "No steps defined" or similar

#### test_pipeline_with_invalid_step_status
**Input**: StepState with unrecognized status value
**Expected Output**: Default signal lamp or error indicator
**Fallback Display**: `(?)` for unknown status

#### test_very_long_pipeline_title
**Input**: Pipeline with extremely long title (>100 chars)
**Expected Output**: Title truncation with ellipsis
**Expected Format**: "very-long-project / very-long-repo  #epic-id..."

#### test_step_without_matching_worker
**Input**: Step in "in_progress" status but no worker in state
**Expected Output**: Signal lamp shows (*) but no cord pair
**Verification**: Handles state inconsistency gracefully

#### test_worker_without_matching_step
**Input**: Worker in state but no corresponding step
**Expected Output**: Worker ignored for display purposes
**Verification**: No orphan cord pairs or display artifacts

### Performance and Memory Tests

#### test_large_pipeline_rendering_performance
**Input**: Pipeline with 50+ steps
**Expected Output**: Renders within performance bounds (<100ms)
**Verification**:
- No significant performance degradation
- Memory usage remains reasonable
- Horizontal scrolling works smoothly

#### test_frequent_state_updates_performance
**Input**: Rapid state updates (10/second) for 1 minute
**Expected Output**: UI remains responsive throughout
**Verification**:
- No memory leaks
- No accumulating lag
- Consistent render times

## 2. PartyLine Widget Tests (test_party_line.py)

### Test File Structure

```python
"""Tests for PartyLine signature widget."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from textual.testing import AppTester
from switchboard.tui.widgets.party_line import PartyLine
from switchboard.tui.state import LogEvent
```

### Widget Initialization Tests

#### test_party_line_creation
**Input**: PartyLine() constructor
**Expected Output**: Widget instance with correct initial state
**Verification**:
- Default source set to "DAEMON LOG"
- Empty log entry list
- Source indicator header displayed
- Auto-scroll enabled

#### test_party_line_empty_state_display
**Input**: PartyLine with no log events
**Expected Output**: Empty log display with header
**Expected Display**:
```
[DAEMON LOG] ────────────────────────────────
(empty - waiting for events)
```

### Log Entry Display Tests

#### test_basic_log_entry_rendering
**Input**: Single LogEvent
**Expected Output**: Formatted log entry with timestamp
**Test Data**:
```python
event = LogEvent(
    timestamp="2026-05-20 14:23:01",
    level="INFO", 
    message="Switchboard started (poll=10s, max_workers=3)",
    parsed_event_type="daemon_started"
)
```
**Expected Display**:
```
14:23:01  DAEMON ONLINE
```

#### test_multiple_log_entries_chronological_order
**Input**: List of LogEvents with different timestamps
**Expected Output**: Entries displayed in chronological order
**Verification**:
- Oldest entries at top
- Newest entries at bottom  
- Timestamps correctly parsed and sorted
- Auto-scroll to newest entry

#### test_log_entry_timestamp_formatting
**Input**: LogEvents with various timestamp formats
**Expected Output**: Consistent HH:MM:SS format display
**Test Cases**:
- ISO format: "2026-05-20T14:23:01" → "14:23:01"
- Log format: "2026-05-20 14:23:01.123" → "14:23:01"
- With timezone: "2026-05-20 14:23:01+00:00" → "14:23:01"

### Operator Jargon Translation Tests

#### test_claimed_event_translation
**Input**: LogEvent with "claimed" parsed_event_type
**Expected Output**: Operator jargon translation
**Test Data**: `"Claimed mol-2hn (agent: development, repo: nexus)"`
**Expected Display**: `"14:23:01  CONNECTING mol-2hn"`

#### test_launched_event_translation  
**Input**: LogEvent indicating worker launched
**Expected Output**: Line connection announcement
**Test Data**: Worker appears in state with new PID
**Expected Display**: `"14:23:02  LINE 1 CONNECTED (mol-2hn development)"`

#### test_completed_event_translation
**Input**: LogEvent with "completed" parsed_event_type  
**Expected Output**: Line clear announcement
**Test Data**: `"Completed mol-2hn (agent: development)"`
**Expected Display**: `"14:23:15  LINE CLEAR ✓ (mol-2hn)"`

#### test_failed_event_translation
**Input**: LogEvent with "failed" parsed_event_type
**Expected Output**: Dropped call with retry info
**Test Data**: `"Failed mol-2hn attempt 1/3, requeued"`
**Expected Display**: `"14:23:20  DROPPED CALL · REDIALING (1/3) mol-2hn"`

#### test_merge_conflict_event_translation
**Input**: LogEvent about merge conflict
**Expected Output**: Routing to supervisor message  
**Test Data**: `"Merge conflict for mol-2hn, creating integrate bead"`
**Expected Display**: `"14:23:25  ROUTING TO SUPERVISOR (mol-2hn conflict)"`

#### test_epic_completed_event_translation
**Input**: LogEvent with "epic_completed" parsed_event_type
**Expected Output**: Call complete announcement
**Test Data**: `"Epic completed: epic-xyz (Add user authentication)"`
**Expected Display**: `"14:23:30  CALL COMPLETE ✓ (epic-xyz)"`

#### test_unrecognized_event_passthrough
**Input**: LogEvent with no parsed_event_type (None)
**Expected Output**: Original message displayed with timestamp
**Test Data**: `"Some unrecognized log message"`
**Expected Display**: `"14:23:01  Some unrecognized log message"`

### Source Switching Tests

#### test_default_daemon_log_source
**Input**: PartyLine initialized with daemon events
**Expected Output**: Header shows [DAEMON LOG]
**Verification**:
- Header displays current source
- Daemon events are shown
- Worker events are filtered out

#### test_switch_to_worker_source
**Input**: Switch to specific worker output (key press 1-9)
**Expected Output**: Header changes to [WORKER N: bead-id agent]
**Test Flow**:
1. Start with daemon log display
2. Press '1' key
3. Header changes to "[WORKER 1: mol-2hn development]"
4. Only worker stdout/stderr shown
5. Daemon events filtered out

#### test_worker_source_header_format
**Input**: Switch to worker with specific bead and agent
**Expected Output**: Correctly formatted worker header
**Test Data**: Worker with bead_id="mol-abc", agent="tests"  
**Expected Header**: `"[WORKER 1: mol-abc tests]"`

#### test_switch_between_multiple_workers
**Input**: Multiple workers active, switch between them
**Expected Output**: Headers and content update correctly
**Test Flow**:
1. Worker 1: mol-2hn development
2. Worker 2: epic-xyz tests  
3. Press '1' → "[WORKER 1: mol-2hn development]"
4. Press '2' → "[WORKER 2: epic-xyz tests]"
5. Content filters correctly for each worker

#### test_switch_back_to_daemon_log
**Input**: Switch from worker source back to daemon
**Expected Output**: Daemon events displayed again
**Test Flow**:
1. Viewing worker output
2. Press '0' or 'D' key
3. Header returns to "[DAEMON LOG]"
4. Daemon events displayed, worker output filtered

#### test_switch_to_nonexistent_worker
**Input**: Press key for worker number that doesn't exist
**Expected Output**: No source change, error indication optional
**Test Cases**:
- Press '5' when only 3 workers exist
- Press '1' when no workers exist
- Headers remain unchanged

### Auto-scroll and Navigation Tests

#### test_auto_scroll_new_entries
**Input**: New LogEvents added while viewing bottom of log
**Expected Output**: Automatically scroll to show new entries
**Test Flow**:
1. Display full screen of log entries
2. Add new LogEvent to state
3. Verify scroll position moves to show new entry
4. Newest entry remains visible

#### test_manual_scroll_disables_auto_scroll
**Input**: User scrolls up manually, then new entries arrive
**Expected Output**: Auto-scroll pauses, user maintains position
**Test Flow**:
1. Display full screen of log entries  
2. User scrolls up 10 lines
3. New LogEvents arrive
4. Scroll position unchanged (user stays at current position)
5. New entries added but not visible

#### test_scroll_to_bottom_resumes_auto_scroll
**Input**: User scrolls back to bottom after manual scrolling
**Expected Output**: Auto-scroll resumes for new entries
**Test Flow**:
1. User has scrolled up (auto-scroll disabled)
2. User scrolls back to bottom
3. New LogEvent arrives
4. Auto-scroll resumes, new entry shown

#### test_keyboard_navigation
**Input**: Arrow key presses for navigation
**Expected Output**: Correct scroll behavior
**Test Cases**:
- Up arrow scrolls up one line
- Down arrow scrolls down one line
- Page Up scrolls up one screen
- Page Down scrolls down one screen
- Home key jumps to top
- End key jumps to bottom (resumes auto-scroll)

### Log Buffer Management Tests

#### test_log_entry_buffer_size_limit
**Input**: More than 1000 LogEvents over time
**Expected Output**: Oldest entries removed, buffer size maintained
**Verification**:
- Buffer never exceeds 1000 entries
- Oldest entries removed first (FIFO)
- Display updates to show current buffer contents
- No memory accumulation

#### test_high_volume_log_processing
**Input**: Rapid influx of LogEvents (100/second for 30 seconds)
**Expected Output**: UI remains responsive, buffer managed correctly
**Verification**:
- No UI freezing or lag
- Memory usage stable
- Recent events always visible
- Older events properly evicted

### Error Handling and Edge Cases Tests

#### test_malformed_log_event_handling
**Input**: LogEvent with invalid timestamp or missing fields
**Expected Output**: Graceful handling, error entry displayed
**Test Cases**:
- LogEvent with None timestamp
- LogEvent with unparseable timestamp
- LogEvent with empty message
- Expected fallback: "??:??:??  [ERROR] Malformed log entry"

#### test_very_long_log_messages
**Input**: LogEvent with extremely long message (>500 chars)
**Expected Output**: Message word-wrapped or truncated appropriately
**Verification**:
- No horizontal scrolling required
- Text fits within widget bounds
- Readability maintained

#### test_special_characters_in_log_messages
**Input**: LogEvents with special characters, Unicode, ANSI codes
**Expected Output**: Characters displayed correctly or safely filtered
**Test Cases**:
- Unicode emojis: "✓ ✗ ★"
- ANSI color codes: "\033[31mERROR\033[0m"  
- Control characters: tabs, newlines
- Expected: Safe display without breaking layout

#### test_empty_log_source_switching
**Input**: Switch to worker that has no log entries
**Expected Output**: Empty source display with appropriate message
**Expected Display**:
```
[WORKER 1: mol-2hn development] ──────────────
(no output from this worker)
```

### Performance Tests

#### test_large_log_buffer_scroll_performance
**Input**: Full buffer (1000 entries), rapid scrolling
**Expected Output**: Smooth scrolling performance
**Verification**:
- Scroll operations complete within 50ms
- No frame drops or stuttering
- Memory usage remains constant during scrolling

#### test_rapid_source_switching_performance  
**Input**: Rapidly switch between sources (daemon, worker1, worker2...)
**Expected Output**: Source changes happen immediately
**Verification**:
- Source switches complete within 100ms
- No lag in header updates
- Content filters apply immediately

## Common Test Fixtures

### State Fixtures

```python
@pytest.fixture
def sample_pipeline_state():
    """Sample pipeline with all step types."""
    return PipelineState(
        epic_id="mol-2hn",
        title="Add user authentication",
        project="nexus", 
        repo="api",
        steps=[
            StepState("tdd-001", "tdd", "closed"),
            StepState("test-001", "tests", "closed"),
            StepState("dev-001", "development", "in_progress"), 
            StepState("verify-001", "verify", "open"),
            StepState("review-001", "review", "open")
        ]
    )

@pytest.fixture  
def sample_worker_state():
    """Sample active worker."""
    return WorkerState(
        bead_id="dev-001",
        agent="development",
        repo="api",
        tool="claude", 
        pid=12345,
        started_at="2026-05-20T14:23:01",
        title="Implement authentication", 
        epic_id="mol-2hn"
    )

@pytest.fixture
def sample_log_events():
    """Sample log events for testing."""
    return [
        LogEvent(
            timestamp="2026-05-20 14:23:01",
            level="INFO",
            message="Switchboard started (poll=10s, max_workers=3)",
            parsed_event_type="daemon_started"
        ),
        LogEvent(
            timestamp="2026-05-20 14:23:02", 
            level="INFO",
            message="Claimed mol-2hn (agent: development, repo: nexus)",
            parsed_event_type="claimed"
        ),
        LogEvent(
            timestamp="2026-05-20 14:23:15",
            level="INFO", 
            message="Completed mol-2hn (agent: development)",
            parsed_event_type="completed"
        ),
        LogEvent(
            timestamp="2026-05-20 14:23:20",
            level="ERROR",
            message="Failed mol-abc attempt 1/3, requeued", 
            parsed_event_type="failed"
        ),
    ]
```

### Mock Helpers

```python
@pytest.fixture
def mock_switchboard_state():
    """Mock SwitchboardState with test data."""
    state = MagicMock(spec=SwitchboardState)
    state.pipelines = {}
    state.workers = {}
    state.events = []
    return state

def create_multi_pipeline_state(count=3):
    """Helper to create state with multiple pipelines."""
    # Implementation for creating test states with multiple pipelines
    
async def simulate_log_stream(widget, events, delay=0.1):
    """Helper to simulate real-time log events.""" 
    # Implementation for simulating streaming log events
```

## Coverage and Performance Requirements

### Coverage Targets
- **Line Coverage**: 95% for all widget code
- **Branch Coverage**: 90% for conditional logic  
- **Function Coverage**: 100% for public widget methods

### Performance Requirements
- **Widget Rendering**: < 100ms for initial render
- **State Updates**: < 50ms for state change response
- **Scroll Operations**: < 50ms for smooth scrolling
- **Memory Usage**: < 10MB for widget instances with full data

### Stress Testing
- **Large State**: 50+ pipelines, 100+ workers
- **High Frequency Updates**: 100 state changes/second for 1 minute
- **Extended Runtime**: 8+ hours continuous operation
- **Log Volume**: 10,000+ log entries with rapid additions

## Integration Test Scenarios

### Widget Integration Tests
- PatchPanel + PartyLine in same app layout
- State changes affecting both widgets simultaneously
- Cross-widget interaction (selecting pipeline affects logs)
- Resource sharing and cleanup

### Real Data Integration Tests  
- Connect to live agent_router daemon
- Process real log files
- Handle actual bd CLI output
- End-to-end workflow visualization