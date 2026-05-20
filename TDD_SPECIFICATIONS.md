# TDD Specifications for Switchboard Core Features

## Overview

This document specifies test requirements for Switchboard's core daemon functionality, pipeline execution, and end-to-end workflows that are not yet comprehensively tested.

## 1. Daemon Core Loop and Bead Processing

### Happy Path Scenarios

#### Test: Process Agent Beads Successfully
**Given**: 
- A ready bead with `agent:development`, `project:test-project`, `repo:backend` labels
- Project registry contains the project and repo configuration
- Agent file exists for the specified agent

**When**: Daemon processes the bead

**Then**:
- Bead is claimed successfully
- Worktree is created for the agent
- Coding tool is launched with correct prompt
- Process is tracked in active workers

#### Test: Process Tool Beads Successfully  
**Given**:
- A ready bead with `tool:create-pr`, `project:test-project`, `repo:backend` labels
- Project has pipeline tool configuration for `create-pr`

**When**: Daemon processes the bead

**Then**:
- Bead is claimed successfully
- No worktree is created (tools run directly)
- Pipeline tool command is executed with variable substitution
- Process is tracked in active workers

#### Test: Respect Maximum Worker Limit
**Given**:
- Max workers set to 2
- 3 ready beads available

**When**: Daemon processes beads

**Then**:
- Only 2 beads are claimed and started
- Third bead remains unclaimed until a worker completes

### Dependency and Blocking Scenarios

#### Test: Skip Beads with Open Dependencies
**Given**:
- Bead A depends on Bead B
- Bead B status is "in_progress"

**When**: Daemon evaluates Bead A

**Then**:
- Bead A is not claimed or started
- Bead A remains in ready state

#### Test: Process Beads When Dependencies Complete
**Given**:
- Bead A depends on Bead B  
- Bead B status changes to "closed"

**When**: Daemon runs next poll cycle

**Then**:
- Bead A becomes available for processing
- Bead A is claimed and started

### Epic Completion Detection

#### Test: Close Epic When All Children Complete
**Given**:
- Epic bead with 3 child task beads
- All 3 children have status "closed"

**When**: Daemon evaluates the epic

**Then**:
- Epic status is set to "closed"
- Epic is removed from processing queue

#### Test: Keep Epic Open with Incomplete Children
**Given**:
- Epic bead with 3 child task beads
- 2 children "closed", 1 child "in_progress"

**When**: Daemon evaluates the epic

**Then**:
- Epic remains with status "open"
- Epic continues to be evaluated each cycle

### Error Handling and Retries

#### Test: Retry Failed Beads Within Limit
**Given**:
- Bead fails with exit code 1
- Attempt count is 1, max_attempts is 3

**When**: Worker completes with failure

**Then**:
- Bead status is set to "open" 
- Attempt metadata is incremented to 2
- Bead becomes available for retry

#### Test: Block Beads After Max Attempts
**Given**:
- Bead fails with exit code 1
- Attempt count equals max_attempts (3)

**When**: Worker completes with failure

**Then**:
- Bead status is set to "blocked"
- Bead is removed from processing queue
- Error is logged

## 2. Pipeline Tool Execution

### Command Variable Substitution

#### Test: Substitute All Template Variables
**Given**:
- Tool command: `["gh", "pr", "create", "--title", "{epic_title}", "--head", "{branch}"]`
- Current branch: "feature/auth-fix"
- Epic title: "Add authentication"
- Bead ID: "bead-123"

**When**: Tool command is built

**Then**:
- Command becomes: `["gh", "pr", "create", "--title", "Add authentication", "--head", "feature/auth-fix"]`

#### Test: Working Directory Resolution
**Given**: Tool config with `cwd: "project"`
**When**: Tool is executed
**Then**: Command runs in project directory

**Given**: Tool config with `cwd: "repo"`
**When**: Tool is executed  
**Then**: Command runs in repository directory

**Given**: Tool config with `cwd: "switchboard"`
**When**: Tool is executed
**Then**: Command runs in switchboard directory

### Tool Validation

#### Test: Skip Bead with Missing Tool Config
**Given**:
- Bead has `tool:nonexistent-tool` label
- Project has no pipeline tool config for `nonexistent-tool`

**When**: Daemon evaluates the bead

**Then**:
- Bead is not claimed
- Warning is logged about missing tool config
- Bead remains in ready queue

## 3. Conflict Resolution Workflow

### Auto-Merge Failure Handling

#### Test: Create Conflict Resolution Bead on Merge Failure
**Given**:
- Agent completes successfully (exit code 0)
- Auto-merge to feature branch fails due to conflicts

**When**: Daemon processes completion

**Then**:
- Original bead is closed
- New integrate bead is created with conflict resolution instructions
- Integrate bead has appropriate parent/dependency relationships

#### Test: Conflict Bead Contains Proper Context
**Given**: Merge conflict occurs for `development` agent on branch `agents/bead-123-development`

**When**: Conflict resolution bead is created

**Then**: Bead description includes:
- Specific branch name that failed to merge
- Repository path where conflicts exist
- Step-by-step resolution instructions
- Reference to original bead context

## 4. Multi-Project Management

### Project Registry Building

