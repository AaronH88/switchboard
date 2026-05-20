#!/usr/bin/env python3
"""Switchboard — single daemon that manages agent pipelines across multiple projects."""

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

SWITCHBOARD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


def load_switchboard_config() -> dict:
    """Load the central switchboard.yaml with project registry."""
    path = Path(SWITCHBOARD_DIR) / "switchboard.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_project_config(project_path: str) -> dict:
    """Load a project's local project.yaml."""
    path = Path(project_path) / "project.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _build_project_registry(sb_config: dict) -> dict:
    """Build a lookup of project name → {path, repos, pipelines, tools} from all configs."""
    registry = {}
    for name, project_entry in sb_config.get("projects", {}).items():
        project_path = project_entry.get("path", "")
        if not project_path:
            continue
        local_config = load_project_config(project_path)
        repos_by_name = {}
        for repo in local_config.get("repos", []):
            repo_path = repo.get("path", "")
            if not os.path.isabs(repo_path):
                repo_path = os.path.join(project_path, repo_path)
            repos_by_name[repo["name"]] = {
                "path": repo_path,
                "verify": repo.get("verify", ""),
            }
        agents_dir = local_config.get("agents_dir")
        if agents_dir and not os.path.isabs(agents_dir):
            agents_dir = os.path.join(project_path, agents_dir)
        registry[name] = {
            "path": project_path,
            "repos": repos_by_name,
            "coding_tools": local_config.get("coding_tools", {}),
            "default_tool": local_config.get("default_tool", "claude"),
            "agent_tools": local_config.get("agent_tools", {}),
            "pipelines": local_config.get("pipelines", {}),
            "agents_dir": agents_dir,
            "pipeline_tools": local_config.get("pipeline_tools", {}),
        }
    return registry


def _extract_label(bead: dict, prefix: str) -> str | None:
    """Extract a value from a bead's labels by prefix (e.g., 'agent:', 'repo:', 'project:')."""
    for label in bead.get("labels") or []:
        if label.startswith(prefix):
            return label.split(":", 1)[1]
    return None


def _resolve_repo_path(project_name: str, repo_name: str, registry: dict) -> str | None:
    """Resolve a repo name to an absolute path using the project registry."""
    project = registry.get(project_name)
    if not project:
        return None
    repo = project["repos"].get(repo_name)
    if not repo:
        return None
    return repo["path"]


def _resolve_agent_file(agent: str, project_name: str, registry: dict, default_agents_dir: str) -> Path | None:
    """Resolve agent name to definition file. Project agents take priority."""
    project = registry.get(project_name)
    if project:
        project_agents = project.get("agents_dir")
        if project_agents:
            candidate = Path(project_agents) / f"{agent}.md"
            if candidate.exists():
                return candidate
    candidate = Path(default_agents_dir) / f"{agent}.md"
    if candidate.exists():
        return candidate
    return None


def _check_epic_completion(bead_id: str) -> bool:
    """Check if all children of an epic are closed."""
    result = subprocess.run(
        ["bd", "show", bead_id, "--json"],
        capture_output=True,
        text=True,
        cwd=SWITCHBOARD_DIR,
    )
    if result.returncode != 0:
        return False
    try:
        data = json.loads(result.stdout)
        bead = data[0] if isinstance(data, list) else data
        dependents = bead.get("dependents") or []
        if not dependents:
            return False
        return all(d.get("status") == "closed" for d in dependents)
    except (json.JSONDecodeError, IndexError):
        return False


def _has_open_dependencies(bead_id: str) -> bool:
    """Check if a bead has any depends_on dependencies that aren't closed."""
    result = subprocess.run(
        ["bd", "show", bead_id, "--json"],
        capture_output=True,
        text=True,
        cwd=SWITCHBOARD_DIR,
    )
    if result.returncode != 0:
        return True
    try:
        data = json.loads(result.stdout)
        bead = data[0] if isinstance(data, list) else data
        for dep in bead.get("dependencies") or []:
            if dep.get("dependency_type") == "depends_on" and dep.get("status") != "closed":
                return True
        return False
    except (json.JSONDecodeError, IndexError):
        return True


def _resolve_tool_config(agent: str, project_name: str, registry: dict) -> dict | None:
    """Resolve which coding tool config to use for an agent in a project."""
    project = registry.get(project_name)
    if not project:
        return None
    tool_name = project["agent_tools"].get(agent, project["default_tool"])
    return project["coding_tools"].get(tool_name)


def _get_branch_name(repo_path: str) -> str | None:
    """Get the current branch name of a repo."""
    result = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return None if branch == "HEAD" else branch


