# Switchboard TUI App Assembly - Acceptance Criteria

## Overview

The App Assembly is the final integration layer of the Switchboard TUI that wires together all signature widgets (PatchPanel, PartyLine, etc.) with the core application infrastructure. It handles layout composition, keybinding orchestration, polling coordination, and state propagation across the entire interface.

## Functional Requirements

### 1. App Layout Requirements (app.py)

#### compose() Method Integration
The `compose()` method must mount all widgets in the correct hierarchical order:

```
┌─────────────────────────────────────────────────────┐
│ SwitchboardHeader (full width, top)                │
├─────────────────┬───────────────────────────────────┤
│ OperatorPanel   │ ProjectsPanel                     │
│ (left sidebar)  │ (right sidebar)                   │
├─────────────────┴───────────────────────────────────┤
│ PatchPanel (main scrollable area)                  │
├─────────────────────────────────────────────────────┤
│ ActiveLines (worker status table)                  │
├─────────────────────────────────────────────────────┤
│ PartyLine (log display area)                       │
├─────────────────────────────────────────────────────┤
│ Footer (keybindings + daemon status)               │
└─────────────────────────────────────────────────────┘
```

#### Widget Presence Requirements
- **SwitchboardHeader**: Always visible, full width, contains title and system status
- **OperatorPanel**: Left sidebar, shows current user context and operator controls  
- **ProjectsPanel**: Right sidebar, displays project information and active counts
- **PatchPanel**: Main content area, scrollable pipeline display
- **ActiveLines**: Tabular view of active worker processes
- **PartyLine**: Log output area with source switching capability
- **Footer**: Status bar with keybinding hints and daemon connectivity

#### Layout Responsiveness
- Layout must adapt to terminal resize events
- Minimum supported terminal size: 80x24 characters
- Sidebar panels collapse gracefully on narrow terminals (< 100 chars wide)
- Main content area maintains scrollability regardless of terminal size

### 2. Keybinding System Requirements

#### Primary Navigation Keys
- **Q**: Quit application (immediate, no confirmation)
- **Tab**: Cycle focus forward through interactive widgets
- **Shift+Tab**: Cycle focus backward through interactive widgets
- **Escape**: Clear current selection/focus, return to default state

#### Action Keys  
- **D** or **Enter**: Open detail screen for selected item (when applicable)
- **L** or **F**: Toggle log focus mode (fullscreen PartyLine) — placeholder implementation
- **R**: Trigger immediate state refresh across all pollers

#### PartyLine Source Switching Keys
- **1-9**: Switch PartyLine to show Worker N output
- **0**: Switch PartyLine to daemon log (default source)

#### Navigation Keys (when focused on scrollable widgets)
- **Up/Down**: Line-by-line scrolling
- **Page Up/Page Down**: Screen-by-screen scrolling
- **Home/End**: Jump to top/bottom of content

#### Key Handling Requirements
- All keys must be case-insensitive where applicable
- Invalid key combinations should be ignored (no error display)
- Keybindings must not conflict between widget contexts
- Key events must not block UI rendering or state updates

### 3. Polling Integration Requirements

#### Polling System Startup (on_mount)
When the application mounts, it must start these background tasks:

1. **Log Watcher**: 
   - Target: `{artifacts_dir}/agent_router.log`
   - Method: File tailing using `tail_file()` async generator
   - Frequency: Real-time file watching

2. **Worker Poller**: 
   - Target: `bd list --status=in_progress --json`
   - Method: `set_interval(poll_workers, 10)` 
   - Frequency: Every 10 seconds

3. **Pipeline Poller**: 
   - Target: Build pipeline state from worker and epic data
   - Method: `set_interval(poll_pipelines, 15)`
   - Frequency: Every 15 seconds

4. **Stats Poller**:
   - Target: `bd stats --json`
   - Method: `set_interval(poll_stats, 60)`
   - Frequency: Every 60 seconds

#### Poller Error Handling
- Failed polling attempts must not crash the application
- Network/subprocess errors should be logged but not displayed to user
- Polling should resume automatically after temporary failures
- Daemon offline state should be detected and indicated in Footer

#### Polling Performance Requirements
- No polling operation should block UI updates > 100ms
- Memory usage should remain stable during extended operation
- Failed polls should use exponential backoff (up to 30s intervals)

### 4. State Propagation Requirements

#### State → Widget Binding
State changes must automatically trigger widget updates:

- **workers Dict Changes** → Updates to:
  - `ActiveLines` widget (worker process table)
  - `OperatorPanel` worker count and status indicators
  - `PatchPanel` active step "cord pairs"

- **pipelines Dict Changes** → Updates to:
  - `PatchPanel` pipeline rows and progress indicators
  - `ProjectsPanel` project activity counts

- **projects Dict Changes** → Updates to:
  - `ProjectsPanel` project list and metadata

- **events Deque Changes** → Updates to:
  - `PartyLine` log display with new entries

- **daemon_online Boolean Changes** → Updates to:
  - `Footer` daemon status indicator
  - All widgets should handle offline state gracefully

#### Update Propagation Timing
- State updates must be reflected in UI within 50ms
- Multiple rapid state changes should be batched for performance
- Widget updates should not cause scroll position loss
- Focus should be preserved across state updates

#### State Consistency Requirements
- All widgets must share the same `SwitchboardState` instance
- State modifications must be atomic (no partial updates visible)
- State rollback must be supported for error conditions

### 5. Footer Requirements

#### Keybinding Hints Display
Footer must display context-sensitive keybinding hints:

**Default State**: `Q:Quit  Tab:Navigate  R:Refresh  1-9:Workers  0:Daemon`

