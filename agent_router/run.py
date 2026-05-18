#!/usr/bin/env python3
"""Switchboard — polls bd for ready beads and launches Claude Code workers."""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import worktree, worker

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("switchboard")


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_project() -> dict:
    project_path = Path(WORKSPACE) / "project.yaml"
    if not project_path.exists():
        return {}
    with open(project_path) as f:
        return yaml.safe_load(f) or {}


def get_ready_beads() -> list[dict]:
    result = subprocess.run(
        ["bd", "ready", "--json"],
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        log.warning("Failed to parse bd ready output")
        return []


def get_bead_metadata(bead_id: str) -> dict:
    result = subprocess.run(
        ["bd", "show", bead_id, "--json"],
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )
    if result.returncode != 0:
        return {}
    try:
        data = json.loads(result.stdout)
        if isinstance(data, list):
            return data[0] if data else {}
        return data
    except (json.JSONDecodeError, IndexError):
        return {}


def extract_agent(bead: dict) -> str | None:
    metadata = bead.get("metadata") or {}
    if "agent" in metadata:
        return metadata["agent"]
    for label in bead.get("labels") or []:
        if label.startswith("agent:"):
            return label.split(":", 1)[1]
    return None


def extract_repo(bead: dict) -> str | None:
    metadata = bead.get("metadata") or {}
    repo = metadata.get("repo")
    if repo:
        return repo
    for label in bead.get("labels") or []:
        if label.startswith("repo:"):
            return label.split(":", 1)[1]
    return None


def claim_bead(bead_id: str) -> bool:
    result = subprocess.run(
        ["bd", "update", bead_id, "--claim"],
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )
    return result.returncode == 0


def close_bead(bead_id: str) -> None:
    subprocess.run(
        ["bd", "close", bead_id],
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )


def requeue_bead(bead_id: str, attempt: int) -> None:
    subprocess.run(
        ["bd", "update", bead_id, "--set-metadata", f"attempt={attempt}"],
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )
    subprocess.run(
        ["bd", "update", bead_id, "--status", "open"],
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )


def block_bead(bead_id: str) -> None:
    subprocess.run(
        ["bd", "update", bead_id, "--status", "blocked"],
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )


def _create_conflict_bead(bead_id: str, agent: str, repo: str) -> None:
    """Create an integrate bead to resolve merge conflicts."""
    branch = f"agents/{bead_id}-{agent}"
    title = f"Resolve merge conflict: {branch} into feature branch"
    desc = (
        f"The {agent} agent completed work on branch `{branch}` in repo `{repo}`, "
        f"but merging into the feature branch failed due to conflicts.\n\n"
        f"## Steps\n"
        f"1. Check out the feature branch in `{repo}`\n"
        f"2. Run `git merge {branch}` and resolve conflicts\n"
        f"3. Commit the resolution\n"
    )
    bead = get_bead_metadata(bead_id)
    parent = bead.get("parent", "")
    cmd = [
        "bd", "create",
        "--title", title,
        "--description", desc,
        "--type", "task",
        "--priority", "1",
        "--add-label", "agent:integrate",
        "--add-label", f"repo:{repo}",
    ]
    if parent:
        cmd.extend(["--parent", parent])
    subprocess.run(cmd, capture_output=True, text=True, cwd=WORKSPACE)
    log.info("Created conflict resolution bead for %s", branch)


def main():
    config = load_config()
    project = load_project()

    settings = project.get("settings", {})
    poll_interval = settings.get("poll_interval", config.get("poll_interval", 10))
    max_workers = settings.get("max_workers", config.get("max_workers", 3))

    # Tool configuration
    tools = project.get("coding_tools", {})
    default_tool_name = project.get("default_tool", "claude")
    agent_tools = project.get("agent_tools", {})
    artifacts_dir = os.path.join(WORKSPACE, config.get("artifacts_dir", "artifacts"))
    worktrees_dir = config.get("worktrees_dir", "worktrees")
    agents_dir = os.path.join(WORKSPACE, config.get("agents_dir", ".claude/agents"))

    log_file = os.path.join(artifacts_dir, "switchboard.log")
    os.makedirs(artifacts_dir, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)

    active: dict[str, dict] = {}
    running = True

    def shutdown(signum, frame):
        nonlocal running
        log.info("Shutdown signal received, waiting for active workers...")
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log.info("Switchboard started (poll=%ds, max_workers=%d)", poll_interval, max_workers)

    while running:
        ready = get_ready_beads()

        for bead in ready:
            if len(active) >= max_workers:
                break

            bead_id = bead.get("id")
            if not bead_id or bead_id in active:
                continue

            agent = extract_agent(bead)
            if not agent:
                log.warning("Bead %s has no agent label, skipping", bead_id)
                continue

            repo = extract_repo(bead)
            if not repo:
                log.warning("Bead %s has no repo label, skipping", bead_id)
                continue

            if agent == "integrate":
                close_bead(bead_id)
                log.info("Auto-closed integrate bead %s (router handles merging)", bead_id)
                continue

            agent_file = Path(agents_dir) / f"{agent}.md"
            if not agent_file.exists():
                log.warning("No agent definition for '%s', skipping %s", agent, bead_id)
                continue

            if not claim_bead(bead_id):
                log.warning("Failed to claim %s", bead_id)
                continue

            log.info("Claimed %s (agent: %s, repo: %s)", bead_id, agent, repo)

            try:
                wt_path = worktree.create(bead_id, agent, repo, worktrees_dir)
            except RuntimeError as e:
                log.error("Worktree creation failed for %s: %s", bead_id, e)
                requeue_bead(bead_id, 0)
                continue

            bead_context = worker.fetch_bead_context(bead_id, WORKSPACE)
            tool_name = agent_tools.get(agent, default_tool_name)
            tool_cfg = tools.get(tool_name)
            proc = worker.launch(agent, bead_id, wt_path, agents_dir, artifacts_dir, bead_context, repo, tool_cfg)
            active[bead_id] = {
                "process": proc,
                "agent": agent,
                "repo": repo,
                "worktree": wt_path,
            }

        completed = []
        for bead_id, info in active.items():
            exit_code = worker.check(info["process"])
            if exit_code is None:
                continue

            completed.append(bead_id)

            if exit_code == 0:
                merged = worktree.merge_to_feature_branch(
                    bead_id, info["agent"], info["repo"],
                )
                if merged:
                    close_bead(bead_id)
                    log.info("Completed %s (agent: %s)", bead_id, info["agent"])
                else:
                    log.warning("Merge conflict for %s, creating integrate bead", bead_id)
                    _create_conflict_bead(bead_id, info["agent"], info["repo"])
                    close_bead(bead_id)
            else:
                detail = get_bead_metadata(bead_id)
                metadata = detail.get("metadata") or {}
                attempt = int(metadata.get("attempt", 0)) + 1
                max_attempts = int(metadata.get("max_attempts", 3))

                if attempt < max_attempts:
                    requeue_bead(bead_id, attempt)
                    log.warning("Failed %s attempt %d/%d, requeued", bead_id, attempt, max_attempts)
                else:
                    block_bead(bead_id)
                    log.error("Failed %s after %d attempts, blocked", bead_id, max_attempts)

            worktree.remove(bead_id, info["repo"], worktrees_dir)

        for bead_id in completed:
            del active[bead_id]

        time.sleep(poll_interval)

    for bead_id, info in active.items():
        log.info("Waiting for %s to finish...", bead_id)
        info["process"].wait()

    log.info("Switchboard stopped")


if __name__ == "__main__":
    main()
