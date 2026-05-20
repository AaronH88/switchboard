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
  Switchboard daemon picks up beads (respects dependency chains)
                         ↓
  For each bead:
    Agent step:                          Tool step (tool:create-pr):
    1. Resolve project + repo            1. Resolve project + repo
    2. Create git worktree               2. Run command directly (no worktree)
    3. Launch coding tool                3. Close bead on success
    4. Agent works, commits
    5. Auto-merge into feature branch
    6. Next step picks up
                         ↓
  Epic completes when all children close
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
├── .claude/agents/                  # Symlinked built-ins + project-specific agents
│   ├── development.md → symlink     # Built-in from switchboard
│   ├── verify.md → symlink          # Built-in from switchboard
│   └── go-security-scan.md          # Project-specific (BYOA)
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

# Optional: project-specific agents (overrides built-in agents of the same name)
agents_dir: .claude/agents

pipelines:
  dev: [tdd, interface, tests, development, verify, review]
  quick-fix: [development, verify]
  review: [review]
  docs: [docs-writer, verify]
  deploy: [development, verify, tool:create-pr]  # Mix agents and tools

# Shell commands that run as pipeline steps (no worktree, no AI)
pipeline_tools:
  create-pr:
    command: ["gh", "pr", "create", "--title", "[switchboard] {epic_title}", "--head", "{branch}"]
    cwd: repo

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

Pipelines are named sequences of agents and/or tool steps:

```yaml
pipelines:
  dev:        [tdd, interface, tests, development, verify, review]  # Full TDD
  quick-fix:  [development, verify]                                  # Fast bugfix
  review:     [review]                                               # PR review
  test-only:  [tdd, tests, verify]                                   # Add coverage
  deploy:     [development, verify, tool:create-pr]                  # Code + PR
```

Steps prefixed with `tool:` run shell commands (see [Pipeline tools](#pipeline-tools)). All other steps are agents.

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

### Pipeline tools

Pipeline steps prefixed with `tool:` run shell commands directly — no worktree, no AI agent. Useful for PR creation, notifications, deployments, or any scripted action.

```yaml
pipeline_tools:
  create-pr:
    command: ["gh", "pr", "create", "--title", "[switchboard] {epic_title}", "--head", "{branch}"]
    cwd: repo
  notify:
    command: ["curl", "-X", "POST", "-d", "Done: {epic_title}", "https://hooks.slack.com/..."]
    cwd: project
```

Template variables: `{repo}`, `{branch}`, `{bead_id}`, `{epic_id}`, `{epic_title}`, `{project}`

The `cwd` option controls where the command runs: `repo` (default), `project`, or `switchboard`.

### Bring Your Own Agents (BYOA)

Projects can define their own agents alongside switchboard's built-ins. Set `agents_dir` in `project.yaml`:

```yaml
agents_dir: .claude/agents
```

The daemon checks the project's agents directory first, then falls back to switchboard's built-in agents. This means projects can:
- Add project-specific agents (e.g., `go-security-scan.md`)
- Override built-in agents (e.g., a custom `verify.md` with project-specific checks)

Agent format is the same — Markdown with YAML frontmatter:

```markdown
---
name: go-security-scan
description: Run gosec and custom security checks
---

You are a security scanning agent. ...
```

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

**Project-specific agents** (recommended): Add a `.md` file to your project's `agents_dir` (see [BYOA](#bring-your-own-agents-byoa)):

```bash
# In your project
echo '---\nname: docs-writer\ndescription: Write docs\n---\nYou are the Documentation agent.' \
  > .claude/agents/docs-writer.md
```

**Global agents**: Add a `.md` file to switchboard's `agents/` directory. Available to all projects.

Then reference it in a pipeline: `docs: [docs-writer, verify]`

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
