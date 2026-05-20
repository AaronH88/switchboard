"""Tests for worker module agent file handling."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directory to path to import agent_router modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent_router', 'helpers'))

from worker import build_prompt, launch


def test_build_prompt_with_agent_file():
    """Test that build_prompt reads agent definition from provided file path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        agent_file = Path(temp_dir) / "development.md"
        agent_content = """---
name: development
description: Development agent
---

# Development Agent

You write implementation code."""
        agent_file.write_text(agent_content)

        prompt = build_prompt(
            agent="development",
            bead_id="test-bead",
            worktree_path="/test/worktree",
            agent_file=agent_file
        )

        # Should contain the stripped agent definition (without frontmatter)
        assert "# Development Agent" in prompt
        assert "You write implementation code." in prompt
        assert "name: development" not in prompt  # Frontmatter should be stripped


def test_build_prompt_with_nonexistent_agent_file():
    """Test that build_prompt handles nonexistent agent file gracefully."""
    nonexistent_file = Path("/nonexistent/path/agent.md")

    prompt = build_prompt(
        agent="development",
        bead_id="test-bead",
        worktree_path="/test/worktree",
        agent_file=nonexistent_file
    )

    # Should still generate a prompt without agent definition
    assert "Bead: test-bead" in prompt
    assert "Worktree: /test/worktree" in prompt


def test_build_prompt_with_none_agent_file():
    """Test that build_prompt handles None agent file."""
    prompt = build_prompt(
        agent="development",
        bead_id="test-bead",
        worktree_path="/test/worktree",
        agent_file=None
    )

    # Should still generate a prompt without agent definition
    assert "Bead: test-bead" in prompt
    assert "Worktree: /test/worktree" in prompt


def test_build_prompt_preserves_other_functionality():
    """Test that other build_prompt functionality is preserved."""
    with tempfile.TemporaryDirectory() as temp_dir:
        agent_file = Path(temp_dir) / "test.md"
        agent_file.write_text("# Test Agent")

        prompt = build_prompt(
            agent="test",
            bead_id="test-bead",
            worktree_path="/test/worktree",
            agent_file=agent_file,
            bead_context="Test bead context",
            repo_abs="/test/repo"
        )

        # Should contain all the expected sections
        assert "# Test Agent" in prompt
        assert "Bead: test-bead" in prompt
        assert "Worktree: /test/worktree" in prompt
        assert "# Assignment Context" in prompt
        assert "Test bead context" in prompt
        assert "# Important" in prompt
        assert "Do NOT use `bd` commands" in prompt


@patch('worker.subprocess.Popen')
def test_launch_signature_change(mock_popen):
    """Test that launch function works with new agent_file parameter."""
    mock_process = MagicMock()
    mock_popen.return_value = mock_process

    with tempfile.TemporaryDirectory() as temp_dir:
        agent_file = Path(temp_dir) / "test.md"
        agent_file.write_text("# Test Agent")

        log_dir = Path(temp_dir) / "logs"
        log_dir.mkdir()

        result = launch(
            agent="test",
            bead_id="test-bead",
            worktree_path="/test/worktree",
            agent_file=agent_file,
            artifacts_dir=temp_dir,
            bead_context="Test context"
        )

        assert result == mock_process
        mock_popen.assert_called_once()


@patch('worker.subprocess.Popen')
def test_launch_with_none_agent_file(mock_popen):
    """Test that launch handles None agent_file gracefully."""
    mock_process = MagicMock()
    mock_popen.return_value = mock_process

    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        log_dir.mkdir()

        result = launch(
            agent="test",
            bead_id="test-bead",
            worktree_path="/test/worktree",
            agent_file=None,
            artifacts_dir=temp_dir
        )

        assert result == mock_process
        mock_popen.assert_called_once()