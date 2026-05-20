# Switchboard TUI Foundation Layer - Test Specifications

## Test Organization

Tests are organized by component following the existing patterns in this codebase:
- Use `pytest` as test framework
- Use `unittest.mock` for mocking external dependencies
- Use `tempfile` for temporary file operations
- Use `pathlib.Path` for path handling
- Import modules using sys.path.insert pattern

## 1. State Dataclasses Tests (test_state.py)

### Test File Structure
```python
"""Tests for TUI state management dataclasses."""

from datetime import datetime
from collections import deque
import pytest
from switchboard.tui.state import (
    WorkerState, StepState, PipelineState, LogEvent, 
    StatsSnapshot, ProjectInfo, SwitchboardState
)
```

### WorkerState Tests

#### test_worker_state_creation
**Input**: Valid field values
**Expected Output**: WorkerState instance with correct attributes
**Edge Cases**: 
- None values for optional fields
- Empty string for title
- Future timestamp for started_at

#### test_worker_state_update
**Input**: Existing WorkerState and update fields
**Expected Output**: Updated WorkerState with modified fields
**Edge Cases**:
- Update with None values
- Update with same values
- Update non-existent fields (should raise AttributeError)

#### test_worker_state_equality
**Input**: Two WorkerState instances
**Expected Output**: Correct equality comparison
**Edge Cases**:
- Identical states should be equal
- Different bead_id should not be equal
- Same data, different object references

### StepState Tests

#### test_step_state_valid_statuses
**Input**: Each valid status value
**Expected Output**: StepState instance
**Valid Statuses**: "open", "in_progress", "closed", "blocked"

#### test_step_state_invalid_status
**Input**: Invalid status values
**Expected Output**: ValueError or validation error
**Invalid Statuses**: "pending", "failed", "unknown", None, 123

#### test_step_state_status_transition
**Input**: StepState with status updates
**Expected Output**: Valid state transitions
**Business Rules**:
- open → in_progress (valid)
- in_progress → closed (valid) 
- closed → in_progress (invalid)
- blocked → any status (valid after unblock)

### PipelineState Tests

#### test_pipeline_state_empty_steps
**Input**: PipelineState with empty steps list
**Expected Output**: Valid PipelineState
**Edge Cases**: Empty list should be allowed

#### test_pipeline_state_steps_ordering
**Input**: Steps list with specific order
**Expected Output**: Maintained order in steps attribute
**Edge Cases**: Duplicate bead_ids in steps

#### test_pipeline_state_add_step
**Input**: PipelineState and new StepState
**Expected Output**: Step added to pipeline
**Edge Cases**:
- Adding duplicate step (update existing)
- Adding step with mismatched project/repo

### LogEvent Tests

#### test_log_event_timestamp_parsing
**Input**: Various timestamp formats
**Expected Output**: Correctly parsed datetime objects
**Formats**:
- ISO format: "2026-05-20T14:23:01"
- Log format: "2026-05-20 14:23:01"
- With timezone: "2026-05-20 14:23:01+00:00"

#### test_log_event_level_validation
**Input**: Log levels
**Expected Output**: Accepted levels
**Valid Levels**: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
**Invalid Levels**: "TRACE", "FATAL", None, 123

#### test_log_event_parsed_event_type_extraction
**Input**: Log messages with event patterns
**Expected Output**: Correct event type classification
**Event Types**:
- "claimed" for "Claimed mol-2hn (agent: development)"
- "completed" for "Completed mol-2hn (agent: development)"
- "failed" for "Failed mol-2hn attempt 1/3"
- "epic_completed" for "Epic completed: epic-xyz"
- "daemon_started" for "Switchboard started"
- None for unrecognized patterns

### SwitchboardState Tests

#### test_switchboard_state_initialization
**Input**: No parameters (default initialization)
**Expected Output**: SwitchboardState with empty collections
**Defaults**:
- workers: empty dict
- pipelines: empty dict  
- projects: empty dict
- stats: default StatsSnapshot
- daemon_online: False
- events: empty deque

#### test_switchboard_state_add_worker
**Input**: SwitchboardState and WorkerState
**Expected Output**: Worker added to workers dict
**Key**: bead_id
**Edge Cases**: 
- Overwrite existing worker
- Add worker with None bead_id

