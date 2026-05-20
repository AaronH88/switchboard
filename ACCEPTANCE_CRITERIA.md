# Acceptance Criteria: Switchboard Core Testing

## Objective

Establish comprehensive test coverage for Switchboard's daemon functionality, ensuring reliable multi-project AI agent pipeline orchestration.

## Success Criteria

### 1. Daemon Core Functionality ✅

The switchboard daemon must:

- **Process agent beads**: Successfully claim, create worktrees, and launch coding tools for agent-labeled beads
- **Process tool beads**: Successfully claim and execute pipeline tools without worktrees
- **Respect worker limits**: Never exceed configured max_workers, queue additional beads appropriately
- **Handle dependencies**: Skip beads with open dependencies, process them when dependencies clear
- **Manage epic lifecycles**: Auto-close epics when all children complete, keep open otherwise
- **Retry failed work**: Requeue failed beads up to max_attempts, then block permanently
- **Clean up resources**: Remove worktrees and processes for completed/failed work

**Acceptance Test**: Full daemon loop processes mixed agent/tool beads with dependencies under load.

### 2. Pipeline Tool Execution ✅

Pipeline tools must:

- **Variable substitution**: Replace all template variables (`{repo}`, `{branch}`, `{epic_title}`, etc.) correctly
- **Working directory control**: Execute in correct directory based on `cwd` setting (repo/project/switchboard)
- **Validation**: Skip beads with missing tool configurations, log warnings appropriately
- **Process tracking**: Track tool processes same as agent processes for completion detection

**Acceptance Test**: Tool pipeline creates GitHub PR with correct title/branch after code changes.

### 3. Conflict Resolution ✅

When auto-merge fails:

- **Conflict detection**: Detect merge conflicts reliably after agent completion
- **Integrate bead creation**: Auto-create integrate bead with proper context and dependencies
- **Workflow continuation**: Pipeline resumes after conflict resolution bead completes
- **Context preservation**: Conflict resolution instructions include all necessary details

**Acceptance Test**: Simulate merge conflict mid-pipeline, verify integrate bead creation and resolution.

### 4. Multi-Project Management ✅

The daemon must:

- **Registry building**: Parse all project configs, resolve paths, handle missing configs gracefully
- **Project isolation**: Use correct agent files, tool configs, and repos per project
- **Cross-project concurrency**: Process beads from multiple projects simultaneously
- **Configuration reloading**: Pick up project config changes on next poll cycle

**Acceptance Test**: Two projects with different agent configurations process work simultaneously.

### 5. Error Handling and Recovery ✅

System must gracefully handle:

- **Worktree creation failures**: Requeue beads, don't crash daemon
- **Missing repositories**: Skip beads with warnings, continue processing others  
- **Malformed configurations**: Skip problematic projects, load valid ones
- **Process failures**: Retry within limits, block after max attempts
- **Resource exhaustion**: Queue beads when at worker limits

**Acceptance Test**: Inject various failure modes, verify daemon continues operating.

### 6. End-to-End Integration ✅

Complete workflows must:

- **Execute pipelines**: TDD → Interface → Tests → Development → Verify → Review flows
- **Mixed pipelines**: Agent steps + tool steps in same pipeline
- **Dependency chains**: Respect bead dependencies throughout execution
- **Feature branch management**: All agent work merges cleanly to feature branch
- **Epic completion**: Mark epics complete when all children finish

**Acceptance Test**: Full feature workflow from intake to PR creation works end-to-end.

## Performance Requirements

- **Startup time**: < 5 seconds to start daemon and load project registry
- **Poll cycle**: < 2 seconds to evaluate all ready beads (up to 100 beads)
- **Worker spawn**: < 10 seconds to create worktree and launch coding tool
- **Memory usage**: < 100MB base + 50MB per active worker
- **Concurrent workers**: Support up to 10 concurrent workers per daemon

## Quality Gates

### Test Coverage
- **Unit tests**: 90%+ coverage of all daemon functions
- **Integration tests**: End-to-end workflows with real git repos and mock tools
- **Error injection tests**: All error conditions tested with appropriate responses

### Code Quality
- **Linting**: All code passes ruff linting without warnings
- **Type checking**: All code passes mypy strict type checking  
- **Documentation**: All public functions have docstrings with examples

### Reliability
- **No crashes**: Daemon handles all error conditions without terminating
- **Resource cleanup**: No leaked processes, worktrees, or file handles
- **State consistency**: Bead states remain consistent with actual work status

## Test Data Requirements

### Project Configurations
- **Minimal project**: Single repo, basic pipeline, default tools
- **Multi-repo project**: Frontend + backend repos with different verify commands
- **BYOA project**: Custom agents directory with overrides
- **Tool-heavy project**: Pipeline with multiple tool steps

### Bead Scenarios  
- **Simple epic**: 3-step linear pipeline (tdd → tests → development)
- **Complex epic**: 7-step full pipeline with mixed agents and tools
- **Parallel epic**: Multiple independent task beads under same epic
- **Dependent epics**: Epic B depends on Epic A completion

### Error Scenarios
- **Conflict epic**: Guaranteed merge conflicts in development step
- **Failure epic**: Agent step that always fails for retry testing
- **Missing config**: References to non-existent agents, tools, repos

## Definition of Done

This feature is complete when:

1. ✅ All acceptance tests pass consistently
2. ✅ Test coverage meets quality gates (90%+ unit, full integration)
3. ✅ Performance requirements met under load testing
4. ✅ Error injection testing passes all scenarios
5. ✅ Documentation includes setup, configuration, and troubleshooting guides
6. ✅ Deployment can run multiple projects simultaneously in production

## Risk Mitigation

### Identified Risks
- **Process zombies**: Workers not cleaned up properly on daemon shutdown
- **Git state corruption**: Merge conflicts leave repos in bad state
- **Configuration drift**: Project configs change while daemon is running  
- **Resource exhaustion**: Too many workers exceed system limits

### Mitigation Strategies
- **Graceful shutdown**: SIGTERM handler waits for active workers to complete
- **Git safety**: Validate repo state before and after operations
- **Config watching**: Reload project registry on config file changes
- **Resource monitoring**: Track and limit worker memory/disk usage

## Success Metrics

- **Reliability**: 99.9% uptime in production with multiple projects
- **Throughput**: Process 50+ beads per hour with 5 concurrent workers  
- **User satisfaction**: Zero reports of lost work or corruption
- **Maintainability**: New agent types can be added without daemon changes
- **Scalability**: Single daemon instance supports 10+ active projects

This specification ensures Switchboard provides robust, reliable multi-project AI agent orchestration ready for production deployment.