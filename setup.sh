#!/bin/bash
# Switchboard setup — run this from your workspace root.
# Usage: ./switchboard/setup.sh

set -e

SWITCHBOARD_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(pwd)"

if [ "$SWITCHBOARD_DIR" = "$WORKSPACE" ]; then
  echo "Error: Run this script from your workspace root, not from inside switchboard/"
  echo "Usage: ./switchboard/setup.sh"
  exit 1
fi

echo "Setting up Switchboard in: $WORKSPACE"
echo "Switchboard location: $SWITCHBOARD_DIR"

# Symlink pipeline agents into .claude/agents/
mkdir -p "$WORKSPACE/.claude/agents"
for agent in "$SWITCHBOARD_DIR/agents/"*.md; do
  name="$(basename "$agent")"
  if [ ! -e "$WORKSPACE/.claude/agents/$name" ]; then
    ln -sf "$agent" "$WORKSPACE/.claude/agents/$name"
    echo "  Linked agent: $name"
  else
    echo "  Skipped agent (exists): $name"
  fi
done

# Symlink intake skill
mkdir -p "$WORKSPACE/.claude/skills/intake"
if [ ! -e "$WORKSPACE/.claude/skills/intake/SKILL.md" ]; then
  ln -sf "$SWITCHBOARD_DIR/skills/intake/SKILL.md" "$WORKSPACE/.claude/skills/intake/SKILL.md"
  echo "  Linked skill: intake"
else
  echo "  Skipped skill (exists): intake"
fi

# Copy beads formula (don't overwrite)
mkdir -p "$WORKSPACE/.beads/formulas"
cp -n "$SWITCHBOARD_DIR/formulas/feature.formula.json" "$WORKSPACE/.beads/formulas/" 2>/dev/null && \
  echo "  Copied formula: feature.formula.json" || \
  echo "  Skipped formula (exists): feature.formula.json"

# Copy project.yaml template (don't overwrite)
if [ ! -e "$WORKSPACE/project.yaml" ]; then
  cp "$SWITCHBOARD_DIR/project.yaml.example" "$WORKSPACE/project.yaml"
  echo "  Created project.yaml — edit this to configure your repos"
else
  echo "  Skipped project.yaml (exists)"
fi

# Init beads if needed
if [ ! -d "$WORKSPACE/.beads/embeddeddolt" ]; then
  (cd "$WORKSPACE" && bd init 2>/dev/null) && \
    echo "  Initialized beads database" || \
    echo "  Warning: bd init failed — install beads CLI: https://github.com/gastownhall/beads"
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit project.yaml to configure your repos and pipeline"
echo "  2. Start the router: python switchboard/agent_router/run.py"
echo "  3. Use /intake to create feature DAGs"
