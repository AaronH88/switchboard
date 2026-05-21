# Acceptance Criteria: Dynamic Config Reloading

## Feature Overview

The switchboard daemon must dynamically reload its project registry when configuration files change, without interrupting active worker processes.

## Current State Analysis

- Registry is built once during startup in `_build_project_registry()` (line 52 in `agent_router/run.py`)
- Registry contains project_name → {path, repos, pipelines, coding_tools, agents_dir, pipeline_tools, on_epic_complete}
- Main loop polls for ready beads using the static registry
- No mechanism exists for detecting config file changes

## Success Criteria

### 1. File Change Detection
- **MUST** detect when `switchboard.yaml` modification time changes
- **MUST** detect when any project's `project.yaml` modification time changes  
- **MUST NOT** rebuild when files haven't changed (performance optimization)
- **MUST** handle missing files gracefully (log warning, continue with current config)

### 2. Registry Rebuilding
- **MUST** rebuild the complete project registry when changes detected
- **MUST** preserve existing registry if new config is corrupted/invalid
- **MUST** log successful rebuilds with project count and changed projects
- **MUST** log rebuild failures with specific error details

### 3. Worker Process Safety
- **MUST NOT** interrupt active workers during config reload
- **MUST** allow running workers to complete using their original config
- **MUST** apply new config only to newly claimed beads
- **SHOULD** log when workers are using stale config vs new config

### 4. Project Registry Changes
- **MUST** pick up new projects added to `switchboard.yaml`
- **MUST** remove projects deleted from `switchboard.yaml` 
- **MUST** update project paths when changed
- **MUST** update pipeline definitions when `project.yaml` changes
- **MUST** update coding tools when `project.yaml` changes
- **MUST** update pipeline tools when `project.yaml` changes

### 5. Configuration Management
- **MUST** make reload check interval configurable in `config.yaml`
- **SHOULD** default to reasonable interval (30 seconds suggested)
- **MUST** allow disabling reload checks via config
- **SHOULD** support immediate reload via signal (SIGHUP)

### 6. Error Handling
- **MUST NOT** crash daemon on corrupted config files
- **MUST** log detailed error messages for config parsing failures
- **MUST** keep using previous valid config when reload fails
- **SHOULD** track and report consecutive reload failures

### 7. Observability
- **MUST** log when file changes are detected
- **MUST** log registry rebuild start/completion
- **MUST** log config validation errors
- **SHOULD** expose reload metrics for monitoring

## Non-Functional Requirements

### Performance
- Config change detection MUST complete within 100ms
- Registry rebuild MUST complete within 5 seconds for typical configs
- Reload checks MUST NOT impact bead polling performance

### Reliability
- Feature MUST be backward compatible with existing configs
- Feature MUST NOT introduce memory leaks from file watching
- Feature MUST handle file system permission errors gracefully

## Edge Cases Covered

1. **File System Events**: File disappears during read, permission changes, network filesystem delays
2. **Concurrent Access**: Multiple processes modifying configs, atomic write operations
3. **Malformed Configs**: YAML syntax errors, missing required fields, invalid paths
4. **Resource Limits**: Many projects with frequent config changes, file handle limits
5. **Timing Issues**: Config changes during registry rebuild, rapid successive changes