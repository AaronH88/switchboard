"""Tests for multi-directory agent resolution feature.

Tests the agent resolution logic that allows projects to override built-in agents
by placing agent files in project-local directories.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

# Import the functions we need to test
# These imports will fail initially since the implementation doesn't exist yet
try:
    from agent_router.run import _resolve_agent_file, _build_project_registry
    from agent_router.helpers.worker import build_prompt
except ImportError:
    # Expected during red phase - functions don't exist yet
    _resolve_agent_file = None
    _build_project_registry = None
    build_prompt = None


class TestResolveAgentFile:
    """Test the _resolve_agent_file() function."""

    def test_agent_found_in_project_dir_returns_project_path(self, tmp_path):
        """Agent found in project dir returns project path."""
        # Setup
        project_agents_dir = tmp_path / "project_agents"
        builtin_agents_dir = tmp_path / "builtin_agents"
        project_agents_dir.mkdir()
        builtin_agents_dir.mkdir()

        # Create agent file in both directories
        (project_agents_dir / "development.md").write_text("Project agent definition")
        (builtin_agents_dir / "development.md").write_text("Built-in agent definition")

        # Test - should return project path
        if _resolve_agent_file:
            result = _resolve_agent_file("development", str(project_agents_dir), str(builtin_agents_dir))
            assert result == str(project_agents_dir / "development.md")
        else:
            pytest.skip("Function not implemented yet")

    def test_agent_found_only_in_builtin_dir_returns_builtin_path(self, tmp_path):
        """Agent found only in built-in dir returns built-in path."""
        # Setup
        project_agents_dir = tmp_path / "project_agents"
        builtin_agents_dir = tmp_path / "builtin_agents"
        project_agents_dir.mkdir()
        builtin_agents_dir.mkdir()

        # Create agent file only in built-in directory
        (builtin_agents_dir / "review.md").write_text("Built-in agent definition")

        # Test - should return built-in path
        if _resolve_agent_file:
            result = _resolve_agent_file("review", str(project_agents_dir), str(builtin_agents_dir))
            assert result == str(builtin_agents_dir / "review.md")
        else:
            pytest.skip("Function not implemented yet")

    def test_agent_in_both_dirs_returns_project_path(self, tmp_path):
        """Agent in both dirs returns project path (project wins)."""
        # Setup
        project_agents_dir = tmp_path / "project_agents"
        builtin_agents_dir = tmp_path / "builtin_agents"
        project_agents_dir.mkdir()
        builtin_agents_dir.mkdir()

        # Create agent file in both directories with different content
        (project_agents_dir / "tdd.md").write_text("Custom project TDD agent")
        (builtin_agents_dir / "tdd.md").write_text("Standard TDD agent")

        # Test - project should win over built-in
        if _resolve_agent_file:
            result = _resolve_agent_file("tdd", str(project_agents_dir), str(builtin_agents_dir))
            assert result == str(project_agents_dir / "tdd.md")
        else:
            pytest.skip("Function not implemented yet")

    def test_agent_in_neither_dir_returns_none(self, tmp_path):
        """Agent in neither dir returns None."""
        # Setup
        project_agents_dir = tmp_path / "project_agents"
        builtin_agents_dir = tmp_path / "builtin_agents"
        project_agents_dir.mkdir()
        builtin_agents_dir.mkdir()

        # Don't create any agent files

        # Test - should return None
        if _resolve_agent_file:
            result = _resolve_agent_file("nonexistent", str(project_agents_dir), str(builtin_agents_dir))
            assert result is None
        else:
            pytest.skip("Function not implemented yet")

    def test_no_project_agents_dir_configured_falls_back_to_builtin(self, tmp_path):
        """No project agents_dir configured falls back to built-in."""
        # Setup
        builtin_agents_dir = tmp_path / "builtin_agents"
        builtin_agents_dir.mkdir()

        # Create agent file only in built-in directory
        (builtin_agents_dir / "interface.md").write_text("Built-in interface agent")

        # Test - None/empty project dir should fall back to built-in
        if _resolve_agent_file:
            result = _resolve_agent_file("interface", None, str(builtin_agents_dir))
            assert result == str(builtin_agents_dir / "interface.md")

            result = _resolve_agent_file("interface", "", str(builtin_agents_dir))
            assert result == str(builtin_agents_dir / "interface.md")
        else:
            pytest.skip("Function not implemented yet")


class TestBuildProjectRegistry:
    """Test the updated _build_project_registry() function."""

    def test_project_with_agents_dir_in_config_gets_absolute_path(self, tmp_path):
        """Project with agents_dir in config gets absolute path in registry."""
        # Setup
        project_path = tmp_path / "my_project"
        project_path.mkdir()
        agents_dir = project_path / "custom_agents"
        agents_dir.mkdir()

        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        # Mock the load_project_config to return agents_dir
        mock_project_config = {
            "agents_dir": "custom_agents",
            "repos": [],
            "coding_tools": {},
            "default_tool": "claude",
            "agent_tools": {},
            "pipelines": {}
        }

        if _build_project_registry:
            with patch('agent_router.run.load_project_config', return_value=mock_project_config):
                registry = _build_project_registry(sb_config)

                assert "test_project" in registry
                assert "agents_dir" in registry["test_project"]
                # Should be absolute path
                expected_path = str(project_path / "custom_agents")
                assert registry["test_project"]["agents_dir"] == expected_path
        else:
            pytest.skip("Function not implemented yet")

    def test_project_without_agents_dir_gets_none_in_registry(self, tmp_path):
        """Project without agents_dir gets None in registry."""
        # Setup
        project_path = tmp_path / "my_project"
        project_path.mkdir()

        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        # Mock the load_project_config without agents_dir
        mock_project_config = {
            "repos": [],
            "coding_tools": {},
            "default_tool": "claude",
            "agent_tools": {},
            "pipelines": {}
        }

        if _build_project_registry:
            with patch('agent_router.run.load_project_config', return_value=mock_project_config):
                registry = _build_project_registry(sb_config)

                assert "test_project" in registry
                assert registry["test_project"]["agents_dir"] is None
        else:
            pytest.skip("Function not implemented yet")

    def test_relative_agents_dir_resolved_against_project_path(self, tmp_path):
        """Relative agents_dir resolved against project path."""
        # Setup
        project_path = tmp_path / "workspace" / "my_project"
        project_path.mkdir(parents=True)

        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        # Mock the load_project_config with relative path
        mock_project_config = {
            "agents_dir": "./agents",  # Relative path
            "repos": [],
            "coding_tools": {},
            "default_tool": "claude",
            "agent_tools": {},
            "pipelines": {}
        }

        if _build_project_registry:
            with patch('agent_router.run.load_project_config', return_value=mock_project_config):
                registry = _build_project_registry(sb_config)

                assert "test_project" in registry
                # Should resolve relative to project path
                expected_path = str(project_path / "agents")
                assert registry["test_project"]["agents_dir"] == expected_path
        else:
            pytest.skip("Function not implemented yet")

    def test_absolute_agents_dir_used_as_is(self, tmp_path):
        """Absolute agents_dir used as-is."""
        # Setup
        project_path = tmp_path / "my_project"
        project_path.mkdir()
        agents_path = tmp_path / "shared_agents"
        agents_path.mkdir()

        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        # Mock the load_project_config with absolute path
        mock_project_config = {
            "agents_dir": str(agents_path),  # Absolute path
            "repos": [],
            "coding_tools": {},
            "default_tool": "claude",
            "agent_tools": {},
            "pipelines": {}
        }

        if _build_project_registry:
            with patch('agent_router.run.load_project_config', return_value=mock_project_config):
                registry = _build_project_registry(sb_config)

                assert "test_project" in registry
                # Should use absolute path as-is
                assert registry["test_project"]["agents_dir"] == str(agents_path)
        else:
            pytest.skip("Function not implemented yet")


class TestBuildPromptUpdated:
    """Test the updated build_prompt() function with agent_file parameter."""

    def test_accepts_agent_file_path_and_reads_from_it(self, tmp_path):
        """Accepts agent_file Path and reads from it."""
        # Setup
        agent_file = tmp_path / "custom_development.md"
        agent_content = """---
