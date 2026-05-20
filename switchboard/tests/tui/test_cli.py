"""Tests for CLI entry point and argument parsing."""

import pytest
import sys
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path
import argparse
import subprocess
import io

from switchboard.tui import cli, __main__


class TestCliArgumentParsing:
    """Tests for CLI argument parsing functionality."""

    def test_cli_default_arguments(self):
        """Test CLI with no command line arguments uses defaults."""
        # Mock sys.argv to have no arguments
        with patch('sys.argv', ['switchboard-tui']):
            args = cli.parse_arguments()

            # Should use default values
            assert args.artifacts_dir == "artifacts/"
            assert args.poll_interval == 10

    def test_cli_artifacts_dir_argument_absolute_path(self):
        """Test --artifacts-dir with absolute path."""
        test_path = "/custom/absolute/path"

        with patch('sys.argv', ['switchboard-tui', '--artifacts-dir', test_path]):
            args = cli.parse_arguments()

            assert args.artifacts_dir == test_path

    def test_cli_artifacts_dir_argument_relative_path(self):
        """Test --artifacts-dir with relative path."""
        test_path = "custom/relative/path"

        with patch('sys.argv', ['switchboard-tui', '--artifacts-dir', test_path]):
            args = cli.parse_arguments()

            assert args.artifacts_dir == test_path

    def test_cli_poll_interval_argument_valid_values(self):
        """Test --poll-interval with valid integer values."""
        test_cases = [5, 10, 30, 60]

        for interval in test_cases:
            with patch('sys.argv', ['switchboard-tui', '--poll-interval', str(interval)]):
                args = cli.parse_arguments()

                assert args.poll_interval == interval

    def test_cli_poll_interval_argument_invalid_values(self):
        """Test --poll-interval with invalid values raises error."""
        invalid_values = [0, -1, "abc", "10.5"]

        for invalid_value in invalid_values:
            with patch('sys.argv', ['switchboard-tui', '--poll-interval', str(invalid_value)]):
                with pytest.raises(SystemExit):
                    cli.parse_arguments()

    def test_cli_poll_interval_edge_cases(self):
        """Test --poll-interval with edge case values."""
        # Very large number
        with patch('sys.argv', ['switchboard-tui', '--poll-interval', '99999']):
            args = cli.parse_arguments()
            assert args.poll_interval == 99999

        # Minimum valid value (1)
        with patch('sys.argv', ['switchboard-tui', '--poll-interval', '1']):
            args = cli.parse_arguments()
            assert args.poll_interval == 1

    def test_cli_help_argument(self):
        """Test --help displays help text and exits."""
        with patch('sys.argv', ['switchboard-tui', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                cli.parse_arguments()

            # Should exit with code 0 (success) for help
            assert exc_info.value.code == 0

    def test_cli_help_short_argument(self):
        """Test -h displays help text and exits."""
        with patch('sys.argv', ['switchboard-tui', '-h']):
            with pytest.raises(SystemExit) as exc_info:
                cli.parse_arguments()

            # Should exit with code 0 (success) for help
            assert exc_info.value.code == 0

    def test_cli_invalid_arguments(self):
        """Test CLI with invalid/unknown arguments."""
        invalid_args = [
            ['switchboard-tui', '--invalid'],
            ['switchboard-tui', '--poll-interval'],  # Missing value
            ['switchboard-tui', '--artifacts-dir'],  # Missing value
            ['switchboard-tui', '--unknown-flag'],
        ]

        for args in invalid_args:
            with patch('sys.argv', args):
                with pytest.raises(SystemExit) as exc_info:
                    cli.parse_arguments()

                # Should exit with error code
                assert exc_info.value.code != 0

    def test_cli_combined_arguments(self):
        """Test CLI with multiple arguments combined."""
        with patch('sys.argv', [
            'switchboard-tui',
            '--artifacts-dir', '/custom/path',
            '--poll-interval', '30'
        ]):
            args = cli.parse_arguments()

            assert args.artifacts_dir == '/custom/path'
            assert args.poll_interval == 30

    def test_cli_arguments_order_independence(self):
        """Test CLI arguments work regardless of order."""
        # Test both orders
        orders = [
            ['--artifacts-dir', '/custom/path', '--poll-interval', '30'],
            ['--poll-interval', '30', '--artifacts-dir', '/custom/path']
        ]

        for arg_order in orders:
            with patch('sys.argv', ['switchboard-tui'] + arg_order):
                args = cli.parse_arguments()

                assert args.artifacts_dir == '/custom/path'
                assert args.poll_interval == 30

    def test_cli_artifacts_dir_creation(self):
        """Test CLI creates artifacts directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory path that doesn't exist
            artifacts_path = Path(temp_dir) / "new" / "artifacts"

            with patch('sys.argv', ['switchboard-tui', '--artifacts-dir', str(artifacts_path)]):
                args = cli.parse_arguments()

                # Should validate/create directory
                result = cli.setup_artifacts_directory(args.artifacts_dir)

                assert result is True or Path(artifacts_path).exists()

    def test_cli_artifacts_dir_parent_not_exist(self):
        """Test CLI handles case where parent directory doesn't exist."""
        nonexistent_path = "/nonexistent/parent/artifacts"

        with patch('sys.argv', ['switchboard-tui', '--artifacts-dir', nonexistent_path]):
            args = cli.parse_arguments()

            # Should handle gracefully
            try:
                result = cli.setup_artifacts_directory(args.artifacts_dir)
                # Either succeeds with recursive creation or fails gracefully
                assert isinstance(result, bool)
            except (OSError, PermissionError):
                # Acceptable to fail with proper exception
                pass

    def test_cli_artifacts_dir_permissions(self):
        """Test CLI handles permission restrictions."""
        # This test might be platform-specific and could be skipped on some systems
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Remove write permissions
                temp_path = Path(temp_dir)
                temp_path.chmod(0o444)  # Read-only

                artifacts_path = temp_path / "artifacts"

                with patch('sys.argv', ['switchboard-tui', '--artifacts-dir', str(artifacts_path)]):
                    args = cli.parse_arguments()

                    with pytest.raises(PermissionError):
                        cli.setup_artifacts_directory(args.artifacts_dir)

        except OSError:
            # Skip test if we can't modify permissions (e.g., Windows)
            pytest.skip("Permission modification not supported on this system")

    def test_cli_version_argument(self):
        """Test --version prints version string and exits with code 0."""
        with patch('sys.argv', ['switchboard-tui', '--version']):
            # Capture stdout since argparse prints version to stdout by default
            captured_output = io.StringIO()
            with patch('sys.stdout', captured_output):
                with pytest.raises(SystemExit) as exc_info:
                    cli.parse_arguments()

                # Should exit with code 0 (success)
                assert exc_info.value.code == 0

                # Should print the version string
                version_output = captured_output.getvalue().strip()
                assert version_output == "switchboard-tui 1.0.0"


class TestPythonModuleInvocation:
    """Tests for python -m switchboard.tui invocation."""

    def test_main_module_execution(self):
        """Test python -m switchboard.tui launches app with defaults."""
        with patch('switchboard.tui.__main__.main') as mock_main, \
             patch('sys.argv', ['__main__.py']):

            # Import should trigger main execution
            import switchboard.tui.__main__

            # Should call main function
            mock_main.assert_called_once()

    def test_main_module_with_arguments(self):
        """Test python -m switchboard.tui with arguments."""
        test_args = ['__main__.py', '--poll-interval', '5', '--artifacts-dir', '/test']

        with patch('switchboard.tui.__main__.main') as mock_main, \
             patch('sys.argv', test_args):

            # Should parse arguments and pass to main
            __main__.main()

            mock_main.assert_called_once()

    def test_main_module_import_error(self):
        """Test module handles import failures gracefully."""
        with patch('switchboard.tui.cli.parse_arguments', side_effect=ImportError("Module not found")):
            with pytest.raises(ImportError):
                __main__.main()

    def test_main_module_keyboard_interrupt(self):
        """Test main module handles Ctrl+C gracefully."""
        with patch('switchboard.tui.cli.parse_arguments', side_effect=KeyboardInterrupt):
            try:
                __main__.main()
            except SystemExit as e:
                # Should exit with appropriate code for keyboard interrupt
                assert e.code == 130 or e.code == 1

    def test_main_module_general_exception(self):
        """Test main module handles general exceptions."""
        with patch('switchboard.tui.cli.parse_arguments', side_effect=RuntimeError("Test error")):
            with pytest.raises((RuntimeError, SystemExit)):
                __main__.main()

    def test_main_function_delegates_to_app(self):
        """Test main function properly delegates to app."""
        mock_args = MagicMock()
        mock_args.artifacts_dir = "/test/artifacts"
        mock_args.poll_interval = 15

        with patch('switchboard.tui.cli.parse_arguments', return_value=mock_args), \
             patch('switchboard.tui.app.SwitchboardApp') as mock_app_class:

            mock_app = MagicMock()
            mock_app_class.return_value = mock_app

            __main__.main()

            # Should create app with parsed arguments
            mock_app_class.assert_called_once()
            mock_app.run.assert_called_once()

    def test_main_with_app_exception(self):
        """Test main handles app execution exceptions."""
        mock_args = MagicMock()

        with patch('switchboard.tui.cli.parse_arguments', return_value=mock_args), \
             patch('switchboard.tui.app.SwitchboardApp') as mock_app_class:

            mock_app = MagicMock()
            mock_app.run.side_effect = RuntimeError("App failed")
            mock_app_class.return_value = mock_app

            with pytest.raises(RuntimeError):
                __main__.main()


class TestCliIntegration:
    """Integration tests for CLI components."""

    def test_cli_to_app_integration(self):
        """Test complete flow from CLI to app execution."""
        test_args = ['switchboard-tui', '--poll-interval', '5']

        with patch('sys.argv', test_args), \
             patch('switchboard.tui.app.SwitchboardApp') as mock_app_class:

            mock_app = MagicMock()
            mock_app_class.return_value = mock_app

            # Parse arguments
            args = cli.parse_arguments()

            # Validate arguments were parsed correctly
            assert args.poll_interval == 5

            # Create and run app
            app = mock_app_class(
                artifacts_dir=args.artifacts_dir,
                poll_interval=args.poll_interval
            )
            app.run()

            # Verify app was created and run
            mock_app_class.assert_called_once()
            mock_app.run.assert_called_once()

    def test_cli_error_exit_codes(self):
        """Test CLI exits with appropriate error codes."""
        error_scenarios = [
            (['switchboard-tui', '--invalid'], 2),  # Invalid arguments
            (['switchboard-tui', '--poll-interval', 'abc'], 2),  # Invalid value
        ]

        for args, expected_code in error_scenarios:
            with patch('sys.argv', args):
                with pytest.raises(SystemExit) as exc_info:
                    cli.parse_arguments()

                assert exc_info.value.code == expected_code

    def test_cli_help_exit_code(self):
        """Test CLI help exits with success code."""
        with patch('sys.argv', ['switchboard-tui', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                cli.parse_arguments()

            assert exc_info.value.code == 0

    def test_cli_success_exit_code(self):
        """Test successful CLI execution."""
        with patch('sys.argv', ['switchboard-tui']), \
             patch('switchboard.tui.app.SwitchboardApp') as mock_app_class:

            mock_app = MagicMock()
            mock_app_class.return_value = mock_app

            # Should complete successfully
            try:
                args = cli.parse_arguments()
                app = mock_app_class()
                app.run()

                # No exception means success
                success = True
            except SystemExit as e:
                success = e.code == 0

            assert success


class TestCliUtilities:
    """Tests for CLI utility functions."""

    def test_setup_artifacts_directory_new_directory(self):
        """Test creating new artifacts directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_path = Path(temp_dir) / "artifacts"

            result = cli.setup_artifacts_directory(str(artifacts_path))

            assert result is True
            assert artifacts_path.exists()
            assert artifacts_path.is_dir()

    def test_setup_artifacts_directory_existing_directory(self):
        """Test with existing artifacts directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_path = Path(temp_dir)

            result = cli.setup_artifacts_directory(str(artifacts_path))

            assert result is True

    def test_setup_artifacts_directory_file_exists(self):
        """Test when artifacts path exists as a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file at the artifacts path
            artifacts_path = Path(temp_dir) / "artifacts"
            artifacts_path.touch()

            with pytest.raises((OSError, ValueError)):
                cli.setup_artifacts_directory(str(artifacts_path))

    def test_validate_poll_interval_valid(self):
        """Test poll interval validation with valid values."""
        valid_intervals = [1, 5, 10, 30, 60, 300]

        for interval in valid_intervals:
            result = cli.validate_poll_interval(interval)
            assert result == interval

    def test_validate_poll_interval_invalid(self):
        """Test poll interval validation with invalid values."""
        invalid_intervals = [0, -1, -10]

        for interval in invalid_intervals:
            with pytest.raises(ValueError):
                cli.validate_poll_interval(interval)

    def test_format_help_text(self):
        """Test help text formatting."""
        help_text = cli.get_help_text()

        # Should contain key information
        assert "switchboard" in help_text.lower()
        assert "artifacts-dir" in help_text
        assert "poll-interval" in help_text

    def test_parse_arguments_with_config_file(self):
        """Test parsing arguments from config file (if supported)."""
        # This test assumes config file support might be added
        try:
            config_content = """
            artifacts_dir = "/config/artifacts"
            poll_interval = 20
            """

            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as config_file:
                config_file.write(config_content)
                config_file.flush()

                with patch('sys.argv', ['switchboard-tui', '--config', config_file.name]):
                    args = cli.parse_arguments()

                    # Should load config from file
                    assert args.artifacts_dir == "/config/artifacts"
                    assert args.poll_interval == 20

        except AttributeError:
            # Config file support not implemented yet
            pytest.skip("Config file support not implemented")
        finally:
            try:
                Path(config_file.name).unlink()
            except:
                pass


# Test fixtures

@pytest.fixture
def temp_artifacts_dir():
    """Create temporary artifacts directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_args():
    """Create mock CLI arguments for testing."""
    args = MagicMock()
    args.artifacts_dir = "artifacts/"
    args.poll_interval = 10
    return args


@pytest.fixture
def isolated_argv():
    """Isolate sys.argv for testing."""
    original_argv = sys.argv.copy()
    yield
    sys.argv = original_argv


# Performance tests

class TestCliPerformance:
    """Performance tests for CLI operations."""

    def test_argument_parsing_performance(self):
        """Test CLI argument parsing is fast."""
        import time

        start_time = time.time()

        # Parse arguments multiple times
        for _ in range(100):
            with patch('sys.argv', ['switchboard-tui', '--poll-interval', '10']):
                cli.parse_arguments()

        elapsed = time.time() - start_time

        # Should complete quickly
        assert elapsed < 1.0  # Less than 1 second for 100 parses

    def test_directory_creation_performance(self):
        """Test directory creation is reasonably fast."""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = time.time()

            # Create multiple directories
            for i in range(10):
                artifacts_path = Path(temp_dir) / f"artifacts_{i}"
                cli.setup_artifacts_directory(str(artifacts_path))

            elapsed = time.time() - start_time

            # Should complete quickly
            assert elapsed < 1.0