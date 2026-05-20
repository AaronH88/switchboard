# Signature Widget Acceptance Criteria

## Overview

The Switchboard TUI signature widgets provide the core visual interface for monitoring agent pipelines. These widgets transform raw state data into intuitive, real-time displays that allow operators to understand system status at a glance.

## 1. PatchPanel Widget Requirements

### Purpose
The PatchPanel widget displays active agent pipelines as horizontal rows of connected step boxes, mimicking a telephone switchboard patch panel. Each pipeline shows the progress of work through standard agent stages.

### Visual Layout Requirements

#### Pipeline Title Format
- **Format**: `{project} / {repo}  #{epic_id}`
- **Examples**: 
  - `nexus / api  #mol-2hn`
  - `nexus-ui / packages  #epic-xyz`
- **Character Limit**: Truncate with ellipsis if > 80 characters
- **Alignment**: Left-aligned within pipeline row

#### Step Box Layout
- **Arrangement**: Horizontal row of connected boxes
- **Standard Steps**: TDD → TEST → DEV → VRFY → REVW
- **Box Dimensions**: Fixed width (8 chars), single height
- **Connections**: Visual connectors between adjacent boxes
- **Labels**: Abbreviated step names (TDD, TEST, DEV, VRFY, REVW)

#### Signal Lamp Status Indicators
- **Open**: `( )` - Empty parentheses, neutral color
- **In Progress**: `(*)` - Asterisk, active/bright color  
- **Completed**: `(✓)` - Checkmark, success/green color
- **Blocked/Failed**: `(✗)` - X mark, error/red color

#### Progress Counter
- **Format**: `{completed}/{total} done`
- **Position**: Right-aligned on pipeline title line
- **Logic**: Count steps with status "closed" as completed
- **Examples**: `3/5 done`, `0/7 done`, `5/5 done`

#### Active Step "Cord Pair" Display
When a step is in "in_progress" status and has an active worker:
```
┌──────┬──────┬──────┬──────┬──────┐
│ TDD  │ TEST │ DEV  │ VRFY │ REVW │
│ (✓)  │ (✓)  │ (*)  │ ( )  │ ( )  │
└──────┴──────┴──┬───┴──────┴──────┘
                 └── claude · 12m 34s
```
- **Content**: `{tool_name} · {elapsed_time}`
- **Position**: Connector line from active step box to bottom
- **Update**: Real-time elapsed time updates every second
- **Removal**: Disappears when step completes or worker stops

### Functional Requirements

#### Empty State Display
- **Condition**: No active pipelines in system
- **Display**: Centered message "No active pipelines"
- **Styling**: Muted text color, consistent with theme

#### Multiple Pipeline Display
- **Layout**: Vertical stack of pipeline rows
- **Spacing**: 1 line space between pipeline rows  
- **Ordering**: Sort by epic_id alphabetically
- **Scrolling**: Vertical scroll when pipelines exceed screen height

#### Real-Time Updates
- **Signal Lamps**: Update immediately when step status changes
- **Cord Pairs**: Appear/disappear as workers start/stop
- **Elapsed Time**: Update every second for active workers
- **Progress Counters**: Update when any step completes
- **New Pipelines**: Appear automatically when epics start
- **Completed Pipelines**: Remove automatically when epics finish

### Performance Requirements
- **Initial Render**: < 100ms for up to 20 pipelines
- **State Update**: < 50ms response to status changes
- **Scroll Performance**: Smooth scrolling for 100+ pipelines
- **Memory Usage**: < 5MB for widget with 50 pipelines

### Error Handling Requirements
- **Missing Workers**: Show (*) signal without cord pair
- **Invalid Status**: Show (?) for unrecognized step status
- **Malformed Data**: Graceful degradation, show what's available
- **Long Titles**: Truncate with ellipsis, maintain layout

## 2. PartyLine Widget Requirements

### Purpose
The PartyLine widget displays log entries from the agent router daemon and individual workers, formatted with telephone operator jargon to match the switchboard metaphor. Operators can switch between sources to monitor specific workers.