#### test_switchboard_state_remove_worker
**Input**: SwitchboardState and bead_id
**Expected Output**: Worker removed from workers dict
**Edge Cases**:
- Remove non-existent worker (no error)
- Remove from empty workers dict

#### test_switchboard_state_update_stats
**Input**: SwitchboardState and new StatsSnapshot
**Expected Output**: Stats updated
**Edge Cases**: Update with None stats

#### test_switchboard_state_add_log_event
**Input**: SwitchboardState and LogEvent
**Expected Output**: Event added to events deque
**Business Rules**:
- Events added to end of deque
- Deque maintains max 1000 entries
- Oldest events dropped when full

#### test_switchboard_state_reconcile_workers
**Input**: SwitchboardState and list of current workers
**Expected Output**: Workers dict synchronized with current state
**Business Logic**:
- Remove workers not in current list
- Add new workers from current list
- Update existing workers with new data
- Preserve additional state for existing workers

## 2. Log Parser Tests (test_log_parser.py)

### Test File Structure
```python
"""Tests for agent_router log parsing functionality."""

import pytest
from datetime import datetime
from switchboard.tui.polling import parse_log_line
```

### parse_log_line Tests

#### test_parse_log_line_valid_formats
**Input**: Valid log line strings
**Expected Output**: LogEvent objects with correct fields
**Test Cases**:
```python
# Standard format
"2026-05-20 14:23:01 [INFO] Claimed mol-2hn (agent: development, repo: nexus)"
# With milliseconds
"2026-05-20 14:23:01.123 [ERROR] Failed mol-2hn attempt 1/3, requeued"
# Different levels
"2026-05-20 14:23:01 [WARNING] Merge conflict for mol-2hn, creating integrate bead"
```

#### test_parse_log_line_invalid_formats
**Input**: Invalid log line strings
**Expected Output**: None (unparseable)
**Test Cases**:
```python
# Missing timestamp
"[INFO] Some message"
# Invalid timestamp
"not-a-date [INFO] Some message"
# Missing level
"2026-05-20 14:23:01 Some message"
# Empty string
""
# None input
None
```

#### test_parse_claimed_event
**Input**: Log lines with "Claimed" events
**Expected Output**: LogEvent with event_type="claimed"
**Pattern**: `"Claimed {bead_id} (agent: {agent}, repo: {repo})"`
**Test Cases**:
```python
"2026-05-20 14:23:01 [INFO] Claimed mol-2hn (agent: development, repo: nexus)"
"2026-05-20 14:23:01 [INFO] Claimed epic-xyz (project: myapp, tool: pytest, repo: api)"
```

#### test_parse_completed_event
**Input**: Log lines with "Completed" events
**Expected Output**: LogEvent with event_type="completed"
**Pattern**: `"Completed {bead_id} (agent: {agent})"`

#### test_parse_failed_event  
**Input**: Log lines with "Failed" events
**Expected Output**: LogEvent with event_type="failed"
**Pattern**: `"Failed {bead_id} attempt {attempt}/{max_attempts}, requeued"`

#### test_parse_epic_completed_event
**Input**: Log lines with "Epic completed" events
**Expected Output**: LogEvent with event_type="epic_completed"
**Pattern**: `"Epic completed: {epic_id} ({title})"`

#### test_parse_daemon_lifecycle_events
**Input**: Daemon start/stop messages
**Expected Output**: LogEvent with appropriate event_type
**Patterns**:
- `"Switchboard started (poll=10s, max_workers=3, projects=nexus,ui)"` → "daemon_started"
- `"Switchboard stopped"` → "daemon_stopped"

#### test_parse_timezone_handling
**Input**: Log lines with different timezone formats
**Expected Output**: Correctly parsed timestamps
**Edge Cases**:
- UTC timestamps
- Local timezone timestamps
- Missing timezone (assume local)

#### test_parse_malformed_messages
**Input**: Log lines with malformed event patterns
**Expected Output**: LogEvent with event_type=None
**Test Cases**:
- Partial patterns: "Claimed mol-2hn (agent: development)"
- Typos: "Claiimed mol-2hn (agent: development, repo: nexus)"
- Missing parentheses: "Claimed mol-2hn agent: development, repo: nexus"

## 3. bd CLI Wrapper Tests (test_bd_cli_wrappers.py)

