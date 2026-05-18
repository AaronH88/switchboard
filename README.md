# Switchboard

AI agent pipeline that orchestrates coding tools through customizable workflows. One daemon manages multiple projects. Each project defines its own repos, pipelines, and tool preferences.

## How it works

```
Human (in project-a) → /intake "Fix the auth bug"
                         ↓
  Asks: which pipeline? which repo?
                         ↓
  Creates bead DAG → shared switchboard DB
                         ↓
  Switchboard daemon picks up beads
                         ↓
  For each bead:
    1. Resolve project + repo from labels
    2. Create git worktree in the repo
    3. Launch coding tool (Claude, Goose, Aider, etc.)
    4. Agent works, commits to branch
    5. Auto-merge into feature branch
    6. Next agent picks up (sees previous work)
```

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (or another coding tool)
- [beads CLI](https://github.com/gastownhall/beads) (`bd`)
- Git
- Python 3.10+ with PyYAML (`pip install pyyaml`)

## Quick start

```bash
# 1. Clone switchboard
git clone https://github.com/AaronH88/switchboard.git ~/.switchboard

# 2. Set up a project
cd ~/my-project
~/.switchboard/setup.sh

# 3. Edit project config
vi project.yaml   # set repos, pipelines, tools

# 4. Start the daemon (manages all registered projects)
python ~/.switchboard/agent_router/run.py

# 5. Create work (in a Claude Code session inside your project)
/intake "Add user authentication"
```

## Architecture

```
~/.switchboard/                      # Central install (one per machine)
├── agent_router/run.py              # Single daemon for all projects
├── switchboard.yaml                 # Project registry
├── .beads/                          # Shared beads DB
├── agents/                          # Agent building blocks
├── skills/intake/                   # /intake skill (symlinked into projects)
├── artifacts/                       # Logs organized by bead
└── formulas/                        # Workflow templates

~/project-a/                         # Your project
├── .claude/agents/ → symlinks       # Agents from switchboard
├── .claude/skills/intake/ → symlink # Intake skill from switchboard
├── project.yaml                     # Project-specific config
└── src/                             # Your code

~/project-b/                         # Another project
├── .claude/agents/ → symlinks
├── project.yaml
└── ...
```

## Configuration

### switchboard.yaml (central)

Lists all projects the daemon manages:

```yaml
projects:
  my-webapp:
    path: /home/user/my-webapp
  cli-tool:
    path: /home/user/cli-tool
  mobile-app:
    path: /home/user/mobile-app
```

### project.yaml (per-project)

Each project configures its repos, pipelines, and coding tools:

```yaml
repos:
  - name: api
    path: ./api
    verify: "make test && make lint"
  - name: frontend
    path: ./frontend
    verify: "npm test && npm run lint"

pipelines:
  dev: [tdd, interface, tests, development, verify, review]
  quick-fix: [development, verify]
  review: [review]
  docs: [docs-writer, verify]
  test-only: [tdd, tests, verify]

coding_tools:
  claude:
    command: ["claude", "-p", "{prompt_file}", "--output-format", "text", "--dangerously-skip-permissions"]
  goose:
    command: ["goose", "run", "--text", "{prompt_file}"]

default_tool: claude

agent_tools:
  tests: goose
  review: claude
```

### Named pipelines

Pipelines are named sequences of agents. Different operations use different pipelines:

```yaml
pipelines:
  dev:        [tdd, interface, tests, development, verify, review]  # Full TDD
  quick-fix:  [development, verify]                                  # Fast bugfix
  review:     [review]                                               # PR review
  test-only:  [tdd, tests, verify]                                   # Add coverage
  docs:       [docs-writer, verify]                                  # Documentation
```

When you run `/intake`, it asks which pipeline to use.

### Configuring coding tools

Different tools for different agents:

```yaml
coding_tools:
  claude:
    command: ["claude", "-p", "{prompt_file}", "--output-format", "text", "--dangerously-skip-permissions"]
  goose:
    command: ["goose", "run", "--text", "{prompt_file}"]
  aider:
    command: ["aider", "--message-file", "{prompt_file}", "--yes-always"]

default_tool: claude

agent_tools:
  tests: goose      # Use goose for writing tests
  review: aider     # Use aider for code review
```

Template variables:
- `{prompt_file}` — path to file containing the prompt (recommended)
- `{prompt}` — inline prompt text
- `{worktree}` — path to the agent's worktree

## Built-in agents

| Agent | Role | Produces |
|-------|------|----------|
| `tdd` | Design test specs and acceptance criteria | Spec documents |
| `interface` | Design types, APIs, component signatures | Type stubs |
| `tests` | Write runnable test code (red phase) | Test files |
| `development` | Implement code to make tests pass | Implementation |
| `integrate` | Resolve merge conflicts (auto-merge handles the rest) | Conflict resolutions |
| `verify` | Run lint, typecheck, test suite | Pass/fail report |
| `review` | Code review the feature branch | Review findings |

### Adding custom agents

Create a `.md` file in `agents/`:

```markdown
---
name: docs-writer
description: Write project documentation
---

You are the Documentation agent. ...
```

Then use it in a pipeline: `docs: [docs-writer, verify]`

## Monitoring

```bash
# Daemon log
tail -f ~/.switchboard/artifacts/switchboard.log

# Specific agent output
tail -f ~/.switchboard/artifacts/logs/<bead-id>/stdout.log

# What was sent to an agent
cat ~/.switchboard/artifacts/logs/<bead-id>/prompt.txt

# Agent commits on the feature branch
cd <repo> && git log --oneline feature/<slug>

# Bead status
cd ~/.switchboard && bd list
```

## Adding a new project

```bash
cd ~/new-project
~/.switchboard/setup.sh --project new-project
vi project.yaml  # configure repos, pipelines, tools
# Daemon picks it up automatically on next poll
```

## Troubleshooting

### Router crashes on worktree creation
Stale state from a previous killed run. The router retries automatically. If it persists:
```bash
cd <repo> && git worktree prune && git branch -D agents/<branch>
```

### Agent produces no commits
Check `~/.switchboard/artifacts/logs/<bead-id>/stdout.log`. Common causes:
- Bead description too vague (improve it)
- Agent hit an error (check `stderr.log`)

### Beads stuck in progress
```bash
cd ~/.switchboard && bd update <bead-id> --status=open --assignee=""
```
