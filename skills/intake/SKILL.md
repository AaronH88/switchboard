---
name: intake
description: Convert human feature requests into Bead DAGs for the switchboard agent router. Creates parent epic + child beads with chained dependencies. Never implements code directly.
---

# Intake Skill

Convert a human feature request into a structured Bead DAG that the switchboard executes.

## When to Use

The human describes a feature they want built. You create the bead workflow.

## Process

### 1. Read project config

Read `project.yaml` in the workspace root to discover:
- Available repos (names, paths, verify commands)
- Pipeline steps (which agents to use)

### 2. Clarify scope

Ask the human:
- What is the feature? (one sentence)
- Which repo? (list available repos from project.yaml)
- If both repos are needed, you will create **separate DAGs per repo**
- Acceptance criteria (what does "done" look like?)

If the human gave enough detail, skip clarification.

### 3. Determine repo per bead

Every bead MUST target exactly one repo. Never set `repo=both`.

**Single-repo feature:** All beads target the same repo.

**Cross-repo feature:** Create two separate DAGs — one per repo. Each DAG has its own epic, its own steps, and its own feature branch. The two DAGs are independent.

### 4. Create feature branch

Create the feature branch in each target repo and **leave it checked out** — the router creates worktrees from HEAD:

```bash
cd <repo-path> && git checkout -b feature/<slug> main
```

### 5. Build the graph JSON and create the DAG

**CRITICAL**: Use `bd create --graph` to create all beads atomically with complete descriptions, labels, and dependencies in a single command. Do NOT create beads individually — the router picks them up immediately.

Read the `pipeline` list from `project.yaml` to determine which agents to include. Build the graph JSON with only those agents.

For each repo in `project.yaml`, use its `verify` command in the verify bead description.

```json
{
  "nodes": [
    {
      "key": "epic",
      "title": "<feature name>",
      "type": "epic",
      "description": "<feature overview and acceptance criteria>"
    },
    {
      "key": "<agent>",
      "title": "<Agent>: <feature name>",
      "type": "task",
      "labels": ["agent:<agent>", "repo:<repo-name>"],
      "description": "<ENRICHED: specific context for this agent>"
    }
  ],
  "edges": [
    {"from_key": "<agent>", "to_key": "epic", "type": "parent"},
    {"from_key": "<agent2>", "to_key": "<agent1>", "type": "depends_on"}
  ]
}
```

Write this JSON to a temp file and create the DAG:

```bash
cat > /tmp/bead-graph.json <<'EOF'
{ ... complete JSON ... }
EOF
bd create --graph /tmp/bead-graph.json
```

### 6. Verify descriptions are complete

Each bead description MUST include feature-specific context (not generic). Check:
- **TDD**: Specific test scenarios, file paths, scope
- **Interface**: Specific methods/types to design, patterns to follow
- **Tests**: Which test files to create, test framework, specific test cases
- **Development**: Specific fixes/implementations, files to modify, guidelines
- **Integrate**: Standard (router auto-merges; integrate only handles conflicts)
- **Verify**: Use the verify command from project.yaml for the target repo
- **Review**: What to review, acceptance criteria to check

### 7. Confirm with human

```bash
bd list --parent <epic-id>
bd ready
```

Tell the human:
- Feature branch: `feature/<slug>`
- Repo: `<repo>`
- Epic bead: `<epic-id>`
- Steps: list of pipeline agents
- The feature branch must be checked out in the repo
- The switchboard (if already running) will pick up work automatically

## Rules

- **NEVER implement feature code directly**
- **NEVER use `bd mol pour`** — it creates beads with generic descriptions
- **NEVER create beads then update them** — the router picks up beads immediately
- Every bead MUST target exactly one repo
- For cross-repo features, create separate DAGs per repo
- Create pipeline steps in order with chained dependencies
- Set `agent:<name>` and `repo:<repo>` labels on every child bead
- **All descriptions must be complete at creation time**
- Read `project.yaml` for available repos and their verify commands

## Output

```
Created feature DAG:
  Epic: <epic-id> — <name>
  Repo: <repo>
  Branch: feature/<slug>
  Steps: <pipeline steps from project.yaml>

  The switchboard will pick up work automatically.
```
