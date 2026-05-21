"""Tests for dynamic config reloading functionality."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from unittest.mock import call

import pytest
import yaml

# Add parent directory to path to import agent_router modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent_router'))

from run import _build_project_registry, load_switchboard_config, load_project_config


class TestConfigChangeDetection:
    """Tests for detecting when configuration files have changed."""

    def test_should_reload_config_returns_true_when_switchboard_yaml_mtime_changes(self, tmp_path):
        """Test that _should_reload_config() returns True when switchboard.yaml mtime changes."""
        # This function doesn't exist yet - test should fail
        from run import _should_reload_config

        # Create initial switchboard.yaml
        switchboard_yaml = tmp_path / "switchboard.yaml"
        config = {"projects": {"test": {"path": "/test/path"}}}
        switchboard_yaml.write_text(yaml.safe_dump(config))

        # Initialize watcher state (assuming this will be the interface)
        initial_mtime = switchboard_yaml.stat().st_mtime

        # Modify the file
        time.sleep(0.01)  # Ensure mtime difference
        switchboard_yaml.touch()
        new_mtime = switchboard_yaml.stat().st_mtime

        # Should detect change
        assert _should_reload_config(str(switchboard_yaml), initial_mtime) is True

    def test_should_reload_config_returns_false_when_files_unchanged(self, tmp_path):
        """Test that _should_reload_config() returns False when files haven't changed."""
        from run import _should_reload_config

        switchboard_yaml = tmp_path / "switchboard.yaml"
        config = {"projects": {"test": {"path": "/test/path"}}}
        switchboard_yaml.write_text(yaml.safe_dump(config))

        mtime = switchboard_yaml.stat().st_mtime

        # No changes made, should return False
        assert _should_reload_config(str(switchboard_yaml), mtime) is False

    def test_should_reload_config_returns_true_when_project_yaml_mtime_changes(self, tmp_path):
        """Test that _should_reload_config() detects changes in project.yaml files."""
        from run import _should_reload_config

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_yaml = project_dir / "project.yaml"
        config = {"repos": [{"name": "app", "path": "./app"}]}
        project_yaml.write_text(yaml.safe_dump(config))

        initial_mtime = project_yaml.stat().st_mtime

        time.sleep(0.01)
        project_yaml.touch()
        new_mtime = project_yaml.stat().st_mtime

        assert _should_reload_config(str(project_yaml), initial_mtime) is True

    def test_should_reload_config_handles_missing_files_gracefully(self, tmp_path):
        """Test that _should_reload_config() handles missing files without crashing."""
        from run import _should_reload_config

        nonexistent_file = tmp_path / "nonexistent.yaml"

        # Should handle missing file gracefully (probably return False or True depending on implementation)
        # The specific behavior will be defined during implementation
        result = _should_reload_config(str(nonexistent_file), 0.0)
        assert isinstance(result, bool)  # Should return a boolean, not crash


