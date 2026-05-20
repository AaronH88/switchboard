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

**CRITICAL**: Pipeline edges MUST use `"type": "blocks"`, NOT `"type": "depends_on"`. The `depends_on` type creates informational links that do NOT prevent the daemon from picking up downstream steps. Only `blocks` makes a bead wait until its upstream dependency is closed.

Read the selected pipeline from `project.yaml` to determine which steps to include. Build the graph JSON with those steps chained in order.

Pipeline steps are either **agents** (bare names like `development`) or **tools** (prefixed like `tool:create-pr`).

**For agent steps**, use the `agent:` label:
- `agent:<agent-name>` — which agent handles it

**For tool steps** (prefixed with `tool:` in the pipeline), use the `tool:` label:
- `tool:<tool-name>` — which pipeline tool to run

Every bead MUST also have:
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
      "key": "<step>",
      "title": "<Step>: <work description>",
      "type": "task",
      "labels": ["agent:<agent>", "repo:<repo-name>", "project:<project-name>"],
      "description": "<ENRICHED: specific context for this step>"
    },
    {
      "key": "<tool-step>",
      "title": "Tool: <tool-name>",
      "type": "task",
      "labels": ["tool:<tool-name>", "repo:<repo-name>", "project:<project-name>"],
      "description": "Run pipeline tool: <tool-name>"
    }
  ],
  "edges": [
    {"from_key": "<step>", "to_key": "epic", "type": "parent"},
    {"from_key": "<step2>", "to_key": "<step1>", "type": "blocks"}
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

### 6. Verify blocking dependencies

After creating the graph, run `bd ready` and `bd blocked` to confirm:
- Only the **first** pipeline step (and the epic) should appear in `bd ready`
- All downstream steps should appear in `bd blocked`

If all steps show as ready, the edges used `depends_on` instead of `blocks` — delete and recreate.

### 7. Verify descriptions are complete

Each bead description MUST include work-specific context. For verify beads, use the verify command from the repo's entry in `project.yaml`.

### 8. Confirm with human

```bash
bd list --parent <epic-id>
bd ready
bd blocked
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
- Every bead MUST have `repo:` and `project:` labels, plus either `agent:` (for agent steps) or `tool:` (for tool steps)
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
