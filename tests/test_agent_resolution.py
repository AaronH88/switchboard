"""Tests for project-local agent resolution functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# Add parent directory to path to import agent_router modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent_router'))

from run import _build_project_registry, _resolve_agent_file


def test_build_project_registry_with_agents_dir():
    """Test that _build_project_registry reads agents_dir from project config."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a project directory
        project_path = Path(temp_dir) / "test_project"
        project_path.mkdir()

        # Create project.yaml with agents_dir config
        project_config = {
            "repos": [{"name": "test_repo", "path": "./repo"}],
            "agents_dir": ".claude/agents"
        }
        (project_path / "project.yaml").write_text(yaml.safe_dump(project_config))

        # Mock switchboard config
        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        registry = _build_project_registry(sb_config)

        assert "test_project" in registry
        expected_agents_dir = str(project_path / ".claude" / "agents")
        assert registry["test_project"]["agents_dir"] == expected_agents_dir


def test_build_project_registry_absolute_agents_dir():
    """Test that absolute agents_dir paths are preserved."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test_project"
        project_path.mkdir()

        absolute_agents_dir = "/absolute/path/to/agents"
        project_config = {
            "repos": [{"name": "test_repo", "path": "./repo"}],
            "agents_dir": absolute_agents_dir
        }
        (project_path / "project.yaml").write_text(yaml.safe_dump(project_config))

        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        registry = _build_project_registry(sb_config)

        assert registry["test_project"]["agents_dir"] == absolute_agents_dir


def test_build_project_registry_no_agents_dir():
    """Test that agents_dir is None when not configured."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test_project"
        project_path.mkdir()

        # No agents_dir in config
        project_config = {
            "repos": [{"name": "test_repo", "path": "./repo"}]
        }
        (project_path / "project.yaml").write_text(yaml.safe_dump(project_config))

        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        registry = _build_project_registry(sb_config)

        assert registry["test_project"]["agents_dir"] is None


def test_resolve_agent_file_project_priority():
    """Test that project agents take priority over default agents."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create project agents directory with custom agent
        project_agents_dir = Path(temp_dir) / "project_agents"
        project_agents_dir.mkdir()
        (project_agents_dir / "development.md").write_text("# Project Development Agent")

        # Create default agents directory with same agent
        default_agents_dir = Path(temp_dir) / "default_agents"
        default_agents_dir.mkdir()
        (default_agents_dir / "development.md").write_text("# Default Development Agent")

        registry = {
            "test_project": {
                "agents_dir": str(project_agents_dir)
            }
        }

        agent_file = _resolve_agent_file("development", "test_project", registry, str(default_agents_dir))

        assert agent_file == project_agents_dir / "development.md"


def test_resolve_agent_file_fallback_to_default():
    """Test fallback to default agents when project agent doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create project agents directory without the requested agent
        project_agents_dir = Path(temp_dir) / "project_agents"
        project_agents_dir.mkdir()

        # Create default agents directory with the agent
        default_agents_dir = Path(temp_dir) / "default_agents"
        default_agents_dir.mkdir()
        (default_agents_dir / "development.md").write_text("# Default Development Agent")

        registry = {
            "test_project": {
                "agents_dir": str(project_agents_dir)
            }
        }

        agent_file = _resolve_agent_file("development", "test_project", registry, str(default_agents_dir))

        assert agent_file == default_agents_dir / "development.md"


def test_resolve_agent_file_no_project_agents_dir():
    """Test behavior when project has no agents_dir configured."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create default agents directory
        default_agents_dir = Path(temp_dir) / "default_agents"
        default_agents_dir.mkdir()
        (default_agents_dir / "development.md").write_text("# Default Development Agent")

        registry = {
            "test_project": {
                "agents_dir": None  # No project agents configured
            }
        }

        agent_file = _resolve_agent_file("development", "test_project", registry, str(default_agents_dir))

        assert agent_file == default_agents_dir / "development.md"


def test_resolve_agent_file_agent_not_found():
    """Test that None is returned when agent file doesn't exist anywhere."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create empty directories
        project_agents_dir = Path(temp_dir) / "project_agents"
        project_agents_dir.mkdir()
        default_agents_dir = Path(temp_dir) / "default_agents"
        default_agents_dir.mkdir()

        registry = {
            "test_project": {
                "agents_dir": str(project_agents_dir)
            }
        }

        agent_file = _resolve_agent_file("nonexistent", "test_project", registry, str(default_agents_dir))

        assert agent_file is None


def test_resolve_agent_file_project_not_found():
    """Test that None is returned when project doesn't exist in registry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        default_agents_dir = Path(temp_dir) / "default_agents"
        default_agents_dir.mkdir()
        (default_agents_dir / "development.md").write_text("# Default Development Agent")

        registry = {}  # Empty registry

        agent_file = _resolve_agent_file("development", "nonexistent_project", registry, str(default_agents_dir))

        assert agent_file == default_agents_dir / "development.md"


def test_full_flow_project_agent_to_prompt(tmp_path):
    """Integration test: project config → agent resolution → prompt generation."""
    # 1. Create project structure
    project_path = tmp_path / "my-project"
    project_path.mkdir()
    agents_dir = project_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)

    # 2. Create a custom agent
    custom_agent = agents_dir / "custom-lint.md"
    custom_agent.write_text("---\nname: custom-lint\ndescription: Custom linter\n---\n\nYou are a custom linting agent.\n")

    # 3. Create project.yaml
    import yaml
    config = {"repos": [{"name": "app", "path": "./app"}], "agents_dir": ".claude/agents"}
    (project_path / "project.yaml").write_text(yaml.safe_dump(config))

    # 4. Build registry
    sb_config = {"projects": {"my-project": {"path": str(project_path)}}}
    registry = _build_project_registry(sb_config)

    # 5. Resolve custom agent → should find project-local
    agent_file = _resolve_agent_file("custom-lint", "my-project", registry, "/nonexistent/builtin")
    assert agent_file is not None
    assert agent_file == custom_agent

    # 6. Resolve built-in agent → should fall back
    # Create a built-in agents dir
    builtin_dir = tmp_path / "builtin"
    builtin_dir.mkdir()
    (builtin_dir / "verify.md").write_text("---\nname: verify\n---\n\nBuilt-in verify agent.\n")
    builtin_file = _resolve_agent_file("verify", "my-project", registry, str(builtin_dir))
    assert builtin_file == builtin_dir / "verify.md"

    # 7. Build prompt with custom agent → should include its content
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent_router', 'helpers'))
    from worker import build_prompt
    prompt = build_prompt("custom-lint", "test-bead", "/tmp/wt", agent_file)
    assert "You are a custom linting agent." in prompt
    assert "name: custom-lint" not in prompt  # frontmatter stripped