"""Git worktree management."""

import logging
import os
import shutil
import subprocess

log = logging.getLogger("agent_router.worktree")


def _repo_abs(repo: str) -> str:
    """Resolve repo to an absolute path."""
    return os.path.abspath(repo)


def _is_worktree_active(repo_abs: str, path: str) -> bool:
    """Check if the path is a registered, active git worktree."""
    result = subprocess.run(
        ["git", "-C", repo_abs, "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if line.startswith("worktree ") and line.split(" ", 1)[1] == path:
            return True
    return False


def _cleanup_stale(repo_abs: str, path: str, branch: str) -> None:
    """Remove stale worktree and branch from a previous run.

    Only cleans up if the worktree is NOT registered as active in git.
    If it IS active, another agent may be using it — leave it alone.
    """
    if _is_worktree_active(repo_abs, path):
        log.warning("Worktree %s is registered and active, not cleaning up", path)
        return

    # Directory exists but not registered — orphaned, safe to remove
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
        log.info("Removed orphaned worktree directory %s", path)
    # Prune any dangling worktree refs
    subprocess.run(
        ["git", "-C", repo_abs, "worktree", "prune"],
        capture_output=True,
        text=True,
    )
    # Delete stale branch if it exists
    subprocess.run(
        ["git", "-C", repo_abs, "branch", "-D", branch],
        capture_output=True,
        text=True,
    )


def create(bead_id: str, agent: str, repo: str, worktrees_dir: str) -> str:
    repo_abs = _repo_abs(repo)
    path = os.path.join(repo_abs, worktrees_dir, bead_id)
    branch = f"agents/{bead_id}-{agent}"

    result = subprocess.run(
        ["git", "-C", repo_abs, "worktree", "add", "-b", branch, path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if _is_worktree_active(repo_abs, path):
            raise RuntimeError(
                f"Worktree {path} is already in use by another agent — skipping"
            )
        # Not active — clean up stale state and retry once
        log.info("Worktree create failed, cleaning stale state and retrying: %s", path)
        _cleanup_stale(repo_abs, path, branch)
        result = subprocess.run(
            ["git", "-C", repo_abs, "worktree", "add", "-b", branch, path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree {path}: {result.stderr.strip()}")

    log.info("Created worktree %s on branch %s (repo: %s)", path, branch, repo)
    return path


def merge_to_feature_branch(bead_id: str, agent: str, repo: str) -> bool:
    """Merge the agent's branch into the feature branch.

    Returns True on success or no-op, False on conflict (needs integrate agent).
    """
    repo_abs = _repo_abs(repo)
    branch = f"agents/{bead_id}-{agent}"

    result = subprocess.run(
        ["git", "-C", repo_abs, "log", "--oneline", f"HEAD..{branch}"],
        capture_output=True,
        text=True,
    )
    if not result.stdout.strip():
        log.info("No new commits on %s, skipping merge", branch)
        return True

    result = subprocess.run(
        ["git", "-C", repo_abs, "merge", branch, "--no-edit"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        log.info("Merged %s into feature branch (repo: %s)", branch, repo)
        return True

    # Conflict — abort and let the integrate agent handle it
    subprocess.run(
        ["git", "-C", repo_abs, "merge", "--abort"],
        capture_output=True,
        text=True,
    )
    log.warning("Merge conflict on %s, escalating to integrate agent", branch)
    return False


def remove(bead_id: str, repo: str, worktrees_dir: str) -> None:
    repo_abs = _repo_abs(repo)
    path = os.path.join(repo_abs, worktrees_dir, bead_id)
    subprocess.run(
        ["git", "-C", repo_abs, "worktree", "remove", path, "--force"],
        capture_output=True,
        text=True,
    )
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    subprocess.run(
        ["git", "-C", repo_abs, "worktree", "prune"],
        capture_output=True,
        text=True,
    )
    log.info("Removed worktree %s", path)
