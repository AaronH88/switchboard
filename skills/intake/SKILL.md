---
name: intake
description: Convert feature requests into Bead DAGs for the switchboard daemon. Creates an epic + pipeline beads with chained dependencies. Never implements code directly.
---

# Intake Skill

Convert a human feature request into a structured Bead DAG that the switchboard executes.

## When to Use

The human describes work they want done. You create the bead workflow.

## Process

### 1. Read project config

Read `project.yaml` in the current workspace to discover:
- Available repos (names, paths, verify commands)
- Available pipelines (named sequences of agents)

### 2. Clarify scope

Ask the human:
- What is the work? (one sentence)
- Which pipeline? (list available pipelines from project.yaml)
- Which repo? (list available repos from project.yaml)
- List any project-specific agents: read `agents_dir` from `project.yaml`, then list `.md` files in that directory that are NOT symlinks (symlinks are built-in agents from switchboard). Tell the human what custom agents are available so they can use them in pipelines.
- If multiple repos are needed, create **separate DAGs per repo**
- Acceptance criteria (what does "done" look like?)

If the human gave enough detail, skip clarification.

### 3. Determine the project name

Read `project.yaml` to find the project name. This goes into the `project:` label on every bead so the switchboard daemon knows which project config to use.

The project name comes from the workspace directory name or can be set explicitly in `project.yaml`.

### 4. Create feature branch

Create the feature branch in each target repo and **leave it checked out**:

```bash
cd <repo-path> && git checkout -b feature/<slug> main
```

### 5. Build the graph JSON and create the DAG

**CRITICAL**: Use `bd create --graph` to create all beads atomically.

Read the selected pipeline from `project.yaml` to determine which agents to include. Build the graph JSON with only those agents, chained in order.

Every bead MUST have these labels:
- `agent:<agent-name>` — which agent handles it
- `repo:<repo-name>` — which repo to work in
- `project:<project-name>` — which project this belongs to

```json
{
  "nodes": [
    {
      "key": "epic",
      "title": "<work description>",
      "type": "epic",
      "description": "<overview and acceptance criteria>"
    },
    {
      "key": "<agent>",
      "title": "<Agent>: <work description>",
      "type": "task",
      "labels": ["agent:<agent>", "repo:<repo-name>", "project:<project-name>"],
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

Each bead description MUST include work-specific context. For verify beads, use the verify command from the repo's entry in `project.yaml`.

### 7. Confirm with human

```bash
bd list --parent <epic-id>
bd ready
```

Tell the human:
- Feature branch: `feature/<slug>`
- Repo: `<repo>`
- Pipeline: `<pipeline-name>` with its steps
- Epic bead: `<epic-id>`
- The switchboard daemon will pick up work automatically

## Rules

- **NEVER implement code directly**
- **NEVER create beads then update them** — the daemon picks up beads immediately
- Every bead MUST have `agent:`, `repo:`, and `project:` labels
- For multi-repo work, create separate DAGs per repo
- Pipeline steps are chained in the order defined in `project.yaml`
- **All descriptions must be complete at creation time**
- Read `project.yaml` for available repos, pipelines, and verify commands

## Output

```
Created DAG:
  Epic: <epic-id> — <description>
  Project: <project-name>
  Repo: <repo>
  Pipeline: <pipeline-name> → <step1> → <step2> → ...

  The switchboard daemon will pick up work automatically.
```
