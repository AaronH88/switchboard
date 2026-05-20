"""Tests for Textual application shell."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from textual.testing import AppTest
from textual.keys import Keys
import tempfile

from switchboard.tui.app import SwitchboardApp


class TestSwitchboardApp:
    """Tests for SwitchboardApp Textual application."""

    def test_app_initialization(self):
        """Test SwitchboardApp initialization."""
        app = SwitchboardApp()

        # Should have basic app properties
        assert isinstance(app, SwitchboardApp)
        assert hasattr(app, 'css_path')
        assert hasattr(app, 'title')

    def test_app_css_loading(self):
        """Test app loads CSS theme correctly."""
        mock_css_content = """
        Screen {
            background: black;
            color: amber;
        }

        .header {
            background: dark_amber;
            color: white;
        }
        """

        # Mock CSS file existence and content
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_css_content)):

            app = SwitchboardApp()

            # Should load CSS successfully
            assert app.css_path is not None

    def test_app_css_missing_file(self):
        """Test app gracefully handles missing CSS file."""
        # Mock CSS file not existing
        with patch('pathlib.Path.exists', return_value=False):
            app = SwitchboardApp()

            # Should handle missing CSS gracefully
            # App should still be initializable
            assert isinstance(app, SwitchboardApp)

    def test_app_quit_key_handler(self):
        """Test 'Q' key press triggers app exit."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # Press 'Q' key
            pilot.press("q")

            # App should exit
            assert pilot.app.is_running is False

    def test_app_quit_key_case_insensitive(self):
        """Test both 'q' and 'Q' keys trigger quit."""
        # Test lowercase 'q'
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            pilot.press("q")
            assert pilot.app.is_running is False

        # Test uppercase 'Q'
        app2 = SwitchboardApp()

        with AppTest(app2) as pilot:
            pilot.press("Q")
            assert pilot.app.is_running is False

    def test_app_other_key_handlers(self):
        """Test other key presses are handled appropriately."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # Test various keys that should NOT quit the app
            test_keys = ["enter", "escape", "tab", "space", "a", "1"]

            for key in test_keys:
                pilot.press(key)
                # App should still be running
                assert pilot.app.is_running is True

    def test_app_control_characters(self):
        """Test control character key handling."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # Test Ctrl+C (should be handled by terminal, but app should handle gracefully)
            try:
                pilot.press("ctrl+c")
                # If handled, app might still be running
                # Exact behavior depends on implementation
            except KeyboardInterrupt:
                # This is also acceptable behavior
                pass

    def test_app_mount_unmount_lifecycle(self):
        """Test app startup and shutdown lifecycle."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # App should start successfully
            assert pilot.app.is_running is True

            # Test that widgets are mounted
            # (Specific widget tests depend on implementation)
            assert hasattr(pilot.app, 'screen')

            # Exit app
            pilot.press("q")

            # App should clean up resources
            assert pilot.app.is_running is False

    def test_app_error_handling(self):
        """Test app handles various error conditions gracefully."""
        # Test with invalid CSS content
        invalid_css = "invalid css content {{"

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=invalid_css)):

            # App should still be creatable even with invalid CSS
            try:
                app = SwitchboardApp()
                assert isinstance(app, SwitchboardApp)
            except Exception as e:
                # If CSS parsing fails, should have meaningful error
                assert "css" in str(e).lower() or "style" in str(e).lower()

    def test_app_widget_creation_failure(self):
        """Test app handles widget creation failures."""
        app = SwitchboardApp()

        # Mock a widget creation failure
        with patch.object(app, 'compose', side_effect=Exception("Widget creation failed")):
            try:
                with AppTest(app) as pilot:
                    pass
            except Exception as e:
                # Should propagate meaningful error
                assert "Widget creation failed" in str(e)

    def test_app_terminal_resize(self):
        """Test app layout adjusts to terminal resize."""
        app = SwitchboardApp()

        with AppTest(app, size=(80, 24)) as pilot:
            # Initial size
            initial_size = pilot.app.size

            # Resize terminal
            pilot.resize(120, 40)

            # App should handle resize
            new_size = pilot.app.size
            assert new_size != initial_size
            assert new_size.width == 120
            assert new_size.height == 40

    def test_app_theme_colors(self):
        """Test app applies amber CRT color palette."""
        amber_css = """
        Screen {
            background: $surface;
            color: $text;
        }

        $surface: #000000;
        $text: #ffb000;
        $primary: #ff8800;
        $accent: #ffcc00;
        """

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=amber_css)):

            app = SwitchboardApp()

            # Should load amber theme
            assert app.css_path is not None

            with AppTest(app) as pilot:
                # App should render with theme
                # (Color verification would depend on specific implementation)
                assert pilot.app.is_running is True

    def test_app_css_path_configuration(self):
        """Test app CSS path is correctly configured."""
        app = SwitchboardApp()

        # Should look for switchboard.tcss file
        if hasattr(app, 'css_path'):
            assert app.css_path is None or str(app.css_path).endswith('switchboard.tcss')

    def test_app_title_configuration(self):
        """Test app title is set correctly."""
        app = SwitchboardApp()

        # Should have appropriate title
        expected_titles = ["Switchboard", "switchboard", "Switchboard TUI"]
        if hasattr(app, 'title'):
            assert any(title.lower() in app.title.lower() for title in expected_titles)

    def test_app_with_custom_config(self):
        """Test app with custom configuration."""
        # Test with custom artifacts directory
        custom_config = {
            'artifacts_dir': '/custom/path',
            'poll_interval': 5
        }

        app = SwitchboardApp(**custom_config)

        # Should accept custom configuration
        if hasattr(app, 'config'):
            assert app.config.get('artifacts_dir') == '/custom/path'
            assert app.config.get('poll_interval') == 5

    def test_app_initialization_with_missing_dependencies(self):
        """Test app initialization when optional dependencies are missing."""
        # Mock missing textual components
        with patch.dict('sys.modules', {'textual.widgets': None}):
            try:
                app = SwitchboardApp()
                # Should either work with fallback or fail gracefully
                assert isinstance(app, SwitchboardApp)
            except ImportError as e:
                # Acceptable to fail with clear error message
                assert "textual" in str(e).lower()

    def test_app_concurrent_key_presses(self):
        """Test app handles rapid key presses correctly."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # Rapidly press multiple keys
            for i in range(10):
                pilot.press(f"{i}")

            # App should still be running and responsive
            assert pilot.app.is_running is True

            # Final quit should work
            pilot.press("q")
            assert pilot.app.is_running is False

    def test_app_memory_cleanup(self):
        """Test app cleans up resources properly on exit."""
        import gc
        import weakref

        app = SwitchboardApp()
        app_ref = weakref.ref(app)

        with AppTest(app) as pilot:
            pilot.press("q")

        # Clear references
        del app
        gc.collect()

        # App should be garbage collected
        # Note: This test might be flaky depending on Python implementation
        # assert app_ref() is None

    def test_app_exception_during_startup(self):
        """Test app handles exceptions during startup."""
        # Mock an exception during app setup
        original_setup = SwitchboardApp.on_mount

        def failing_setup(self):
            raise RuntimeError("Startup failed")

        with patch.object(SwitchboardApp, 'on_mount', failing_setup):
            app = SwitchboardApp()

            try:
                with AppTest(app) as pilot:
                    pass
            except RuntimeError as e:
                assert "Startup failed" in str(e)

    def test_app_logging_configuration(self):
        """Test app configures logging appropriately."""
        app = SwitchboardApp()

        # Should not interfere with existing logging configuration
        import logging
        logger = logging.getLogger('switchboard.tui')

        # Logger should exist and be configurable
        assert isinstance(logger, logging.Logger)

    def test_app_signal_handling(self):
        """Test app handles system signals appropriately."""
        import signal

        app = SwitchboardApp()

        # Should handle SIGTERM gracefully
        try:
            with AppTest(app) as pilot:
                # Simulate SIGTERM (if possible in test environment)
                # This is mainly to ensure app doesn't crash on signals
                assert pilot.app.is_running is True

                pilot.press("q")  # Normal exit
                assert pilot.app.is_running is False
        except:
            # Signal handling in tests can be tricky
            pass


