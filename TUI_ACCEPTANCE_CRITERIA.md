# Switchboard TUI Foundation Layer - Acceptance Criteria

## Overview
The Switchboard TUI provides a read-only interactive terminal interface for observing the switchboard agent_router daemon. Built with Textual, it displays real-time status of agent pipelines, worker processes, and system health.

## Functional Requirements

### 1. State Management (state.py)
- **WorkerState dataclass** must track active worker processes with fields:
  - bead_id: Unique identifier for the bead being processed
  - agent: Agent type (e.g., "development", "tests", "review")
  - repo: Repository name within the project
  - tool: Tool name for pipeline tool steps
  - pid: Process ID of the worker
  - started_at: Timestamp when worker launched
  - title: Human-readable description of the work
  - epic_id: Parent epic identifier for grouping

- **StepState dataclass** must represent individual pipeline steps with fields:
  - bead_id: Unique identifier
  - agent: Agent type
  - status: One of "open", "in_progress", "closed", "blocked"

- **PipelineState dataclass** must represent complete workflows with fields:
  - epic_id: Unique identifier for the pipeline
  - title: Human-readable description
  - project: Project name
  - repo: Repository name
  - steps: List of StepState objects

- **LogEvent dataclass** must represent parsed log entries with fields:
  - timestamp: When the event occurred
  - level: Log level (INFO, WARNING, ERROR)
  - message: Original log message
  - parsed_event_type: Structured event type

- **StatsSnapshot dataclass** must track system metrics with fields:
  - completed_today: Number of beads completed today
  - failed_today: Number of beads failed today
  - blocked_count: Number of currently blocked beads

- **ProjectInfo dataclass** must track project metadata with fields:
  - name: Project name
  - path: Filesystem path
  - active_lines: Number of active workers/pipelines

- **SwitchboardState dataclass** must be the root state container with fields:
  - workers: Dict mapping bead_id to WorkerState
  - pipelines: Dict mapping epic_id to PipelineState
  - projects: Dict mapping project_name to ProjectInfo
  - stats: StatsSnapshot instance
  - daemon_online: Boolean indicating if agent_router is running
  - events: Deque of recent LogEvent objects (max 1000 entries)

- All dataclasses must support update/reconcile methods for state synchronization

### 2. Log Parser (polling.py)
- **parse_log_line(line) → LogEvent | None** function must:
  - Parse agent_router.log format: `2026-05-20 14:23:01 [INFO] message`
  - Extract timestamp, level, and message
  - Return None for unparseable lines
  - Handle malformed timestamps gracefully

- Must recognize and parse these event types:
  - **Claimed**: `"Claimed mol-2hn (agent: development, repo: nexus)"`
  - **Launched**: Implicit from worker PID tracking
  - **Completed**: `"Completed mol-2hn (agent: development)"`
  - **Failed**: `"Failed mol-2hn attempt 1/3, requeued"`
  - **Merge conflict**: `"Merge conflict for mol-2hn, creating integrate bead"`
  - **Epic auto-closed**: `"Epic completed: epic-xyz (Feature title)"`
  - **Agent Router lifecycle**: `"Switchboard started"`, `"Switchboard stopped"`

### 3. bd CLI Wrappers (polling.py)
- **async bd_json(cmd)** function must:
  - Execute bd CLI commands asynchronously
  - Parse JSON output safely
  - Handle subprocess errors gracefully
  - Return structured data or raise appropriate exceptions

- **async poll_workers()** function must:
  - Execute `bd list --status=in_progress --json`
  - Return list of active worker bead data
  - Handle empty results (no active workers)

- **async poll_stats()** function must:
  - Execute `bd stats --json`
  - Return statistics about bead system
  - Include completed/failed counts and blocked status

- Error handling requirements:
  - Handle `bd` command not found in PATH
  - Handle invalid/malformed JSON responses
  - Handle network/filesystem errors
  - Handle timeout scenarios

### 4. File Tailer (polling.py)
- **async tail_file(path)** async generator must:
  - Yield new lines from log file as they appear
  - Handle log file not existing initially (daemon not started)
  - Handle log rotation/truncation gracefully
  - Resume tailing after temporary file unavailability
  - Use efficient file watching (not polling)

### 5. App Shell (app.py)
- **SwitchboardApp** Textual application must:
  - Load `switchboard.tcss` theme file
  - Respond to 'Q' key to quit application
  - Mount UI components cleanly on startup
  - Unmount and cleanup resources on shutdown
  - Handle terminal resize gracefully
  - Display appropriate error messages for initialization failures

### 6. CLI Entry Point (cli.py, __main__.py)
- Command line interface must accept:
  - `--artifacts-dir` option (default: "artifacts/")
  - `--poll-interval` option (default: 10 seconds)
  - `--help` to display usage information

- **python -m switchboard.tui** must launch the application
- Must validate command line arguments
- Must display helpful error messages for invalid arguments

### 7. Theme System (switchboard.tcss)
- Must define amber CRT color palette suitable for terminal display
- Must provide consistent styling for all UI components
- Must ensure good contrast and readability
- Must support both light and dark terminal backgrounds

## Non-Functional Requirements

### Performance
- Initial startup must complete within 2 seconds
- UI updates must be responsive (< 100ms for state changes)
- Memory usage must remain stable during long-running sessions
- File tailing must not block UI updates

### Reliability
- Must handle daemon restarts gracefully
- Must recover from temporary filesystem errors
- Must handle malformed log entries without crashing
- Must maintain state consistency during rapid updates

### Usability
- Must display clear status indicators
- Must provide meaningful error messages
- Must support standard terminal operations (resize, scroll)
- Must exit cleanly with Ctrl+C or Q key

## Acceptance Tests

### State Management Tests
- ✅ All dataclasses instantiate with correct types
- ✅ Update methods modify state correctly
- ✅ State serialization/deserialization works
- ✅ Concurrent updates don't corrupt state

### Log Parser Tests
- ✅ Parses valid log lines correctly
- ✅ Returns None for invalid lines
- ✅ Extracts all required event types
- ✅ Handles timezone variations

### CLI Wrapper Tests
- ✅ bd_json executes commands and parses output
- ✅ Error handling for missing bd command
- ✅ Error handling for malformed JSON
- ✅ poll_workers returns structured data
- ✅ poll_stats returns metrics

### File Tailer Tests
- ✅ Tails existing file correctly
- ✅ Waits for non-existent file creation
- ✅ Handles file rotation
- ✅ Resumes after temporary failures

### App Shell Tests
- ✅ Application launches successfully
- ✅ Loads CSS theme correctly
- ✅ Q key exits application
- ✅ Handles initialization errors gracefully

### CLI Entry Point Tests
- ✅ Parses command line arguments correctly
- ✅ Validates argument values
- ✅ python -m switchboard.tui works
- ✅ Help text is displayed correctly

## Success Criteria
1. All acceptance tests pass
2. Application runs without errors in clean environment
3. Real-time updates work with live agent_router daemon
4. Performance requirements are met
5. Code coverage exceeds 90% for all modules