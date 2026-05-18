# Switchboard

AI agent pipeline that orchestrates Claude Code workers through a TDD workflow. Human describes a feature, switchboard creates a task DAG and runs specialized agents (TDD → Interface → Tests → Development → Verify → Review) in isolated git worktrees.

## How it works

```
Human → /intake "Add auth middleware"
         ↓
  Creates bead DAG (7 phases)
         ↓
  Switchboard daemon polls for ready beads
         ↓
  For each bead:
    1. Create git worktree (isolated branch)
    2. Launch Claude Code with agent prompt + bead context
    3. Agent reads code, writes files, commits
    4. Merge agent branch into feature branch
    5. Next agent picks up (sees previous agents' work)
         ↓
  Feature branch has complete implementation
```

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- [beads CLI](https://github.com/gastownhall/beads) (`bd`)
- Git
- Python 3.10+ with PyYAML (`pip install pyyaml`)

## Quick start

```bash
# 1. Clone into your workspace
cd my-workspace
git clone <switchboard-repo-url> switchboard

# 2. Run setup
./switchboard/setup.sh

# 3. Configure your project
vi project.yaml   # set your repos and verify commands

# 4. Start the router
python switchboard/agent_router/run.py

# 5. Create a feature (in a Claude Code session)
/intake "Add user authentication"
```

## Configuration

### project.yaml

Created by `setup.sh` in your workspace root. Defines your repos and pipeline:

```yaml
repos:
  - name: backend
    path: ./backend
    verify: "make test && make lint"
  - name: frontend
    path: ./frontend
    verify: "npm test && npm run lint"

pipeline:
  - tdd          # Test-first specifications
  - interface    # API/type design
  - tests        # Write test code (red phase)
  - development  # Implement code (green phase)
  - integrate    # Auto-merged by router; handles conflicts
  - verify       # Run quality gates
  - review       # Code review

settings:
  poll_interval: 10   # seconds between polls
  max_workers: 3      # concurrent agents
```

### Configuring coding tools

By default, all agents use Claude Code. You can use different tools for different agents:

```yaml
coding_tools:
  claude:
    command: ["claude", "-p", "{prompt_file}", "--output-format", "text", "--dangerously-skip-permissions"]
  goose:
    command: ["goose", "run", "--text", "{prompt_file}"]
  aider:
    command: ["aider", "--message-file", "{prompt_file}", "--yes-always"]

default_tool: claude

# Use goose for tests, aider for review, claude for everything else
agent_tools:
  tests: goose
  review: aider
```

Template variables in command arrays:
- `{prompt_file}` — path to file containing the full prompt (recommended)
- `{prompt}` — inline prompt text (may hit shell limits on large prompts)
- `{worktree}` — path to the agent's worktree

### Customizing the pipeline

Remove agents you don't need:

```yaml
# Minimal: just write code and verify
pipeline:
  - development
  - verify
```

```yaml
# No TDD: skip specs, go straight to tests
pipeline:
  - tests
  - development
  - verify
  - review
```

## Agents

| Agent | Role | Produces |
|-------|------|----------|
| `tdd` | Design test specs and acceptance criteria | Spec documents |
| `interface` | Design types, APIs, component signatures | Type stubs, interface files |
| `tests` | Write runnable test code (red phase) | Test files |
| `development` | Implement code to make tests pass | Implementation code |
| `integrate` | Resolve merge conflicts (only if auto-merge fails) | Conflict resolutions |
| `verify` | Run lint, typecheck, test suite | Pass/fail report |
| `review` | Code review the feature branch | Review findings |

### Adding custom agents

Create a `.md` file in `agents/` with frontmatter:

```markdown
---
name: my-agent
description: What this agent does
model: sonnet
---

You are the My-Agent. You do X.

## Context
Your assignment details are provided below under "Assignment Context".
Do NOT use `bd` commands.

## What You Do
1. Read your assignment context
2. Do the work
3. Commit your files

## Completion
Commit your work and exit.
```

Then add `my-agent` to your `pipeline` in `project.yaml`.

## Architecture

```
switchboard/
├── agent_router/          # Daemon that polls beads and launches workers
│   ├── run.py             # Main loop: poll → claim → worktree → launch → merge
│   ├── config.yaml        # Default settings
│   └── helpers/
│       ├── worker.py      # Claude Code process management + prompt building
│       └── worktree.py    # Git worktree lifecycle + merge logic
├── agents/                # Agent definitions (symlinked to .claude/agents/)
├── skills/intake/         # /intake slash command for DAG creation
├── formulas/              # Bead workflow templates
└── setup.sh               # Bootstrap script
```

### Merge strategy

Each agent works on its own branch (`agents/{bead-id}-{agent}`). When the agent completes:

1. Router tries `git merge` into the feature branch
2. **Success** → branch merged, next agent sees the work
3. **Conflict** → `git merge --abort`, creates an integrate bead for manual resolution

### Worktree lifecycle

1. `git worktree add` creates an isolated checkout from the feature branch
2. Agent runs `claude -p` in the worktree directory
3. On completion, worktree is removed and branch is cleaned up
4. If creation fails (stale state), router checks if another agent is active before cleaning up

## Monitoring

```bash
# Watch the router log
tail -f artifacts/switchboard.log

# See a specific agent's output
tail -f artifacts/logs/<bead-id>/stdout.log

# Check what was sent to an agent
cat artifacts/logs/<bead-id>/prompt.txt

# See agent commits on the feature branch
cd <repo> && git log --oneline feature/<slug>

# Check bead status
bd list --parent <epic-id>
```

## Troubleshooting

### Router crashes on worktree creation
Stale worktree from a previous killed run. The router retries automatically by cleaning up orphaned directories. If it persists:
```bash
cd <repo> && git worktree prune && git branch -D agents/<branch-name>
```

### Agent produces no commits
Check `artifacts/logs/<bead-id>/stdout.log` for the agent's output. Common causes:
- Agent didn't understand the task (improve bead description)
- Agent hit an error (check `stderr.log`)

### Beads stuck in progress
Router was killed mid-run. Reset them:
```bash
bd update <bead-id> --status=open --assignee=""
```