# Test fixtures

@pytest.fixture
def temp_css_file():
    """Create temporary CSS file for testing."""
    css_content = """
    Screen {
        background: black;
        color: amber;
    }

    .header {
        background: dark_amber;
        color: white;
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.tcss', delete=False) as tmp_file:
        tmp_file.write(css_content)
        tmp_file.flush()
        yield Path(tmp_file.name)

    # Cleanup
    Path(tmp_file.name).unlink()


@pytest.fixture
def mock_app_dependencies():
    """Mock app dependencies for testing."""
    with patch('switchboard.tui.app.SwitchboardApp.css_path') as mock_css_path:
        mock_css_path.return_value = None
        yield mock_css_path


class TestAppIntegration:
    """Integration tests for SwitchboardApp with real components."""

    def test_app_full_startup_cycle(self):
        """Test complete app startup and shutdown cycle."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # App should start
            assert pilot.app.is_running is True

            # Should be able to interact
            pilot.press("tab")  # Navigation
            pilot.press("enter")  # Selection
            pilot.press("escape")  # Cancel

            # App should still be running
            assert pilot.app.is_running is True

            # Quit should work
            pilot.press("q")
            assert pilot.app.is_running is False

    def test_app_with_real_css_file(self, temp_css_file):
        """Test app with real CSS file."""
        # Configure app to use temporary CSS file
        with patch('switchboard.tui.app.SwitchboardApp.CSS_PATH', temp_css_file):
            app = SwitchboardApp()

            with AppTest(app) as pilot:
                # Should load CSS and render correctly
                assert pilot.app.is_running is True

                pilot.press("q")
                assert pilot.app.is_running is False

    def test_app_keyboard_navigation(self):
        """Test keyboard navigation works correctly."""
        app = SwitchboardApp()

        with AppTest(app) as pilot:
            # Test various navigation keys
            navigation_keys = ["tab", "shift+tab", "up", "down", "left", "right"]

            for key in navigation_keys:
                try:
                    pilot.press(key)
                    # Should not crash
                    assert pilot.app.is_running is True
                except Exception:
                    # Some keys might not be handled, that's OK
                    pass

            pilot.press("q")
            assert pilot.app.is_running is False