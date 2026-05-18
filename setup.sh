#!/bin/bash
# Switchboard setup — run from a project workspace to connect it to switchboard.
#
# Usage:
#   /path/to/switchboard/setup.sh                    # Set up current directory as a project
#   /path/to/switchboard/setup.sh --project my-app   # Set up with explicit project name

set -e

SWITCHBOARD_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(pwd)"
PROJECT_NAME=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --project) PROJECT_NAME="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ "$SWITCHBOARD_DIR" = "$PROJECT_DIR" ]; then
  echo "Error: Run this from your project workspace, not from inside switchboard/"
  echo "Usage: /path/to/switchboard/setup.sh"
  exit 1
fi

if [ -z "$PROJECT_NAME" ]; then
  PROJECT_NAME="$(basename "$PROJECT_DIR")"
fi

echo "Setting up Switchboard for project: $PROJECT_NAME"
echo "  Project: $PROJECT_DIR"
echo "  Switchboard: $SWITCHBOARD_DIR"

# Symlink pipeline agents into project's .claude/agents/
mkdir -p "$PROJECT_DIR/.claude/agents"
for agent in "$SWITCHBOARD_DIR/agents/"*.md; do
  name="$(basename "$agent")"
  if [ ! -e "$PROJECT_DIR/.claude/agents/$name" ]; then
    ln -sf "$agent" "$PROJECT_DIR/.claude/agents/$name"
    echo "  Linked agent: $name"
  else
    echo "  Skipped agent (exists): $name"
  fi
done

# Symlink intake skill
mkdir -p "$PROJECT_DIR/.claude/skills/intake"
if [ ! -e "$PROJECT_DIR/.claude/skills/intake/SKILL.md" ]; then
  ln -sf "$SWITCHBOARD_DIR/skills/intake/SKILL.md" "$PROJECT_DIR/.claude/skills/intake/SKILL.md"
  echo "  Linked skill: intake"
else
  echo "  Skipped skill (exists): intake"
fi

# Copy project.yaml template (don't overwrite)
if [ ! -e "$PROJECT_DIR/project.yaml" ]; then
  cp "$SWITCHBOARD_DIR/project.yaml.example" "$PROJECT_DIR/project.yaml"
  echo "  Created project.yaml — edit this to configure repos and pipelines"
else
  echo "  Skipped project.yaml (exists)"
fi

# Register project in switchboard.yaml
SB_CONFIG="$SWITCHBOARD_DIR/switchboard.yaml"
if [ ! -e "$SB_CONFIG" ]; then
  cp "$SWITCHBOARD_DIR/switchboard.yaml.example" "$SB_CONFIG"
fi

if grep -q "^  $PROJECT_NAME:" "$SB_CONFIG" 2>/dev/null; then
  echo "  Project '$PROJECT_NAME' already registered in switchboard.yaml"
else
  echo "  $PROJECT_NAME:" >> "$SB_CONFIG"
  echo "    path: $PROJECT_DIR" >> "$SB_CONFIG"
  echo "  Registered project '$PROJECT_NAME' in switchboard.yaml"
fi

# Init beads in switchboard dir if needed
if [ ! -d "$SWITCHBOARD_DIR/.beads/embeddeddolt" ]; then
  (cd "$SWITCHBOARD_DIR" && bd init 2>/dev/null) && \
    echo "  Initialized shared beads database" || \
    echo "  Warning: bd init failed — install beads CLI: https://github.com/gastownhall/beads"
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit $PROJECT_DIR/project.yaml — configure repos and pipelines"
echo "  2. Start the daemon: python $SWITCHBOARD_DIR/agent_router/run.py"
echo "  3. Use /intake in Claude Code to create work DAGs"