### Test File Structure
```python
"""Tests for bd CLI wrapper functions."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import subprocess
from switchboard.tui.polling import bd_json, poll_workers, poll_stats
```

### bd_json Tests

#### test_bd_json_successful_execution
**Input**: Valid bd command
**Expected Output**: Parsed JSON data
**Mock Setup**: subprocess returns valid JSON string
**Test Cases**:
```python
cmd = ["bd", "list", "--json"]
mock_result = '{"beads": [{"id": "mol-2hn", "status": "open"}]}'
```

#### test_bd_json_command_not_found
**Input**: bd command when bd not installed
**Expected Output**: FileNotFoundError or appropriate exception
**Mock Setup**: subprocess.run raises FileNotFoundError

#### test_bd_json_invalid_json_response
**Input**: bd command returning malformed JSON
**Expected Output**: json.JSONDecodeError or wrapped exception
**Mock Setup**: subprocess returns non-JSON string
**Test Cases**:
- Empty string
- Partial JSON: `{"beads": [`
- Invalid syntax: `{beads: []}`

#### test_bd_json_command_failure
**Input**: bd command with non-zero exit code
**Expected Output**: subprocess.CalledProcessError
**Mock Setup**: subprocess.run returns non-zero returncode

#### test_bd_json_timeout_handling
**Input**: bd command that hangs
**Expected Output**: subprocess.TimeoutExpired
**Mock Setup**: subprocess.run with timeout

### poll_workers Tests

#### test_poll_workers_success
**Input**: N/A (no parameters)
**Expected Output**: List of worker dictionaries
**Mock Setup**: bd_json returns workers data
**Expected bd Command**: `["bd", "list", "--status=in_progress", "--json"]`

#### test_poll_workers_empty_result
**Input**: N/A
**Expected Output**: Empty list
**Mock Setup**: bd_json returns empty beads list
**Mock Data**: `{"beads": []}`

#### test_poll_workers_malformed_response
**Input**: N/A
**Expected Output**: Appropriate error handling
**Mock Setup**: bd_json returns unexpected structure
**Test Cases**:
- Missing "beads" key
- "beads" is not a list
- Individual bead missing required fields

#### test_poll_workers_bd_error
**Input**: N/A
**Expected Output**: Exception propagated from bd_json
**Mock Setup**: bd_json raises exception

### poll_stats Tests

#### test_poll_stats_success
**Input**: N/A
**Expected Output**: Stats dictionary
**Mock Setup**: bd_json returns stats data
**Expected bd Command**: `["bd", "stats", "--json"]`
**Expected Fields**: completed, failed, blocked, total

#### test_poll_stats_missing_fields
**Input**: N/A
**Expected Output**: Default values for missing fields
**Mock Setup**: bd_json returns partial stats
**Default Values**: 0 for all numeric fields

#### test_poll_stats_invalid_types
**Input**: N/A
**Expected Output**: Type conversion or error handling
**Mock Setup**: bd_json returns string numbers
**Test Cases**: `{"completed": "5", "failed": "0"}`

## 4. File Tailer Tests (test_file_tailer.py)

### Test File Structure  
```python
"""Tests for file tailing functionality."""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, mock_open
from switchboard.tui.polling import tail_file
```

### tail_file Tests

#### test_tail_file_existing_file
**Input**: Path to existing file
**Expected Output**: Async iterator yielding file lines
**Test Setup**: 
- Create temporary file with content
- Read lines and verify output
**Edge Cases**: Empty file, single line, multiple lines

#### test_tail_file_new_lines_appended
**Input**: File that gets new content during tailing
**Expected Output**: New lines yielded as they're added
**Test Setup**:
- Start tailing file
- Append new lines to file
- Verify new lines are yielded

#### test_tail_file_nonexistent_file_waits
**Input**: Path to non-existent file
**Expected Output**: Wait for file creation, then start tailing
**Test Setup**:
- Start tailing non-existent file
- Create file after delay
- Verify tailing begins after creation

#### test_tail_file_file_rotation
**Input**: File that gets rotated/replaced
**Expected Output**: Resume tailing new file
**Test Setup**:
- Start tailing file
- Replace/rotate file 
- Verify tailing continues with new file

#### test_tail_file_permission_error
**Input**: File with no read permissions
**Expected Output**: Appropriate error handling
**Test Setup**: Create file, remove read permissions

