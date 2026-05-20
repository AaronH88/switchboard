# Switchboard TUI Secondary Screens & Thematic Polish - Acceptance Criteria

## Overview

The Secondary Screens & Thematic Polish feature adds three specialized screens (DetailScreen, LogFocusScreen, ProjectScreen) and thematic messaging system to enhance the Switchboard TUI user experience. These screens provide focused views for detailed inspection and project navigation, while thematic messages create an authentic operator console experience.

## Functional Requirements

### 1. DetailScreen (screens/detail.py)

#### Screen Purpose
Provides detailed inspection of selected beads with live output monitoring.

#### Navigation Requirements
- **Entry**: Press 'D' key when bead is selected in PatchPanel or ActiveLines
- **Exit**: Press 'Escape' key to return to main screen
- **Focus**: Screen should capture all input when active

#### Content Display Requirements
- **Header**: Display selected bead ID and title
- **Bead Information Panel**: Show full bead metadata:
  - Title and description
  - Agent type and current status
  - Labels and priority information
  - Dependencies (blocks/blocked-by relationships)
  - Creation and last update timestamps
  - Epic relationship (parent/child hierarchy)

- **Live Log Panel**: Display real-time stdout from selected bead:
  - Source: `artifacts/logs/<bead_id>/stdout.log`
  - Update frequency: Real-time file tailing
  - Display format: Raw log output with timestamps
  - Scrollable with standard navigation keys
  - Auto-scroll to bottom when new content arrives

#### Layout Requirements
```
┌─────────────────────────────────────────────────────────┐
│ DETAIL: [bead-id] [title] (agent: [agent_type])        │
├─────────────────┬───────────────────────────────────────┤
│ BEAD INFO       │ LIVE OUTPUT                           │
│                 │                                       │
│ Title: [...]    │ [timestamp] [log line 1]             │
│ Agent: [...]    │ [timestamp] [log line 2]             │
│ Status: [...]   │ [timestamp] [log line 3]             │
│ Labels: [...]   │ ...                                   │
│ Dependencies:   │ [timestamp] [latest line]             │
│   blocks: [...] │ ▌                                     │
│   blocked: [...] │                                       │
│ Created: [...]  │                                       │
│ Updated: [...]  │                                       │
│ Epic: [...]     │                                       │
│                 │                                       │
└─────────────────┴───────────────────────────────────────┘
│ Esc:Back  ↑↓:Scroll  Tab:Switch Panel                  │
└─────────────────────────────────────────────────────────┘
```

### 2. LogFocusScreen (screens/log_focus.py)

#### Screen Purpose
Provides fullscreen view of Party Line content with enhanced log inspection capabilities.

#### Navigation Requirements
- **Entry**: Press 'L' key from any screen
- **Exit**: Press 'Escape' or 'L' key to return to previous screen
- **Source Switching**: Number keys 1-9 switch worker source, 0 for daemon log

#### Content Display Requirements
- **Fullscreen Log Display**: 
  - Same content as PartyLine widget but with maximum screen real estate
  - Increased vertical space for more log history
  - Maintains source switching functionality
  - Supports all PartyLine navigation and filtering

- **Enhanced Header Information**:
  - Current log source (daemon or worker details)
  - Total line count and current position
  - Time range of displayed logs
  - Connection status indicator

#### Layout Requirements
```
┌─────────────────────────────────────────────────────────┐
│ [DAEMON LOG] 1,247 lines (showing last 100)           │
├─────────────────────────────────────────────────────────┤
│ 14:23:01  DAEMON ONLINE                                 │
│ 14:23:15  CONNECTING mol-feature-xyz                    │
│ 14:23:16  LINE CLEAR ✓ (mol-test-abc)                  │
│ 14:23:45  CONNECTING epic-polish-789                    │
│ 14:24:01  DAEMON PROCESSING...                          │
│ ...                                                     │
│ ...                                                     │
│ 14:30:12  CALL COMPLETE ✓ (epic-polish-789)            │
│ ▌                                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
│ Esc/L:Back  1-9:Workers  0:Daemon  ↑↓:Scroll  PgUp/Dn │
└─────────────────────────────────────────────────────────┘
```

### 3. ProjectScreen (screens/project.py)

#### Screen Purpose
Provides project-focused view of epics with status grouping and statistics.

#### Navigation Requirements
- **Entry**: Press 'P' key from main screen (when ProjectsPanel has focus)
- **Exit**: Press 'Escape' or 'P' key to return to main screen
- **Selection**: Up/Down arrows to navigate between epics
- **Details**: 'D' or Enter to open DetailScreen for selected epic

