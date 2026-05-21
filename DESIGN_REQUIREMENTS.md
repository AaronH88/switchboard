# Design Requirements: Dynamic Config Reloading

## Implementation Requirements

This document outlines the technical requirements and design constraints for implementing dynamic config reloading in the switchboard daemon.

## Core Components to Implement

### 1. File Change Detection System

**Location:** New module `agent_router/config_watcher.py`

**Required Functions:**
```python
class ConfigWatcher:
    def __init__(self, switchboard_dir: str, projects_registry: dict, reload_interval: int)
    def check_for_changes() -> bool
    def get_changed_files() -> list[str] 
    def update_tracked_files(new_registry: dict)
```

**Implementation Details:**
- Track modification times (`os.path.getmtime()`) for all config files
- Store mtime cache as class attribute with file path → timestamp mapping
- Compare cached times with current file times on each check
- Handle `FileNotFoundError` gracefully (file deleted/moved)
- Support both `switchboard.yaml` and all project `project.yaml` files

### 2. Registry Reload Logic

**Location:** Modify existing `agent_router/run.py`

**Required Functions:**
```python
def reload_registry_if_needed(watcher: ConfigWatcher, current_registry: dict) -> dict
def validate_registry(registry: dict) -> bool
def log_registry_changes(old_registry: dict, new_registry: dict)
```

**Integration Points:**
- Modify `main()` function to create ConfigWatcher instance
- Add reload check to main daemon loop after bead polling
- Preserve reference to current registry for active workers
- Update global registry variable only after successful validation

### 3. Configuration Extensions

**Location:** `agent_router/config.yaml`

**New Config Options:**
```yaml
# Existing options...
poll_interval: 10
max_workers: 3

# New options for config reloading
config_reload_enabled: true    # Enable/disable reload feature
config_reload_interval: 30     # Seconds between change checks
config_reload_timeout: 5       # Max seconds for reload operation
```

**Required Functions:**
```python
def get_reload_config(config: dict) -> dict[str, Any]
def validate_reload_config(config: dict) -> list[str]  # Returns validation errors
```

### 4. Error Handling and Logging

**Required Log Levels and Messages:**

**INFO Level:**
- `"Config reload enabled (interval=%ds)"`
- `"Config change detected in %s"`  
- `"Registry rebuilt: %d projects loaded (%d added, %d removed, %d modified)"`
- `"Registry reload completed in %.2fs"`

**WARNING Level:**
- `"Project config not found: %s"`
- `"Project %s removed from config, %d orphaned beads may be skipped"`
- `"Config reload took longer than expected: %.2fs > %.2fs"`

**ERROR Level:**
- `"Failed to parse %s: %s"`
- `"Registry rebuild failed, keeping previous config: %s"`
- `"Config reload timeout after %.2fs"`

## Main Loop Integration

**Current main loop structure:**
```python
while running:
    ready = get_ready_beads()          # Current
    for bead in ready:                 # Current  
        # Process beads...             # Current
    time.sleep(poll_interval)          # Current
```

**Updated main loop structure:**
```python
while running:
    ready = get_ready_beads()          # Existing
    
    # NEW: Check for config changes
    if watcher.check_for_changes():
        new_registry = reload_registry_if_needed(watcher, registry)
        if new_registry is not None:
            registry = new_registry    # Update global registry
    
    for bead in ready:                 # Existing
        # Process beads with current registry...
    time.sleep(poll_interval)          # Existing
```

## Worker Process Isolation

**Current Worker Spawning:**
- Workers receive registry data at spawn time
- Registry passed as part of worker environment/parameters  
- Workers operate independently once started

**Required Modifications:**
- No changes needed to worker spawning logic
- Workers naturally isolated by receiving registry snapshot at creation
- New workers automatically get updated registry from current `registry` variable

## Data Structures

### ConfigWatcher State
```python
@dataclass
class FileTrackingInfo:
    path: str
    last_mtime: float
    last_size: int      # Additional verification
    
class ConfigWatcher:
    tracked_files: dict[str, FileTrackingInfo]
    reload_interval: int
    last_check_time: float
```

### Registry Diff Detection
```python
@dataclass  
class RegistryDiff:
    added_projects: set[str]
    removed_projects: set[str] 
    modified_projects: set[str]
    unchanged_projects: set[str]
```

## Performance Constraints

### File System Operations
- File stat operations must complete < 50ms total per check
- Support up to 50 projects (50 project.yaml + 1 switchboard.yaml)
- Minimize filesystem calls using efficient batching

### Memory Usage  
- ConfigWatcher state should use < 1MB memory for typical installations
- Registry objects should be garbage collected after replacement
- No memory leaks from repeated reload operations

### Timing Requirements
- Config change detection: < 100ms
- Registry rebuild: < 5 seconds for typical configs  
- Worker processes unaffected by reload operations

## Backward Compatibility

### Configuration Files
- All existing `switchboard.yaml` and `project.yaml` files continue working
- New config options have sensible defaults
- Feature can be disabled entirely via config

### API Compatibility
- `_build_project_registry()` function signature unchanged
- Registry data structure format unchanged  
- No breaking changes to worker spawning interface

## Testing Strategy

### Unit Test Requirements
- Mock filesystem operations for deterministic testing
- Test file change detection with various scenarios
- Validate registry building with corrupt inputs
- Verify error handling paths

### Integration Test Requirements  
- Real file operations with temporary directories
- Worker process lifecycle during config changes
- End-to-end reload cycles with timing verification
- Resource leak detection over multiple reloads

## Edge Case Handling

### File System Edge Cases
1. **Atomic writes:** Handle editors that write to temp files then rename
2. **Permission changes:** Graceful degradation when files become unreadable  
3. **Missing files:** Project directories deleted while daemon running
4. **Network filesystems:** Handle delayed or inconsistent mtime updates

### Concurrency Edge Cases
1. **Rapid changes:** Multiple config modifications within reload interval
2. **Partial writes:** Config files modified during daemon read operation
3. **Worker spawning during reload:** Ensure consistent registry state

### Resource Limit Edge Cases  
1. **File handle limits:** Efficient file access patterns
2. **Large configs:** Performance with many projects and complex pipelines
3. **Memory pressure:** Graceful behavior under system resource constraints

## Implementation Phases

### Phase 1: Basic File Monitoring
- Implement ConfigWatcher class with mtime tracking
- Add reload check to main loop
- Basic logging and error handling

### Phase 2: Registry Rebuilding  
- Integrate with existing `_build_project_registry()`
- Add validation and diff detection
- Comprehensive error recovery

### Phase 3: Configuration and Polish
- Add config options for reload behavior
- Performance optimization and testing
- Documentation and deployment validation