### Source Management Requirements

#### Default Source - Daemon Log
- **Header Format**: `[DAEMON LOG] ────────────────────`
- **Content**: Events from agent_router.log
- **Filtering**: Show only daemon-level events (claimed, completed, failed, etc.)

#### Worker Source Display  
- **Header Format**: `[WORKER {N}: {bead_id} {agent}] ──────`
- **Content**: stdout/stderr from specific worker process
- **Selection**: Number keys 1-9 switch to worker N
- **Availability**: Only show sources for active workers

#### Source Switching
- **Default Key**: '0' or 'D' returns to daemon log
- **Worker Keys**: '1'-'9' switch to corresponding worker
- **Invalid Keys**: No action if worker doesn't exist
- **Visual Feedback**: Header updates immediately on source change

### Log Entry Display Requirements

#### Timestamp Formatting
- **Format**: `HH:MM:SS` (24-hour format)
- **Source**: Parse from LogEvent timestamp field
- **Alignment**: Left-aligned, fixed width (8 chars + 2 spaces)

#### Operator Jargon Translation
Transform daemon log messages into telephone operator terminology:

- **Claimed Event**: `"Claimed mol-2hn (agent: development)"` 
  → `"14:23:01  CONNECTING mol-2hn"`

- **Launched Event**: Worker appears in state
  → `"14:23:02  LINE 1 CONNECTED (mol-2hn development)"`

- **Completed Event**: `"Completed mol-2hn (agent: development)"` 
  → `"14:23:15  LINE CLEAR ✓ (mol-2hn)"`

- **Failed Event**: `"Failed mol-2hn attempt 1/3, requeued"`
  → `"14:23:20  DROPPED CALL · REDIALING (1/3) mol-2hn"`

- **Merge Conflict**: `"Merge conflict for mol-2hn"`
  → `"14:23:25  ROUTING TO SUPERVISOR (mol-2hn conflict)"`

- **Epic Complete**: `"Epic completed: epic-xyz (title)"`
  → `"14:23:30  CALL COMPLETE ✓ (epic-xyz)"`

- **Daemon Started**: `"Switchboard started"`  
  → `"14:23:00  DAEMON ONLINE"`

- **Daemon Stopped**: `"Switchboard stopped"`
  → `"14:23:59  DAEMON OFFLINE"`

#### Raw Log Passthrough
- **Unrecognized Events**: Display original message with timestamp
- **Worker Output**: Show raw stdout/stderr when viewing worker source
- **Format**: `{timestamp}  {original_message}`

### Scrolling and Navigation Requirements

#### Auto-Scroll Behavior
- **Default**: Auto-scroll enabled, new entries appear at bottom
- **New Entries**: Automatically scroll to show latest entry
- **Manual Override**: Auto-scroll disabled when user scrolls up
- **Re-enable**: Auto-scroll resumes when user scrolls to bottom

#### Keyboard Navigation
- **Arrow Keys**: Up/Down for line-by-line scrolling
- **Page Keys**: Page Up/Down for screen-by-screen scrolling  
- **Home/End**: Jump to top/bottom of log buffer
- **Source Keys**: 0-9 for source switching

#### Buffer Management
- **Capacity**: Maximum 1000 log entries in memory
- **Overflow**: Remove oldest entries when buffer full
- **Performance**: Maintain smooth scrolling with full buffer

### Visual Layout Requirements

#### Empty State Display
- **Condition**: No log entries for current source
- **Daemon Log**: `"(waiting for daemon events)"`
- **Worker Log**: `"(no output from this worker)"`

#### Header Styling  
- **Background**: Distinct color from main log area
- **Text**: Source name clearly visible
- **Separator**: Horizontal line or border below header

#### Log Entry Styling
- **Timestamps**: Muted color, monospace font
- **Messages**: Normal text color, readable font
- **Success Events**: Green tint for "✓" symbols
- **Error Events**: Red tint for error/failure messages  
- **Status Events**: Yellow/amber for in-progress indicators

### Functional Requirements