name: Custom Development Agent
---

You are a custom development agent for this project.
Follow the project-specific coding standards.
"""
        agent_file.write_text(agent_content)

        if build_prompt:
            # Test with Path object
            result = build_prompt(
                agent_file=Path(agent_file),
                bead_id="test-bead-123",
                worktree_path="/tmp/worktree",
                bead_context="Test bead context"
            )

            # Should contain the agent definition without frontmatter
            assert "You are a custom development agent" in result
            assert "Follow the project-specific coding standards" in result
            assert "---" not in result  # Frontmatter should be stripped
            assert "test-bead-123" in result
            assert "/tmp/worktree" in result
        else:
            pytest.skip("Function not implemented yet")

    def test_nonexistent_agent_file_produces_prompt_without_agent_definition(self, tmp_path):
        """Non-existent agent_file produces prompt without agent definition."""
        # Setup
        nonexistent_file = tmp_path / "missing_agent.md"
        # Don't create the file

        if build_prompt:
            # Test with non-existent file
            result = build_prompt(
                agent_file=Path(nonexistent_file),
                bead_id="test-bead-456",
                worktree_path="/tmp/worktree2",
                bead_context="Test context"
            )

            # Should still have the prompt structure but no agent definition
            assert "test-bead-456" in result
            assert "/tmp/worktree2" in result
            assert "Test context" in result
            # Should not have much agent-specific content
            assert len(result.split('\n')[0]) < 50  # First line should be short/empty
        else:
            pytest.skip("Function not implemented yet")

    def test_old_signature_still_works_for_backward_compatibility(self, tmp_path):
        """Old signature (agent, agents_dir) still works for backward compatibility."""
        # Setup
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "development.md"
        agent_content = "Standard development agent definition"
        agent_file.write_text(agent_content)

        if build_prompt:
            # Test old signature - should still work
            result = build_prompt(
                agent="development",
                bead_id="test-bead-789",
                worktree_path="/tmp/worktree3",
                agents_dir=str(agents_dir),
                bead_context="Old style context"
            )

            assert "Standard development agent definition" in result
            assert "test-bead-789" in result
            assert "/tmp/worktree3" in result
        else:
            pytest.skip("Function not implemented yet")


class TestAgentResolutionIntegration:
    """Integration tests for the complete agent resolution workflow."""

    def test_end_to_end_agent_resolution_with_project_override(self, tmp_path):
        """End-to-end test: project agent overrides built-in agent."""
        # Setup directory structure
        project_path = tmp_path / "my_project"
        project_path.mkdir()
        project_agents = project_path / "agents"
        project_agents.mkdir()
        builtin_agents = tmp_path / "builtin_agents"
        builtin_agents.mkdir()

        # Create agents in both locations
        (project_agents / "development.md").write_text("""---
