# Test Specifications: Dynamic Config Reloading

## Test Suite Overview

This document specifies test cases for dynamic config reloading in the switchboard daemon. Tests validate that the registry rebuilds appropriately when configuration files change while preserving active workers and handling error conditions gracefully.

## Test Categories

### 1. File Change Detection Tests

#### Test 1.1: Registry rebuilds when switchboard.yaml mtime changes
**Given:** Daemon is running with loaded registry  
**When:** `switchboard.yaml` file is modified (content or touch)  
**Then:** 
- Registry rebuild is triggered within configured interval
- New registry reflects changes from updated `switchboard.yaml`
- Rebuild completion is logged with timestamp

**Test Inputs:**
- Initial `switchboard.yaml` with 2 projects
- Modified version adding 1 new project
- Touch command updating mtime without content changes

**Expected Outputs:**
- Log message: "Config change detected in switchboard.yaml"
- Log message: "Registry rebuilt: 3 projects loaded"
- Registry contains all 3 projects with correct paths

#### Test 1.2: Registry rebuilds when project's project.yaml mtime changes  
**Given:** Daemon is running with loaded registry containing project "webapp"  
**When:** `webapp/project.yaml` file is modified  
**Then:**
- Registry rebuild is triggered within configured interval
- Project "webapp" config is reloaded from file
- Other projects remain unchanged

**Test Inputs:**
- `webapp/project.yaml` with dev pipeline
- Modified version adding quick-fix pipeline
- Modification timestamp update

**Expected Outputs:**
- Log message: "Config change detected in webapp/project.yaml"
- Registry["webapp"]["pipelines"] contains both dev and quick-fix pipelines

#### Test 1.3: No rebuild when files haven't changed
**Given:** Daemon has completed initial load  
**When:** Multiple reload check intervals pass with no file changes  
**Then:**
- No registry rebuilds are triggered
- No "config change detected" log messages
- Performance impact is minimal (< 10ms per check)

**Test Inputs:**
- Static config files for 5 check intervals
- System clock advancement without file modifications

**Expected Outputs:**
- No rebuild log messages
- Registry object reference remains unchanged
- Check timing under performance threshold

### 2. Active Worker Safety Tests

#### Test 2.1: Active workers are not interrupted during reload
**Given:** Worker process is actively executing bead "task-123"  
**When:** Config files are modified triggering registry reload  
**Then:**
- Active worker continues execution without interruption
- Worker uses original registry for current task completion
- Worker exit code and logs indicate successful completion

**Test Inputs:**
- Long-running development agent task (10+ seconds)
- Config modification during task execution
- Registry change affecting worker's project

**Expected Outputs:**
- Worker process continues without SIGTERM/SIGKILL
- Worker uses pre-reload config for task completion
- New beads use post-reload config

#### Test 2.2: New workers use updated config after reload
**Given:** Registry reload completed with new pipeline definitions  
**When:** New bead becomes ready for processing  
**Then:**
- Worker process uses updated registry for new bead
- New pipelines/tools are available for task execution

**Test Inputs:**
- Bead with agent label requiring new pipeline
- Registry reload adding required pipeline definition

**Expected Outputs:**
- Worker successfully claims and executes bead
- Worker uses new pipeline steps from reloaded config

### 3. Registry Content Update Tests

#### Test 3.1: New projects added to switchboard.yaml are picked up
**Given:** `switchboard.yaml` contains projects A and B  
**When:** File is updated to include project C with valid path  
**Then:**
- Registry contains projects A, B, and C after reload
- Project C configuration is loaded from its `project.yaml`
- Beads labeled with "project:C" become processable

**Test Inputs:**
- Initial switchboard.yaml: `projects: {A: {path: /path/a}, B: {path: /path/b}}`
- Updated: `projects: {A: {path: /path/a}, B: {path: /path/b}, C: {path: /path/c}}`
- Valid `/path/c/project.yaml` exists

**Expected Outputs:**
- `registry.keys()` returns `["A", "B", "C"]`
- `registry["C"]` contains loaded project configuration

#### Test 3.2: Removed projects are dropped from registry
**Given:** Registry contains projects A, B, C  
**When:** `switchboard.yaml` is updated to remove project B  
**Then:**
- Registry contains only projects A and C after reload
- Beads labeled "project:B" are skipped during processing
- Warning logged about orphaned beads for removed project

**Test Inputs:**
- Registry with 3 projects before reload
- `switchboard.yaml` with project B removed

**Expected Outputs:**
- `registry.keys()` returns `["A", "C"]`
- Log warning: "Project B removed from config, skipping related beads"

#### Test 3.3: Changed pipelines/tools in project.yaml take effect for new beads
**Given:** Project "webapp" has dev pipeline with 4 steps  
**When:** `webapp/project.yaml` updated to add quick-fix pipeline  
**Then:**
- Registry reflects new pipeline definition
- Beads requesting quick-fix pipeline can be processed
- Existing pipeline definitions remain functional

**Test Inputs:**
- Original project.yaml with single "dev" pipeline  
- Updated with additional "quick-fix" pipeline: `[development, verify]`