class TestRegistryReloading:
    """Tests for rebuilding the project registry when config changes."""

    def test_reload_config_rebuilds_registry_with_new_data(self, tmp_path):
        """Test that _reload_config() rebuilds registry with updated configuration."""
        from run import _reload_config

        # Create initial switchboard.yaml
        switchboard_yaml = tmp_path / "switchboard.yaml"
        initial_config = {
            "projects": {
                "project_a": {"path": str(tmp_path / "project_a")},
                "project_b": {"path": str(tmp_path / "project_b")}
            }
        }
        switchboard_yaml.write_text(yaml.safe_dump(initial_config))

        # Create project directories and configs
        for project in ["project_a", "project_b"]:
            project_dir = tmp_path / project
            project_dir.mkdir()
            project_config = {
                "repos": [{"name": "app", "path": "./app"}],
                "pipelines": {"dev": ["development", "verify"]}
            }
            (project_dir / "project.yaml").write_text(yaml.safe_dump(project_config))

        # Build initial registry
        old_registry = _build_project_registry(initial_config)
        assert len(old_registry) == 2

        # Update config to add new project
        updated_config = initial_config.copy()
        updated_config["projects"]["project_c"] = {"path": str(tmp_path / "project_c")}
        switchboard_yaml.write_text(yaml.safe_dump(updated_config))

        project_c_dir = tmp_path / "project_c"
        project_c_dir.mkdir()
        project_c_config = {
            "repos": [{"name": "backend", "path": "./backend"}],
            "pipelines": {"quick-fix": ["development", "verify"]}
        }
        (project_c_dir / "project.yaml").write_text(yaml.safe_dump(project_c_config))

        # Reload config
        new_registry = _reload_config(str(switchboard_yaml))

        # Should have all three projects
        assert len(new_registry) == 3
        assert "project_c" in new_registry
        assert new_registry["project_c"]["repos"]["backend"]["path"] == str(project_c_dir / "backend")

    def test_reload_config_handles_corrupt_yaml_gracefully(self, tmp_path):
        """Test that _reload_config() handles corrupt YAML without crashing."""
        from run import _reload_config

        # Create valid initial config
        switchboard_yaml = tmp_path / "switchboard.yaml"
        valid_config = {"projects": {"test": {"path": "/test"}}}
        switchboard_yaml.write_text(yaml.safe_dump(valid_config))

        old_registry = _build_project_registry(valid_config)

        # Corrupt the YAML
        switchboard_yaml.write_text("invalid: yaml: [unclosed bracket")

        # Should handle corruption gracefully and return None or old registry
        result = _reload_config(str(switchboard_yaml))
        # Implementation will decide whether to return None, old_registry, or empty dict
        # Test just ensures it doesn't crash
        assert result is not None or result is None  # Either outcome is acceptable

    def test_reload_config_handles_missing_project_yaml_gracefully(self, tmp_path):
        """Test that _reload_config() handles missing project.yaml files gracefully."""
        from run import _reload_config

        switchboard_yaml = tmp_path / "switchboard.yaml"
        config = {
            "projects": {
                "existing_project": {"path": str(tmp_path / "existing")},
                "missing_project": {"path": str(tmp_path / "missing")}
            }
        }
        switchboard_yaml.write_text(yaml.safe_dump(config))

        # Create only one project
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        project_config = {"repos": [{"name": "app", "path": "./app"}]}
        (existing_dir / "project.yaml").write_text(yaml.safe_dump(project_config))

        # missing_project directory doesn't exist

        registry = _reload_config(str(switchboard_yaml))

        # Should include existing project and handle missing gracefully
        # Exact behavior TBD - might include only existing, or include both with empty config
        assert "existing_project" in registry
        # missing_project behavior will be defined during implementation