def _get_parent_epic_info(bead_id: str) -> tuple[str, str]:
    """Get the parent epic's id and title for a bead."""
    result = subprocess.run(
        ["bd", "show", bead_id, "--json"],
        capture_output=True, text=True, cwd=SWITCHBOARD_DIR,
    )
    if result.returncode != 0:
        return ("", "")
    try:
        data = json.loads(result.stdout)
        bead = data[0] if isinstance(data, list) else data
        for dep in bead.get("dependencies") or []:
            if dep.get("dependency_type") == "parent":
                return (dep.get("id", ""), dep.get("title", ""))
    except (json.JSONDecodeError, IndexError):
        pass
    return ("", "")


def _resolve_tool_cwd(cwd_setting: str, repo_path: str, project_path: str) -> str:
    """Resolve the working directory for a pipeline tool."""
    if cwd_setting == "project":
        return project_path
    if cwd_setting == "switchboard":
        return SWITCHBOARD_DIR
    return repo_path


def _run_pipeline_tool(
    tool_name: str, bead_id: str, project_name: str, repo_path: str,
    registry: dict, artifacts_dir: str,
) -> subprocess.Popen:
    """Launch a pipeline tool step (no worktree, runs directly)."""
    project = registry[project_name]
    tool_cfg = project["pipeline_tools"][tool_name]

    branch = _get_branch_name(repo_path)
    epic_id, epic_title = _get_parent_epic_info(bead_id)

    variables = {
        "{repo}": repo_path,
        "{branch}": branch or "",
        "{bead_id}": bead_id,
        "{epic_id}": epic_id,
        "{epic_title}": epic_title,
        "{project}": project_name,
    }

    cmd = []
    for part in tool_cfg["command"]:
        for var, val in variables.items():
            part = part.replace(var, val)
        cmd.append(part)

    cwd = _resolve_tool_cwd(tool_cfg.get("cwd", "repo"), repo_path, project["path"])

    log_dir = Path(artifacts_dir) / "logs" / bead_id
    log_dir.mkdir(parents=True, exist_ok=True)

    log.info("Running tool '%s' for %s: %s", tool_name, bead_id, " ".join(cmd))

    return subprocess.Popen(
        cmd, cwd=cwd,
        stdout=open(log_dir / "stdout.log", "w"),
        stderr=open(log_dir / "stderr.log", "w"),
    )


# --- Bead operations (all use SWITCHBOARD_DIR as cwd for the shared beads DB) ---