#### Test: Build Registry from Valid Project Configs
**Given**:
- `switchboard.yaml` defines projects A and B
- Each project has valid `project.yaml` with repos, tools, pipelines

**When**: Registry is built

**Then**:
- Registry contains entries for both projects
- Each entry includes resolved paths, tool configs, pipeline definitions
- Agents directories are resolved to absolute paths

#### Test: Handle Missing Project Configs Gracefully
**Given**:
- `switchboard.yaml` references project C
- Project C directory exists but has no `project.yaml`

**When**: Registry is built

**Then**:
- Project C gets empty configuration
- No repos or pipelines are available for project C
- Daemon continues with other valid projects

### Cross-Project Isolation

#### Test: Agent Resolution is Project-Specific
**Given**:
- Project A has custom `development.md` agent
- Project B uses default `development.md` agent
- Both have beads requiring `development` agent

**When**: Daemon processes both beads

**Then**:
- Project A bead uses custom agent file
- Project B bead uses default agent file
- Each uses their project-specific tool configurations

## 5. Worker Process Management

### Process Lifecycle

#### Test: Track Worker Process States
**Given**: Agent worker is launched for a bead

**When**: Daemon tracks the process

**Then**:
- Process is added to active workers dict
- Process includes PID, agent name, repo path, worktree path
- Process exit code is polled each cycle

#### Test: Clean Up Completed Workers
**Given**:
- Worker process completes successfully
- Worktree auto-merge succeeds

**When**: Daemon detects completion

**Then**:
- Process is removed from active workers
- Worktree is cleaned up
- Bead is marked closed

#### Test: Clean Up Failed Workers
**Given**:
- Worker process fails
- Maximum retry attempts exceeded

**When**: Daemon detects failure

**Then**:
- Process is removed from active workers
- Worktree is cleaned up
- Bead is marked blocked

## 6. Integration Test Scenarios

### End-to-End Feature Workflow

#### Test: Complete TDD Pipeline Execution
**Given**:
- Epic with TDD → Interface → Tests → Development → Verify → Review pipeline
- All agent files exist and are functional
- Repository is clean with feature branch

**When**: Daemon processes the complete pipeline

**Then**:
- All beads execute in correct dependency order
- Each agent produces commits in worktree
- Auto-merges succeed at each step
- Epic completes when review finishes
- Feature branch contains all agent work

#### Test: Mixed Agent and Tool Pipeline
**Given**:
- Pipeline: Development → Verify → Tool:create-pr
- Tool configured to create GitHub PR

**When**: Pipeline executes

**Then**:
- Development agent produces code
- Verify agent validates the code
- Tool step creates PR without worktree
- All steps complete successfully

### Error Recovery Scenarios

#### Test: Recovery from Mid-Pipeline Failure
**Given**:
- 5-step pipeline where step 3 fails permanently
- Steps 1-2 completed successfully

**When**: Step 3 exceeds retry limit

**Then**:
- Steps 1-2 remain completed  
- Step 3 is blocked
- Steps 4-5 remain pending (dependencies not met)
- Epic remains open
- Manual intervention can unblock step 3

#### Test: Conflict Resolution During Pipeline
**Given**:
- Pipeline in progress with merge conflict at step 3
- Remaining steps depend on step 3

**When**: Conflict occurs

**Then**:
- Integrate bead is created for conflict resolution
- Original step 3 bead is closed
- Subsequent steps wait for integrate bead completion
- Pipeline resumes after conflict resolution

## Edge Cases and Boundary Conditions

### Resource Limits

#### Test: Handle Worktree Creation Failures
**Given**: Git worktree creation fails (disk space, permissions, etc.)
**When**: Daemon attempts to process agent bead
**Then**: Bead is requeued for retry, error is logged

#### Test: Handle Large Number of Concurrent Beads
**Given**: 100 ready beads in queue, max_workers = 5
**When**: Daemon processes queue
**Then**: Only 5 workers start, remaining beads wait, no resource exhaustion

### Configuration Edge Cases

#### Test: Handle Malformed Project Configurations
**Given**: Project.yaml has invalid YAML syntax
**When**: Registry is built
**Then**: Project is skipped with warning, daemon continues with other projects

#### Test: Handle Missing Repository Paths
**Given**: Project config references repo that doesn't exist on disk
**When**: Bead for that repo is processed
**Then**: Bead is skipped with warning about missing repo

## Acceptance Criteria

For this TDD specification to be considered complete:

1. ✅ **Comprehensive Coverage**: All major daemon workflows specified
2. ✅ **Clear Test Structure**: Given/When/Then format for every test
3. ✅ **Edge Case Handling**: Error conditions and resource limits covered  
4. ✅ **Integration Scenarios**: End-to-end workflows specified
5. ✅ **Performance Considerations**: Concurrent worker limits and queueing behavior
6. ✅ **Multi-Project Support**: Cross-project isolation and configuration management

## Implementation Notes

- Tests should use temporary directories and mock subprocess calls
- Database operations should be isolated using test-specific beads databases
- Git operations should use bare repositories for testing
- Process management tests should mock subprocess.Popen
- Integration tests should use real but minimal project configurations

These specifications provide the foundation for implementing comprehensive test coverage of Switchboard's core daemon functionality.