**When PatchPanel Focused**: `Q:Quit  D:Details  R:Refresh  ↑↓:Scroll  Tab:Navigate`

**When PartyLine Focused**: `Q:Quit  L:Focus  1-9:Workers  0:Daemon  ↑↓:Scroll  Tab:Navigate`

#### Daemon Status Indicator
- **Online State**: `(*) DAEMON ONLINE` (with active/bright color)
- **Offline State**: `(✗) DAEMON OFFLINE` (with error/red color)
- **Unknown State**: `(?) DAEMON STATUS` (with muted color)

#### Status Update Requirements
- Daemon status must update within 5 seconds of connectivity change
- Status indicator must be visible in all terminal sizes
- Status text must not overlap with keybinding hints

## Non-Functional Requirements

### Performance
- **Initial Assembly**: Complete app assembly within 2 seconds on typical systems
- **State Updates**: Propagate state changes to all widgets within 50ms
- **Key Response**: Keybinding actions must execute within 100ms
- **Memory Stability**: Memory usage increase < 1MB per hour of operation

### Reliability  
- **Error Isolation**: Widget failure must not crash entire application
- **Resource Recovery**: Automatic recovery from temporary resource unavailability
- **State Integrity**: No corrupt or inconsistent state visible to user
- **Graceful Degradation**: Reduced functionality when daemon unavailable

### Usability
- **Visual Hierarchy**: Clear information hierarchy across all widgets
- **Consistent Navigation**: Uniform focus and navigation behavior
- **Responsive Feedback**: Visual confirmation of user actions
- **Error Visibility**: Clear indication of error states without disrupting workflow

### Integration
- **Widget Coordination**: No conflicts between widget operations
- **Shared Resources**: Efficient sharing of state and polling resources
- **CSS Consistency**: Unified amber CRT theme across all widgets
- **Accessibility**: Support for terminal-based accessibility tools

## Success Criteria

### Layout Success
1. ✅ All 7 widgets mount in correct hierarchical order
2. ✅ Layout responds appropriately to terminal resize events
3. ✅ Widget boundaries and spacing are visually correct
4. ✅ No widget overlap or rendering artifacts

### Keybinding Success
1. ✅ All 13 defined keybindings work correctly
2. ✅ Focus cycles properly between interactive widgets
3. ✅ PartyLine source switching (keys 0-9) functions correctly
4. ✅ Key events don't block UI updates or cause conflicts

### Polling Success
1. ✅ All 4 polling systems start correctly on app mount
2. ✅ Polling continues reliably during extended operation
3. ✅ Error conditions don't crash polling systems
4. ✅ Manual refresh (R key) triggers immediate poll cycle

### State Integration Success
1. ✅ State changes propagate to correct widgets within 50ms
2. ✅ All widgets display consistent information
3. ✅ State updates don't cause focus loss or scroll jumping
4. ✅ Concurrent state updates handled correctly

### Footer Success
1. ✅ Context-sensitive keybinding hints display correctly
2. ✅ Daemon status indicator reflects actual connectivity
3. ✅ Status updates occur within 5 seconds of state change
4. ✅ Footer layout works across different terminal sizes

## User Acceptance Scenarios

### Scenario 1: Application Startup
**Given**: User launches Switchboard TUI with daemon running
**When**: Application completes startup sequence
**Then**: 
- All widgets are visible and properly positioned
- Daemon status shows "(*) DAEMON ONLINE"
- Live data appears in PatchPanel and ActiveLines
- Footer shows appropriate keybinding hints

### Scenario 2: Real-time Pipeline Monitoring
**Given**: Agent router has 3 active pipelines
**When**: User observes PatchPanel over 30 seconds
**Then**: 
- All 3 pipelines are visible with current status
- Signal lamps update as steps progress
- Worker cord pairs show real-time elapsed time
- Progress counters reflect completion status

### Scenario 3: Interactive Navigation
**Given**: Application is running with multiple widgets
**When**: User presses Tab key repeatedly
**Then**:
- Focus cycles through interactive widgets in correct order
- Visual focus indicator is clear and consistent
- Navigation doesn't disrupt ongoing data updates
- Final Tab press returns to first widget

### Scenario 4: Log Investigation Workflow
**Given**: Multiple workers are active and generating logs
**When**: User uses number keys to switch between log sources
**Then**:
- PartyLine source switches immediately on key press
- Header updates to show correct source (daemon/worker N)
- Log content switches to appropriate stream
- Key '0' returns to daemon log as expected

### Scenario 5: Error Recovery
**Given**: Daemon is stopped while app is running
**When**: User continues using the application
**Then**:
- Footer status changes to "(✗) DAEMON OFFLINE" within 5s
- Widgets handle missing data gracefully
- Manual refresh (R key) attempts to reconnect
- When daemon restarts, status returns to online

### Scenario 6: Extended Operation
**Given**: Application runs continuously for 4+ hours
**When**: User monitors memory usage and responsiveness
**Then**:
- Memory usage remains stable (< 4MB increase)
- All keybindings remain responsive
- Polling continues without degradation
- UI updates remain smooth and timely

## Testing Strategy

### Unit Testing Focus
- Widget mounting and initialization
- Keybinding registration and dispatch
- State change propagation logic
- Polling system coordination
- Error handling and recovery

### Integration Testing Focus
- Cross-widget communication
- Shared state consistency
- Polling system coordination
- End-to-end user scenarios
- Performance under load

### Manual Testing Requirements
- Real daemon connectivity testing
- Long-running session stability
- Terminal resize responsiveness
- Keyboard accessibility verification
- Error injection and recovery testing