def get_ready_beads() -> list[dict]:
    result = subprocess.run(
        ["bd", "ready", "--json"],
        capture_output=True,
        text=True,
        cwd=SWITCHBOARD_DIR,
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
        cwd=SWITCHBOARD_DIR,
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


def claim_bead(bead_id: str) -> bool:
    result = subprocess.run(
        ["bd", "update", bead_id, "--claim"],
        capture_output=True,
        text=True,
        cwd=SWITCHBOARD_DIR,
    )
    return result.returncode == 0


def close_bead(bead_id: str) -> None:
    subprocess.run(
        ["bd", "close", bead_id],
        capture_output=True,
        text=True,
        cwd=SWITCHBOARD_DIR,
    )


def requeue_bead(bead_id: str, attempt: int) -> None:
    subprocess.run(
        ["bd", "update", bead_id, "--set-metadata", f"attempt={attempt}"],
        capture_output=True,
        text=True,
        cwd=SWITCHBOARD_DIR,
    )
    subprocess.run(
        ["bd", "update", bead_id, "--status", "open"],
        capture_output=True,
        text=True,
        cwd=SWITCHBOARD_DIR,
    )


def block_bead(bead_id: str) -> None:
    subprocess.run(
        ["bd", "update", bead_id, "--status", "blocked"],
        capture_output=True,
        text=True,
        cwd=SWITCHBOARD_DIR,
    )


def _create_conflict_bead(bead_id: str, agent: str, repo_path: str, project_name: str) -> None:
    """Create an integrate bead to resolve merge conflicts."""
    branch = f"agents/{bead_id}-{agent}"
    title = f"Resolve merge conflict: {branch}"
    desc = (
        f"The {agent} agent completed work on branch `{branch}` in `{repo_path}`, "
        f"but merging into the feature branch failed due to conflicts.\n\n"
        f"## Steps\n"
        f"1. `cd {repo_path}`\n"
        f"2. `git merge {branch}` and resolve conflicts\n"
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
        "--add-label", f"project:{project_name}",
    ]
    if parent:
        cmd.extend(["--parent", parent])
    subprocess.run(cmd, capture_output=True, text=True, cwd=SWITCHBOARD_DIR)
    log.info("Created conflict resolution bead for %s", branch)


def main():
    config = load_config()
    sb_config = load_switchboard_config()
    registry = _build_project_registry(sb_config)

    poll_interval = config.get("poll_interval", 10)
    max_workers = config.get("max_workers", 3)
    artifacts_dir = os.path.join(SWITCHBOARD_DIR, config.get("artifacts_dir", "artifacts"))
    worktrees_dir = config.get("worktrees_dir", "worktrees")
    agents_dir = os.path.join(SWITCHBOARD_DIR, config.get("agents_dir", "agents"))

    log_file = os.path.join(artifacts_dir, "switchboard.log")
    os.makedirs(artifacts_dir, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)

    if not registry:
        log.error("No projects configured in switchboard.yaml")
        sys.exit(1)

    log.info("Switchboard started (poll=%ds, max_workers=%d, projects=%s)",
             poll_interval, max_workers, list(registry.keys()))

    active: dict[str, dict] = {}
    running = True

    def shutdown(signum, frame):
        nonlocal running
        log.info("Shutdown signal received, waiting for active workers...")
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while running:
        ready = get_ready_beads()

        for bead in ready:
            if len(active) >= max_workers:
                break

            bead_id = bead.get("id")
            if not bead_id or bead_id in active:
                continue

            if bead.get("issue_type") == "epic":
                if _check_epic_completion(bead_id):
                    close_bead(bead_id)
                    log.info("Epic completed: %s (%s)", bead_id, bead.get("title", ""))
                continue

            agent = _extract_label(bead, "agent:")
            tool = _extract_label(bead, "tool:")
            if not agent and not tool:
                log.warning("Bead %s has no agent: or tool: label, skipping", bead_id)
                continue

            project_name = _extract_label(bead, "project:")
            repo_name = _extract_label(bead, "repo:")
            if not project_name or not repo_name:
                log.warning("Bead %s missing project: or repo: label, skipping", bead_id)
                continue

            repo_path = _resolve_repo_path(project_name, repo_name, registry)
            if not repo_path:
                log.warning("Bead %s: repo '%s' not found in project '%s', skipping",
                            bead_id, repo_name, project_name)
                continue

            if agent == "integrate":
                close_bead(bead_id)
                log.info("Auto-closed integrate bead %s (router handles merging)", bead_id)
                continue

            if _has_open_dependencies(bead_id):
                continue

            if tool:
                # Tool step — validate config exists before claiming
                project_entry = registry.get(project_name, {})
                tool_cfg = project_entry.get("pipeline_tools", {}).get(tool)
                if not tool_cfg:
                    log.warning("No pipeline_tools config for '%s', skipping %s", tool, bead_id)
                    continue

                if not claim_bead(bead_id):
                    log.warning("Failed to claim %s", bead_id)
                    continue

                log.info("Claimed %s (project: %s, tool: %s, repo: %s)",
                         bead_id, project_name, tool, repo_name)

                proc = _run_pipeline_tool(tool, bead_id, project_name, repo_path,
                                          registry, artifacts_dir)
                active[bead_id] = {
                    "process": proc,
                    "agent": f"tool:{tool}",
                    "repo": repo_path,
                    "project": project_name,
                    "worktree": None,
                }
            else:
                # Agent step — existing behavior (worktree + coding tool)
                agent_file = _resolve_agent_file(agent, project_name, registry, agents_dir)
                if not agent_file:
                    log.warning("No agent definition for '%s', skipping %s", agent, bead_id)
                    continue

                if not claim_bead(bead_id):
                    log.warning("Failed to claim %s", bead_id)
                    continue

                log.info("Claimed %s (project: %s, agent: %s, repo: %s)",
                         bead_id, project_name, agent, repo_name)

                try:
                    wt_path = worktree.create(bead_id, agent, repo_path, worktrees_dir)
                except RuntimeError as e:
                    log.error("Worktree creation failed for %s: %s", bead_id, e)
                    requeue_bead(bead_id, 0)
                    continue

                bead_context = worker.fetch_bead_context(bead_id, SWITCHBOARD_DIR)
                coding_tool_cfg = _resolve_tool_config(agent, project_name, registry)
                proc = worker.launch(agent, bead_id, wt_path, agent_file, artifacts_dir,
                                     bead_context, repo_path, coding_tool_cfg)
                active[bead_id] = {
                    "process": proc,
                    "agent": agent,
                    "repo": repo_path,
                    "project": project_name,
                    "worktree": wt_path,
                }

        completed = []
        for bead_id, info in active.items():
            exit_code = worker.check(info["process"])
            if exit_code is None:
                continue

            completed.append(bead_id)

            if exit_code == 0:
                if info["worktree"]:
                    merged = worktree.merge_to_feature_branch(
                        bead_id, info["agent"], info["repo"],
                    )
                    if merged:
                        close_bead(bead_id)
                        log.info("Completed %s (agent: %s)", bead_id, info["agent"])
                    else:
                        log.warning("Merge conflict for %s, creating integrate bead", bead_id)
                        _create_conflict_bead(bead_id, info["agent"], info["repo"], info["project"])
                        close_bead(bead_id)
                else:
                    close_bead(bead_id)
                    log.info("Completed %s (%s)", bead_id, info["agent"])
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

            if info["worktree"]:
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