#### Real-Time Updates
- **New Entries**: Appear immediately as events occur
- **Source Changes**: Content updates immediately on source switch
- **Worker Lifecycle**: Sources appear/disappear as workers start/stop
- **Buffer Updates**: Smooth addition/removal of log entries

#### Error Handling
- **Malformed Timestamps**: Show "??:??:??" placeholder
- **Missing Events**: Handle gracefully, no widget crashes  
- **Long Messages**: Word wrap or truncate to fit widget width
- **Unicode/Special Chars**: Display safely without breaking layout

### Performance Requirements
- **Log Processing**: < 1ms per log entry for jargon translation
- **Scroll Performance**: < 50ms for any scroll operation
- **Source Switch**: < 100ms to switch between sources
- **Memory Usage**: < 3MB for widget with full 1000-entry buffer

## Integration Requirements

### Widget Coordination
- **State Sharing**: Both widgets use same SwitchboardState instance
- **Update Synchronization**: State changes update both widgets consistently
- **Resource Management**: No conflicts between widget operations

### Data Dependencies
- **PatchPanel Dependencies**:
  - SwitchboardState.pipelines (Dict[str, PipelineState])
  - SwitchboardState.workers (Dict[str, WorkerState])
- **PartyLine Dependencies**:
  - SwitchboardState.events (deque of LogEvent)
  - SwitchboardState.workers (for source switching)

### CSS Theme Integration
- **Color Palette**: Amber CRT theme colors throughout
- **Consistency**: Visual harmony between both widgets
- **Accessibility**: Sufficient contrast for terminal displays

## Success Criteria

### Functional Success
1. ✅ PatchPanel accurately displays pipeline status in real-time
2. ✅ Signal lamps correctly represent step states (open/progress/done/blocked)
3. ✅ Cord pairs show active workers with real-time elapsed time
4. ✅ Progress counters accurately reflect completion ratios
5. ✅ PartyLine translates daemon events into operator jargon
6. ✅ Source switching works between daemon and worker logs
7. ✅ Auto-scroll behavior works as expected
8. ✅ Both widgets handle empty states gracefully

### Performance Success  
1. ✅ Widgets render initial state within 100ms
2. ✅ State updates reflected within 50ms
3. ✅ Smooth scrolling performance under load
4. ✅ Memory usage remains stable during extended operation

### Usability Success
1. ✅ Information is readable at a glance
2. ✅ Visual metaphor (switchboard) is intuitive
3. ✅ Real-time updates don't disrupt user focus
4. ✅ Keyboard navigation is responsive and predictable

### Integration Success
1. ✅ Widgets work together without conflicts
2. ✅ Consistent visual styling across both widgets
3. ✅ Shared state updates propagate correctly
4. ✅ Error conditions don't crash or corrupt display

## User Acceptance Tests

### Scenario 1: Monitor Pipeline Progress
**Given**: System has 3 active pipelines at different stages
**When**: Operator views PatchPanel
**Then**: 
- All 3 pipelines shown with current step status
- Progress counters accurate (e.g., "2/5 done")
- Active steps show cord pairs with worker info

### Scenario 2: Track Worker Activity
**Given**: Worker is processing a development step  
**When**: Operator observes pipeline over time
**Then**:
- Signal lamp shows (*) for in-progress step
- Cord pair displays tool name and elapsed time
- Elapsed time increments every second

### Scenario 3: Review System Events
**Given**: Various daemon events have occurred
**When**: Operator views PartyLine daemon log
**Then**:
- Events translated to operator jargon
- Chronological order maintained
- Auto-scroll shows latest events

### Scenario 4: Investigate Worker Issues
**Given**: Worker 2 is having problems
**When**: Operator presses '2' key to view worker output
**Then**:
- Source switches to "[WORKER 2: bead-id agent]"
- Raw worker stdout/stderr displayed
- Can switch back to daemon with '0' key

### Scenario 5: Handle System Scale
**Given**: 25+ active pipelines and high log volume
**When**: System runs for several hours
**Then**:
- All pipelines remain visible with scrolling
- Log buffer manages memory efficiently  
- UI remains responsive throughout