#### test_tail_file_file_deletion
**Input**: File that gets deleted during tailing
**Expected Output**: Handle gracefully, resume if recreated
**Test Setup**:
- Start tailing file
- Delete file
- Recreate file
- Verify resumption

#### test_tail_file_large_file_performance
**Input**: Large file (>1MB)
**Expected Output**: Efficient tailing without memory issues
**Performance Requirements**:
- Memory usage stays constant
- No reading entire file into memory
- Start from end of existing file

#### test_tail_file_binary_content
**Input**: File with binary content
**Expected Output**: Appropriate handling (skip or error)
**Test Setup**: File with mixed text/binary content

#### test_tail_file_concurrent_writers
**Input**: File being written by multiple processes
**Expected Output**: All lines captured correctly
**Test Setup**: Simulate concurrent file writes

## 5. App Shell Tests (test_app_shell.py)

### Test File Structure
```python
"""Tests for Textual application shell."""

import pytest
from unittest.mock import patch, MagicMock
from textual.testing import AppTester
from switchboard.tui.app import SwitchboardApp
```

### SwitchboardApp Tests

#### test_app_initialization
**Input**: SwitchboardApp()
**Expected Output**: App instance with correct configuration
**Verification**:
- CSS file loaded correctly
- Initial state properly set
- Required widgets instantiated

#### test_app_css_loading
**Input**: App with switchboard.tcss file
**Expected Output**: Styles applied correctly  
**Test Setup**: Mock CSS file existence and content
**Verification**: CSS rules loaded and applied

#### test_app_css_missing_file
**Input**: App when switchboard.tcss doesn't exist
**Expected Output**: Graceful fallback to default styles
**Test Setup**: Mock file not found

#### test_app_quit_key_handler
**Input**: 'Q' key press event
**Expected Output**: Application exits cleanly
**Test Setup**: Use Textual AppTester
**Verification**: App.exit() called

#### test_app_quit_key_case_insensitive
**Input**: 'q' and 'Q' key presses
**Expected Output**: Both trigger quit
**Test Cases**: lowercase and uppercase

#### test_app_other_key_handlers
**Input**: Other key press events
**Expected Output**: Keys handled appropriately or ignored
**Test Cases**: 
- Valid navigation keys
- Invalid/unmapped keys
- Control characters

#### test_app_mount_unmount_lifecycle
**Input**: App startup and shutdown
**Expected Output**: Clean mount/unmount cycle
**Verification**:
- All widgets mounted on startup
- Resources cleaned up on shutdown
- No leaked event handlers

#### test_app_error_handling
**Input**: Exceptions during app lifecycle
**Expected Output**: Graceful error handling and display
**Test Cases**:
- Widget creation failures
- CSS parsing errors
- Resource initialization failures

#### test_app_terminal_resize
**Input**: Terminal resize events
**Expected Output**: App layout adjusts correctly
**Test Setup**: Simulate terminal size changes
**Verification**: Widget sizes recalculated

#### test_app_theme_colors
**Input**: App with loaded CSS theme
**Expected Output**: Amber CRT color palette applied
**Verification**: 
- Background colors are dark/black
- Text colors are amber/yellow
- Accent colors follow CRT aesthetic

## 6. CLI Entry Point Tests (test_cli_entry.py)

### Test File Structure
```python
"""Tests for CLI entry point and argument parsing."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path
from switchboard.tui import cli, __main__
```

### CLI Argument Parsing Tests

#### test_cli_default_arguments
**Input**: No command line arguments
**Expected Output**: Default values applied
**Defaults**:
- artifacts_dir: "artifacts/"
- poll_interval: 10

#### test_cli_artifacts_dir_argument
**Input**: --artifacts-dir /custom/path
**Expected Output**: artifacts_dir set to "/custom/path"
**Test Cases**:
- Absolute paths
- Relative paths  
- Non-existent directories (should create)

#### test_cli_poll_interval_argument
**Input**: --poll-interval 30
**Expected Output**: poll_interval set to 30
**Test Cases**:
- Valid integers: 5, 10, 60
- Invalid values: 0, -1, "abc"
- Edge cases: very large numbers

#### test_cli_help_argument
**Input**: --help or -h
**Expected Output**: Help text displayed and exit
**Verification**: Help contains usage information