name: Custom Development
---

Custom project development agent with specific rules.""")

        (builtin_agents / "development.md").write_text("""---
name: Standard Development
---

Standard development agent definition.""")

        # Setup project config
        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        mock_project_config = {
            "agents_dir": "agents",
            "repos": [{"name": "main", "path": "./src"}],
            "coding_tools": {"claude": {"command": ["claude"]}},
            "default_tool": "claude",
            "agent_tools": {},
            "pipelines": {}
        }

        if _resolve_agent_file and _build_project_registry and build_prompt:
            with patch('agent_router.run.load_project_config', return_value=mock_project_config):
                # Build registry with project agents_dir
                registry = _build_project_registry(sb_config)

                # Resolve agent file (project should override built-in)
                project_agents_dir = registry["test_project"]["agents_dir"]
                agent_file_path = _resolve_agent_file("development", project_agents_dir, str(builtin_agents))

                # Build prompt using resolved agent file
                prompt = build_prompt(
                    agent_file=Path(agent_file_path),
                    bead_id="integration-test",
                    worktree_path="/tmp/test",
                    bead_context="Integration test"
                )

                # Should use custom project agent, not built-in
                assert "Custom project development agent" in prompt
                assert "Standard development agent" not in prompt
        else:
            pytest.skip("Functions not implemented yet")

    def test_fallback_to_builtin_when_project_agent_missing(self, tmp_path):
        """Fallback to built-in when project agent is missing."""
        # Setup - project has agents_dir but doesn't have this specific agent
        project_path = tmp_path / "my_project"
        project_path.mkdir()
        project_agents = project_path / "agents"
        project_agents.mkdir()
        builtin_agents = tmp_path / "builtin_agents"
        builtin_agents.mkdir()

        # Create agent only in built-in location
        (builtin_agents / "verify.md").write_text("Built-in verify agent")

        # Setup project config
        sb_config = {
            "projects": {
                "test_project": {
                    "path": str(project_path)
                }
            }
        }

        mock_project_config = {
            "agents_dir": "agents",
            "repos": [],
            "coding_tools": {},
            "default_tool": "claude",
            "agent_tools": {},
            "pipelines": {}
        }

        if _resolve_agent_file and _build_project_registry:
            with patch('agent_router.run.load_project_config', return_value=mock_project_config):
                registry = _build_project_registry(sb_config)
                project_agents_dir = registry["test_project"]["agents_dir"]

                # Should fall back to built-in
                agent_file_path = _resolve_agent_file("verify", project_agents_dir, str(builtin_agents))
                assert agent_file_path == str(builtin_agents / "verify.md")
        else:
            pytest.skip("Functions not implemented yet")

    def test_no_agents_dir_uses_builtin_only(self, tmp_path):
        """Project with no agents_dir uses built-in agents only."""
        # Setup
        project_path = tmp_path / "simple_project"
        project_path.mkdir()
        builtin_agents = tmp_path / "builtin_agents"
        builtin_agents.mkdir()

        (builtin_agents / "tests.md").write_text("Built-in tests agent")

        # Setup project config without agents_dir
        sb_config = {
            "projects": {
                "simple_project": {
                    "path": str(project_path)
                }
            }
        }

        mock_project_config = {
            "repos": [],
            "coding_tools": {},
            "default_tool": "claude",
            "agent_tools": {},
            "pipelines": {}
        }

        if _resolve_agent_file and _build_project_registry:
            with patch('agent_router.run.load_project_config', return_value=mock_project_config):
                registry = _build_project_registry(sb_config)
                project_agents_dir = registry["simple_project"]["agents_dir"]  # Should be None

                # Should use built-in agent
                agent_file_path = _resolve_agent_file("tests", project_agents_dir, str(builtin_agents))
                assert agent_file_path == str(builtin_agents / "tests.md")
        else:
            pytest.skip("Functions not implemented yet")


# Test fixtures and utilities

@pytest.fixture
def mock_temp_project(tmp_path):
    """Create a temporary project structure for testing."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    agents_dir = project_root / "agents"
    agents_dir.mkdir()

    return {
        "project_root": project_root,
        "agents_dir": agents_dir,
    }


@pytest.fixture
def sample_agent_configs():
    """Sample agent configuration files for testing."""
    return {
        "development.md": """---
name: Development Agent
model: claude-3-5-sonnet
---

You are the development agent. Write production code.""",

        "tests.md": """---
name: Tests Agent
model: claude-3-5-haiku
---

You write comprehensive test suites."""
    }


def test_imports():
    """Test that we can import the functions (will fail initially)."""
    # This test documents what functions should exist
    # It will fail until the implementation is added

    # Expected functions from agent_router.run
    try:
        from agent_router.run import _resolve_agent_file, _build_project_registry
        assert callable(_resolve_agent_file)
        assert callable(_build_project_registry)
    except ImportError:
        pytest.fail("Functions _resolve_agent_file and _build_project_registry not implemented yet")

    # Expected function from agent_router.helpers.worker
    try:
        from agent_router.helpers.worker import build_prompt
        assert callable(build_prompt)
    except ImportError:
        pytest.fail("Function build_prompt signature not updated yet")