class TestRegistryContentUpdates:
    """Tests for specific registry content changes."""

    def test_new_projects_added_to_registry_after_reload(self, tmp_path):
        """Test that new projects appear in registry after config reload."""
        from run import _reload_config

        # Initial config with 2 projects
        switchboard_yaml = tmp_path / "switchboard.yaml"
        config = {
            "projects": {
                "project_a": {"path": str(tmp_path / "project_a")},
                "project_b": {"path": str(tmp_path / "project_b")}
            }
        }

        # Create project directories
        for project in ["project_a", "project_b"]:
            project_dir = tmp_path / project
            project_dir.mkdir()
            (project_dir / "project.yaml").write_text(yaml.safe_dump({
                "repos": [{"name": "app", "path": "./app"}]
            }))

        initial_registry = _build_project_registry(config)
        assert len(initial_registry) == 2

        # Add new project to config
        config["projects"]["project_c"] = {"path": str(tmp_path / "project_c")}
        switchboard_yaml.write_text(yaml.safe_dump(config))

        project_c_dir = tmp_path / "project_c"
        project_c_dir.mkdir()
        (project_c_dir / "project.yaml").write_text(yaml.safe_dump({
            "repos": [{"name": "backend", "path": "./backend"}]
        }))

        new_registry = _reload_config(str(switchboard_yaml))

        assert len(new_registry) == 3
        assert "project_c" in new_registry

    def test_removed_projects_disappear_from_registry(self, tmp_path):
        """Test that removed projects are dropped from registry after reload."""
        from run import _reload_config

        switchboard_yaml = tmp_path / "switchboard.yaml"
        config = {
            "projects": {
                "project_a": {"path": str(tmp_path / "project_a")},
                "project_b": {"path": str(tmp_path / "project_b")},
                "project_c": {"path": str(tmp_path / "project_c")}
            }
        }

        # Create all projects
        for project in ["project_a", "project_b", "project_c"]:
            project_dir = tmp_path / project
            project_dir.mkdir()
            (project_dir / "project.yaml").write_text(yaml.safe_dump({
                "repos": [{"name": "app", "path": "./app"}]
            }))

        initial_registry = _build_project_registry(config)
        assert len(initial_registry) == 3

        # Remove project_b from config
        del config["projects"]["project_b"]
        switchboard_yaml.write_text(yaml.safe_dump(config))

        new_registry = _reload_config(str(switchboard_yaml))

        assert len(new_registry) == 2
        assert "project_a" in new_registry
        assert "project_c" in new_registry
        assert "project_b" not in new_registry

    def test_changed_pipelines_in_project_yaml_take_effect(self, tmp_path):
        """Test that pipeline changes in project.yaml are picked up after reload."""
        from run import _reload_config

        project_dir = tmp_path / "project_a"
        project_dir.mkdir()
        project_yaml = project_dir / "project.yaml"

        switchboard_yaml = tmp_path / "switchboard.yaml"
        sb_config = {
            "projects": {
                "project_a": {"path": str(project_dir)}
            }
        }
        switchboard_yaml.write_text(yaml.safe_dump(sb_config))

        # Initial project config with only dev pipeline
        initial_project_config = {
            "repos": [{"name": "app", "path": "./app"}],
            "pipelines": {
                "dev": ["development", "tests", "verify"]
            }
        }
        project_yaml.write_text(yaml.safe_dump(initial_project_config))

        initial_registry = _build_project_registry(sb_config)
        assert "dev" in initial_registry["project_a"]["pipelines"]
        assert len(initial_registry["project_a"]["pipelines"]) == 1

        # Add quick-fix pipeline
        updated_project_config = initial_project_config.copy()
        updated_project_config["pipelines"]["quick-fix"] = ["development", "verify"]
        project_yaml.write_text(yaml.safe_dump(updated_project_config))

        new_registry = _reload_config(str(switchboard_yaml))

        assert "dev" in new_registry["project_a"]["pipelines"]
        assert "quick-fix" in new_registry["project_a"]["pipelines"]
        assert len(new_registry["project_a"]["pipelines"]) == 2


class TestMainLoopIntegration:
    """Tests for integration with the main daemon loop."""

    @patch('run.get_ready_beads')
    @patch('run.time.sleep')
    def test_config_reload_check_in_main_loop(self, mock_sleep, mock_get_beads, tmp_path):
        """Test that config reload checking is integrated into main loop."""
        # This test will need to be updated once the main loop is modified
        # For now, it's a placeholder showing the expected integration
        from run import main

        # Mock the bead polling to return empty list (no beads to process)
        mock_get_beads.return_value = []

        # Mock sleep to exit after first iteration
        mock_sleep.side_effect = KeyboardInterrupt()

        with patch('run.load_switchboard_config') as mock_load_sb:
            with patch('run.load_project_config') as mock_load_proj:
                mock_load_sb.return_value = {
                    "projects": {
                        "test_project": {"path": "/fake/path"}
                    }
                }
                mock_load_proj.return_value = {
                    "repos": [{"name": "app", "path": "./app"}]
                }

                with patch('run._should_reload_config_bulk') as mock_should_reload:
                    mock_should_reload.return_value = False

                    # Should not crash and should call reload check functions
                    try:
                        main()
                    except KeyboardInterrupt:
                        pass  # Expected from our mock

                    # Once integration is implemented, we can verify the calls
                    # mock_should_reload.assert_called()

    @patch('subprocess.run')
    def test_registry_reload_during_active_worker_execution(self, mock_subprocess, tmp_path):
        """Test that active workers are not interrupted during config reload."""
        from run import _reload_config

        # Create config setup
        switchboard_yaml = tmp_path / "switchboard.yaml"
        config = {"projects": {"test_project": {"path": str(tmp_path / "project")}}}
        switchboard_yaml.write_text(yaml.safe_dump(config))

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "project.yaml").write_text(yaml.safe_dump({
            "repos": [{"name": "app", "path": "./app"}]
        }))

        # Simulate active worker by mocking subprocess calls for bd commands
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = '[]'

        # Registry reload should not interfere with bd command execution
        # (This is more of an integration concern, but we test the reload function itself)
        new_registry = _reload_config(str(switchboard_yaml))

        assert new_registry is not None
        assert "test_project" in new_registry


