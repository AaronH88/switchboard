"""Switchboard worker management — launches coding tools in worktrees."""

import json
import logging
import os
import re
import subprocess
from pathlib import Path

log = logging.getLogger("switchboard.worker")

DEFAULT_TOOL_CONFIG = {
    "command": ["claude", "-p", "{prompt_file}", "--output-format", "text", "--dangerously-skip-permissions"],
}


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (---...---) from agent definition."""
    return re.sub(r"^---\n.*?\n---\n*", "", text, count=1, flags=re.DOTALL)


def _format_bead_context(bead: dict) -> str:
    """Format bead details into a context block for the prompt."""
    lines = [f"## Bead: {bead.get('id', 'unknown')}"]
    lines.append(f"**Title:** {bead.get('title', 'N/A')}")
    lines.append(f"**Status:** {bead.get('status', 'N/A')}")
    if bead.get("description"):
        lines.append(f"\n### Description\n{bead['description']}")
    if bead.get("parent"):
        lines.append(f"\n**Parent Epic:** {bead['parent']}")
    deps = bead.get("dependencies") or []
    for dep in deps:
        if dep.get("dependency_type") == "parent-child" and dep.get("description"):
            lines.append(f"\n### Epic Context\n{dep['description']}")
    return "\n".join(lines)


def _get_recent_feature_commits(repo_abs: str, count: int = 15) -> str:
    """Get recent commits on the feature branch to show previous agents' work."""
    result = subprocess.run(
        ["git", "-C", repo_abs, "log", "--oneline", f"-{count}",
         "--format=%h %s", "--diff-filter=A", "--name-only"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ""
    return result.stdout.strip()


def _build_tool_command(
    tool_config: dict,
    prompt_file: str,
    prompt_text: str,
    worktree_path: str,
) -> list[str]:
    """Build the command array from a tool template with variable substitution."""
    cmd = []
    for part in tool_config.get("command", DEFAULT_TOOL_CONFIG["command"]):
        part = part.replace("{prompt_file}", prompt_file)
        part = part.replace("{prompt}", prompt_text)
        part = part.replace("{worktree}", worktree_path)
        cmd.append(part)
    return cmd


def build_prompt(
    agent: str,
    bead_id: str,
    worktree_path: str,
    agent_file: Path | None = None,
    bead_context: str = "",
    repo_abs: str = "",
) -> str:
    agent_def = ""
    if agent_file and agent_file.exists():
        agent_def = strip_frontmatter(agent_file.read_text())
    parts = [agent_def, f"\nBead: {bead_id}", f"Worktree: {worktree_path}"]
    if bead_context:
        parts.append(f"\n# Assignment Context\n\n{bead_context}")
    if repo_abs:
        recent = _get_recent_feature_commits(repo_abs)
        if recent:
            parts.append(f"\n# Previous Agents' Work\n\nThese commits are on the feature branch (already in your worktree):\n```\n{recent}\n```\nRead these files to understand what previous agents produced.")
    parts.append(
        "\n# Important"
        "\n- You are running in a git worktree. All file edits and git commits happen here."
        "\n- Commit your work before finishing: `git add <files> && git commit -m '...'`"
        "\n- Do NOT use `bd` commands — the beads DB is not available in this worktree."
        "\n  All bead context is provided above."
    )
    return "\n".join(parts)


def fetch_bead_context(bead_id: str, workspace: str) -> str:
    """Fetch bead details from the workspace beads DB and format as prompt context."""
    result = subprocess.run(
        ["bd", "show", bead_id, "--json"],
        capture_output=True,
        text=True,
        cwd=workspace,
    )
    if result.returncode != 0:
        return ""
    try:
        data = json.loads(result.stdout)
        bead = data[0] if isinstance(data, list) else data
        return _format_bead_context(bead)
    except (json.JSONDecodeError, IndexError):
        return ""


def launch(
    agent: str,
    bead_id: str,
    worktree_path: str,
    agent_file: Path | None,
    artifacts_dir: str,
    bead_context: str = "",
    repo: str = "",
    tool_config: dict | None = None,
) -> subprocess.Popen:
    log_dir = Path(artifacts_dir) / "logs" / bead_id
    log_dir.mkdir(parents=True, exist_ok=True)

    repo_abs = os.path.abspath(repo) if repo else ""
    prompt = build_prompt(agent, bead_id, worktree_path, agent_file, bead_context, repo_abs)

    prompt_file = str(log_dir / "prompt.txt")
    Path(prompt_file).write_text(prompt)

    config = tool_config or DEFAULT_TOOL_CONFIG
    cmd = _build_tool_command(config, prompt_file, prompt, worktree_path)

    tool_name = cmd[0] if cmd else "unknown"
    log.info("Launching %s for %s (agent: %s)", tool_name, bead_id, agent)

    stdout_log = open(log_dir / "stdout.log", "w")
    stderr_log = open(log_dir / "stderr.log", "w")

    proc = subprocess.Popen(
        cmd,
        cwd=worktree_path,
        stdout=stdout_log,
        stderr=stderr_log,
    )
    log.info("Launched worker PID %d for %s (agent: %s, tool: %s)", proc.pid, bead_id, agent, tool_name)
    return proc


def check(proc: subprocess.Popen) -> int | None:
    return proc.poll()