#### test_cli_invalid_arguments
**Input**: Invalid command line arguments
**Expected Output**: Error message and exit code
**Test Cases**:
- Unknown arguments: --invalid
- Malformed values: --poll-interval abc
- Missing required values

#### test_cli_artifacts_dir_creation
**Input**: --artifacts-dir pointing to non-existent directory
**Expected Output**: Directory created if parent exists
**Test Cases**:
- Parent exists: should create
- Parent doesn't exist: should error or create recursively

#### test_cli_artifacts_dir_permissions
**Input**: --artifacts-dir with permission restrictions
**Expected Output**: Appropriate error handling
**Test Cases**:
- Read-only parent directory
- No write permissions

### Python Module Invocation Tests

#### test_main_module_execution
**Input**: python -m switchboard.tui
**Expected Output**: App launches with default arguments
**Test Setup**: Mock app execution

#### test_main_module_with_arguments
**Input**: python -m switchboard.tui --poll-interval 5
**Expected Output**: App launches with specified arguments
**Verification**: Arguments passed correctly to app

#### test_main_module_import_error
**Input**: Module import fails
**Expected Output**: Clear error message
**Test Setup**: Mock import failure

#### test_main_module_keyboard_interrupt
**Input**: Ctrl+C during execution
**Expected Output**: Clean exit without stack trace
**Test Setup**: Mock KeyboardInterrupt

### Integration Tests

#### test_cli_to_app_integration
**Input**: Complete CLI invocation
**Expected Output**: App starts with correct configuration
**Test Flow**:
1. Parse CLI arguments
2. Validate arguments  
3. Initialize app with arguments
4. Start app main loop

#### test_cli_error_exit_codes
**Input**: Various error conditions
**Expected Output**: Appropriate exit codes
**Exit Codes**:
- 0: Success
- 1: General error
- 2: Invalid arguments
- 130: KeyboardInterrupt

## Test Utilities and Fixtures

### Common Test Fixtures

```python
@pytest.fixture
def temp_artifacts_dir():
    """Temporary directory for artifacts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def sample_log_lines():
    """Sample log lines for parser testing."""
    return [
        "2026-05-20 14:23:01 [INFO] Switchboard started (poll=10s, max_workers=3)",
        "2026-05-20 14:23:02 [INFO] Claimed mol-2hn (agent: development, repo: nexus)",
        "2026-05-20 14:23:10 [INFO] Completed mol-2hn (agent: development)",
        "2026-05-20 14:23:15 [ERROR] Failed mol-abc attempt 1/3, requeued",
        "2026-05-20 14:23:20 [INFO] Epic completed: epic-xyz (Add user authentication)",
    ]

@pytest.fixture
def mock_bd_command():
    """Mock bd command execution."""
    with patch('subprocess.run') as mock_run:
        yield mock_run

@pytest.fixture
def sample_worker_data():
    """Sample worker data for testing."""
    return {
        "bead_id": "mol-2hn",
        "agent": "development", 
        "repo": "nexus",
        "tool": None,
        "pid": 12345,
        "started_at": "2026-05-20T14:23:01",
        "title": "Implement user authentication",
        "epic_id": "epic-xyz"
    }
```

### Mock Helper Functions

```python
def create_mock_log_file(content_lines):
    """Create temporary log file with specified content."""
    # Implementation for creating mock log files

def mock_bd_json_response(data):
    """Create mock bd command JSON response.""" 
    # Implementation for mocking bd command responses

async def async_test_helper(coro):
    """Helper for testing async functions."""
    # Implementation for async test utilities
```

## Coverage Requirements

- **Line Coverage**: Minimum 90% for all modules
- **Branch Coverage**: Minimum 85% for conditional logic  
- **Function Coverage**: 100% for public API functions

## Performance Testing

### Response Time Requirements
- Log parsing: < 1ms per line
- State updates: < 10ms per update
- CLI command execution: < 5s timeout
- File tailing: < 100ms latency for new lines

### Memory Usage Requirements  
- Application startup: < 50MB base memory
- Long-running session: < 100MB after 24 hours
- Log event buffer: Max 1000 events in memory

### Stress Testing Scenarios
- **High Log Volume**: 1000+ log lines per second
- **Many Workers**: 50+ concurrent workers  
- **Large Files**: Tailing files > 100MB
- **Extended Runtime**: 48+ hour sessions