**Expected Outputs:**
- `registry["webapp"]["pipelines"]["quick-fix"]` exists
- Bead creation with quick-fix pipeline succeeds

### 4. Configuration Management Tests

#### Test 4.1: Reload interval is configurable  
**Given:** `config.yaml` specifies `config_reload_interval: 5`  
**When:** Daemon starts and config files are modified  
**Then:**
- File changes are detected within 5 second intervals
- Reload timing follows configured interval (±0.5s tolerance)

**Test Inputs:**
- Config.yaml with reload_interval: 5
- File modification at t=0, t=7, t=12

**Expected Outputs:**
- Reload triggered at t≤5, t≤12, t≤17
- No reload attempts between configured intervals

#### Test 4.2: Reload can be disabled via config
**Given:** `config.yaml` specifies `config_reload_enabled: false`  
**When:** Daemon starts and config files are modified  
**Then:**
- No file change detection occurs
- Registry remains static throughout daemon lifetime
- Log message indicates reload disabled

**Test Inputs:**
- Config with reload disabled
- Multiple file modifications during daemon run

**Expected Outputs:**
- Log: "Config reload disabled, using static registry"
- No "config change detected" messages
- Registry never rebuilds

### 5. Error Handling Tests

#### Test 5.1: Corrupt config files don't crash daemon
**Given:** Daemon running with valid registry  
**When:** `switchboard.yaml` is corrupted with invalid YAML syntax  
**Then:**
- Daemon continues running with previous valid config
- Error logged with specific YAML parsing details
- Registry remains unchanged from last valid state

**Test Inputs:**
- Valid initial switchboard.yaml
- Corrupted version with syntax error: `projects: [invalid: yaml: syntax}`

**Expected Outputs:**
- Process continues running (no exit)
- Log error: "Failed to parse switchboard.yaml: YAML syntax error at line 1"
- Registry unchanged from pre-corruption state

#### Test 5.2: Missing project.yaml files are handled gracefully
**Given:** Registry includes project with path `/missing/project`  
**When:** Registry reload attempts to load missing `project.yaml`  
**Then:**
- Project is excluded from new registry with warning
- Other projects continue loading successfully
- Daemon remains operational

**Test Inputs:**
- switchboard.yaml referencing non-existent project path
- Mixed scenario with valid and invalid project paths

**Expected Outputs:**
- Log warning: "Project config not found: /missing/project/project.yaml"
- Registry excludes missing project but includes valid ones

#### Test 5.3: Filesystem permission errors are logged and handled
**Given:** Config file exists but daemon lacks read permissions  
**When:** Registry reload attempts to read protected file  
**Then:**
- Permission error logged with file path and error details  
- Previous registry preserved
- Daemon continues operation

**Test Inputs:**
- `chmod 000 project.yaml` on existing project
- Registry reload triggered

**Expected Outputs:**
- Log error: "Permission denied reading /path/project.yaml"
- Registry retains pre-reload state

### 6. Performance and Integration Tests

#### Test 6.1: Reload performance under load
**Given:** Daemon managing 10 projects with active workers  
**When:** Config reload occurs during peak bead processing  
**Then:**
- Reload completes within 5 seconds
- Bead processing latency increases < 100ms during reload  
- Worker processes show no performance degradation

**Test Inputs:**
- 10 projects each with 5 repos and complex pipelines
- 3 active workers processing beads during reload
- Registry rebuild with file changes

**Expected Outputs:**
- Reload duration < 5000ms
- Worker execution times within normal variance
- No worker process failures

#### Test 6.2: Memory usage stability with frequent reloads
**Given:** Daemon with baseline memory footprint  
**When:** 100 reload cycles executed over 10 minutes  
**Then:**
- Memory usage remains stable (< 5% growth)
- No memory leaks detected
- File handle count remains constant

**Test Inputs:**  
- Automated script modifying configs every 6 seconds
- Memory profiling throughout test duration

**Expected Outputs:**
- RSS memory growth < 5% from baseline
- File descriptor count stable
- No garbage collection pressure increase

## Test Data Requirements

### Mock Configuration Files
- Valid switchboard.yaml with 2-5 test projects
- Template project.yaml with various pipeline configurations  
- Corrupted config files for error testing
- Large config files for performance testing

### Test Environment Setup
- Isolated filesystem with test project directories
- Mock bead database with test beads
- Controllable system clock for timing tests
- Resource monitoring capabilities

### Test Utilities Needed
- Config file modification helpers
- Registry state inspection utilities
- Worker process lifecycle management
- Log message parsing and validation
- Performance measurement tools

## Test Execution Strategy

### Unit Tests
- File change detection logic
- Registry building with various inputs
- Error handling for corrupt configs
- Configuration parsing edge cases

### Integration Tests  
- End-to-end reload cycles with real files
- Worker process interaction during reload
- Multi-project scenarios with mixed changes
- Performance under realistic load

### Stress Tests
- High frequency config changes
- Large number of projects and repos
- Concurrent worker and reload operations
- Resource exhaustion scenarios