#### Content Display Requirements
- **Project Selection**: Show available projects with selection interface
- **Epic Grouping**: Group epics by status:
  - **Active**: Currently running or ready to run
  - **Completed**: Successfully finished epics
  - **Queued**: Blocked or pending epics

- **Epic Information**: For each epic display:
  - Epic ID and title
  - Current status and progress
  - Number of steps (completed/total)
  - Last activity timestamp
  - Estimated completion (for active)

- **Project Statistics**: Show aggregate data:
  - Total epics by status
  - Success rate over time period
  - Average completion time
  - Current resource utilization

#### Layout Requirements
```
┌─────────────────────────────────────────────────────────┐
│ PROJECT: automation-nexus (15 active, 8 queued)        │
├─────────────────────────────────────────────────────────┤
│ ┌─ ACTIVE (15) ─────────────────┐ ┌─ STATS ──────────┐ │
│ │ ▶ epic-auth-refactor          │ │ Completed: 147   │ │
│ │   5/7 steps │ Est: 12m        │ │ Success Rate: 94% │ │
│ │   epic-ui-overhaul            │ │ Avg Time: 23m    │ │
│ │   2/5 steps │ Est: 8m         │ │ Active Lines: 6/9 │ │
│ │   epic-api-gateway            │ └──────────────────┘ │
│ │   1/4 steps │ Est: 15m        │                      │
│ └───────────────────────────────┘                      │
│ ┌─ COMPLETED (8) ───────────────┐                      │
│ │   epic-logging-v2    ✓ 18m    │                      │
│ │   epic-test-suite    ✓ 12m    │                      │
│ │   epic-docs-update   ✓ 6m     │                      │
│ └───────────────────────────────┘                      │
│ ┌─ QUEUED (3) ──────────────────┐                      │
│ │   epic-performance   (blocked) │                      │
│ │   epic-deployment    (waiting) │                      │
│ └───────────────────────────────┘                      │
└─────────────────────────────────────────────────────────┘
│ Esc/P:Back  D:Details  ↑↓:Navigate  Tab:Switch Group   │
└─────────────────────────────────────────────────────────┘
```

### 4. Thematic Messaging System

#### Purpose
Provide authentic operator console experience with context-appropriate messages.

#### Startup Message
- **Display**: App shows 'SWITCHBOARD ONLINE · PATCHING IN...' briefly on mount
- **Duration**: 2-3 seconds during initial connection and state loading
- **Position**: Centered overlay on main interface
- **Style**: Highlighted with operator console styling

#### Daemon Status Messages
- **No Dial Tone**: When `daemon_online` is False, header shows 'NO DIAL TONE'
- **Position**: Replace normal header status in SwitchboardHeader
- **Color**: Warning/amber color to indicate attention needed
- **Update**: Immediate when daemon status changes

#### Empty State Messages
- **All Quiet**: When no workers active AND no ready beads, show 'ALL QUIET ON THE BOARD'
- **Position**: Main PatchPanel area when empty
- **Context**: Only when system is truly idle (no background activity)
- **Style**: Muted/dimmed text indicating standby state

#### Capacity Messages
- **All Lines Busy**: When all worker slots full, show 'ALL LINES BUSY · N CALLS HOLDING'
- **Display**: In OperatorPanel worker capacity area
- **Dynamic**: N = number of ready beads waiting for worker slots
- **Update**: Real-time as queue status changes

#### Epic Completion Visual
- **Epic Complete**: Brief visual flash when a pipeline completes
- **Effect**: Subtle screen flash or highlight animation
- **Duration**: 200-300ms brief flash, no persistent UI change
- **Trigger**: Completion of any epic-level pipeline
- **Style**: Success color (green/bright) flash

### 5. Edge Case Handling

#### Missing Log Files
- **Scenario**: App starts with no agent_router.log file
- **Behavior**: PartyLine shows "(waiting for daemon)" message
- **Recovery**: When file appears, begin normal log tailing
- **No Error**: Silent handling, no user notification needed

#### Empty Database
- **Scenario**: App starts with no beads in database
- **Behavior**: Show appropriate empty states in all panels
- **Message**: "ALL QUIET ON THE BOARD" in main area
- **Navigation**: All screens handle empty state gracefully

#### Daemon Disconnect
- **Scenario**: Daemon stops while TUI is running
- **Immediate**: Header changes to "NO DIAL TONE"
- **Graceful**: All screens continue to function with last known state
- **Recovery**: When daemon reconnects, resume normal operation