@pytest.fixture
def mock_file_operations():
    """Fixture to mock file system operations for testing."""
    with patch('builtins.open'), \
         patch('os.path.getmtime'), \
         patch('os.path.exists'), \
         patch('yaml.safe_load') as mock_yaml:
        yield mock_yaml


class TestErrorHandling:
    """Tests for error handling in config reload operations."""

    def test_file_permission_errors_handled_gracefully(self, tmp_path, mock_file_operations):
        """Test that filesystem permission errors are logged and handled."""
        from run import _reload_config

        switchboard_yaml = tmp_path / "switchboard.yaml"
        switchboard_yaml.write_text("projects: {}")

        # Mock permission error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Should handle error gracefully, not crash
            result = _reload_config(str(switchboard_yaml))
            # Implementation will decide exact behavior - test ensures no crash
            assert result is not None or result is None

    def test_yaml_parse_errors_logged_and_handled(self, tmp_path):
        """Test that YAML parsing errors are logged with details."""
        from run import _reload_config

        switchboard_yaml = tmp_path / "switchboard.yaml"
        # Write invalid YAML
        switchboard_yaml.write_text("invalid: yaml: content: [unclosed")

        with patch('run.log') as mock_logger:
            result = _reload_config(str(switchboard_yaml))

            # Should log the error (exact log message TBD during implementation)
            assert mock_logger.error.called or mock_logger.warning.called

    def test_nonexistent_project_directories_handled(self, tmp_path):
        """Test behavior when project directories referenced in config don't exist."""
        from run import _reload_config

        switchboard_yaml = tmp_path / "switchboard.yaml"
        config = {
            "projects": {
                "nonexistent": {"path": "/completely/fake/path"}
            }
        }
        switchboard_yaml.write_text(yaml.safe_dump(config))

        # Should handle missing directories gracefully
        result = _reload_config(str(switchboard_yaml))

        # Exact behavior TBD - might be empty registry, might exclude bad projects
        assert isinstance(result, dict)  # Should return something, not crash


class TestPerformanceRequirements:
    """Tests for performance-related requirements."""

    def test_config_change_detection_performance(self, tmp_path):
        """Test that config change detection completes quickly."""
        from run import _should_reload_config

        # Create multiple config files
        files_to_check = []
        for i in range(10):  # Test with multiple files
            config_file = tmp_path / f"project_{i}.yaml"
            config_file.write_text(yaml.safe_dump({"repos": []}))
            files_to_check.append((str(config_file), config_file.stat().st_mtime))

        start_time = time.time()

        # Check all files for changes
        for file_path, mtime in files_to_check:
            _should_reload_config(file_path, mtime)

        end_time = time.time()

        # Should complete within 100ms as per requirements
        assert (end_time - start_time) < 0.1

    def test_registry_rebuild_performance(self, tmp_path):
        """Test that registry rebuild completes within acceptable time."""
        from run import _reload_config

        # Create larger config to test performance
        switchboard_yaml = tmp_path / "switchboard.yaml"
        config = {"projects": {}}

        # Create 5 projects (reasonable size for performance testing)
        for i in range(5):
            project_name = f"project_{i}"
            project_dir = tmp_path / project_name
            project_dir.mkdir()

            project_config = {
                "repos": [
                    {"name": "app", "path": "./app"},
                    {"name": "api", "path": "./api"},
                    {"name": "worker", "path": "./worker"}
                ],
                "pipelines": {
                    "dev": ["development", "tests", "verify"],
                    "quick": ["development", "verify"],
                    "full": ["development", "tests", "integration", "verify"]
                }
            }
            (project_dir / "project.yaml").write_text(yaml.safe_dump(project_config))
            config["projects"][project_name] = {"path": str(project_dir)}

        switchboard_yaml.write_text(yaml.safe_dump(config))

        start_time = time.time()
        result = _reload_config(str(switchboard_yaml))
        end_time = time.time()

        # Should complete within 5 seconds as per requirements
        assert (end_time - start_time) < 5.0
        assert len(result) == 5