#### Terminal Resize
- **Scenario**: User resizes terminal during operation
- **Behavior**: All screens adapt layout to new dimensions
- **Minimum**: Support down to 80x24 characters
- **Responsive**: Secondary screens maintain usability at small sizes

## Non-Functional Requirements

### Performance
- **Screen Transitions**: Screen changes complete within 100ms
- **Log Tailing**: New log lines appear within 500ms of file write
- **Memory Efficiency**: Each screen < 5MB additional memory usage
- **Responsive Navigation**: Key presses acknowledged within 50ms

### Reliability
- **Error Isolation**: Screen failures don't crash main application
- **State Preservation**: Return to main screen preserves previous state
- **Resource Cleanup**: Screens properly dispose resources on exit
- **Graceful Fallback**: Missing data doesn't prevent screen display

### Usability
- **Consistent Navigation**: Same key patterns across all screens
- **Clear Context**: User always knows which screen is active
- **Escape Hatch**: Escape key always returns to main interface
- **Visual Hierarchy**: Important information prominently displayed

## Success Criteria

### DetailScreen Success
1. ✅ D key opens detail view for selected bead
2. ✅ All bead metadata displays correctly and completely
3. ✅ Live log output updates in real-time from stdout file
4. ✅ Escape key returns to main screen with preserved state

### LogFocusScreen Success
1. ✅ L key opens fullscreen log view
2. ✅ Number keys switch between log sources (0-9)
3. ✅ Enhanced log capacity shows more history
4. ✅ All PartyLine functionality preserved in fullscreen mode

### ProjectScreen Success
1. ✅ P key opens project view from main screen
2. ✅ Epics grouped correctly by status (Active/Completed/Queued)
3. ✅ Project statistics calculate and display accurately
4. ✅ Epic selection and detail navigation works correctly

### Thematic Messaging Success
1. ✅ Startup message appears briefly during app initialization
2. ✅ "NO DIAL TONE" shows when daemon is offline
3. ✅ "ALL QUIET" appears when system is idle
4. ✅ "ALL LINES BUSY" shows when workers at capacity
5. ✅ Epic completion flash provides satisfying feedback

### Edge Case Success
1. ✅ Missing files handled gracefully without crashes
2. ✅ Empty database states display appropriate messages
3. ✅ Daemon disconnection handled with clear user feedback
4. ✅ Terminal resize maintains screen usability

## User Acceptance Scenarios

### Scenario 1: Bead Investigation Workflow
**Given**: User sees an interesting bead in PatchPanel
**When**: User presses 'D' to open detail view
**Then**: 
- DetailScreen opens showing complete bead information
- Live log output starts displaying real-time stdout
- User can investigate bead behavior in detail
- Escape key returns to main interface smoothly

### Scenario 2: Log Deep Dive
**Given**: User wants to investigate log patterns
**When**: User presses 'L' to open fullscreen logs
**Then**:
- LogFocusScreen opens with maximum log visibility
- Number keys switch between daemon and worker logs
- Enhanced log capacity shows extended history
- User can perform detailed log analysis

### Scenario 3: Project Overview
**Given**: User wants to see project-level status
**When**: User navigates to ProjectsPanel and presses 'P'
**Then**:
- ProjectScreen opens with epic status overview
- Epics are clearly grouped by status
- Project statistics provide useful insights
- User can navigate to specific epics for details

### Scenario 4: Operator Experience
**Given**: User is monitoring multiple active pipelines
**When**: System state changes throughout work session
**Then**:
- Startup shows authentic "PATCHING IN" message
- Daemon disconnection clearly indicates "NO DIAL TONE"
- Capacity limits show "ALL LINES BUSY" messaging
- Epic completions provide satisfying visual feedback

### Scenario 5: Edge Case Recovery
**Given**: User encounters various edge conditions
**When**: Files are missing, database empty, or daemon offline
**Then**:
- All screens handle missing data gracefully
- Appropriate empty state messages display
- No crashes or error dialogs interrupt workflow
- System recovers smoothly when resources become available

## Testing Strategy

### Unit Testing Focus
- Screen initialization and mounting
- Navigation key handling and routing
- Content display and formatting
- State management within screens
- Resource cleanup on screen exit

### Integration Testing Focus
- Screen transitions and state preservation
- Cross-screen navigation patterns
- Shared resource management
- Thematic message triggering
- Edge case handling across screens

### Manual Testing Requirements
- Real daemon connectivity testing with screen transitions
- Log file tailing performance under load
- Terminal resize behavior across all screens
- Extended session testing with frequent screen switching
- User workflow testing for common investigation patterns