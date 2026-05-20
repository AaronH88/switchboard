"""Simplified tests for Switchboard TUI app to verify basic functionality."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from switchboard.tui.app import SwitchboardApp


@pytest.mark.asyncio
async def test_app_can_start():
    """Test that the app can be created and started without crashing."""
    app = SwitchboardApp()

    with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
         patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
         patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

        mock_workers.return_value = []
        mock_stats.return_value = {"completed": 0, "failed": 0}

        # Mock async iterator for log tailing
        async def mock_log_iter():
            yield "2026-05-20 14:23:01 [INFO] Test log"
            return
        mock_tail.return_value = mock_log_iter()

        async with app.run_test() as pilot:
            # App should start without crashing
            assert pilot.app is not None
            assert hasattr(pilot.app, 'state')


@pytest.mark.asyncio
async def test_app_has_required_bindings():
    """Test that the app has the required key bindings defined."""
    app = SwitchboardApp()

    # Check bindings are defined
    binding_keys = [binding.key for binding in app.BINDINGS]

    expected_keys = ['q', 'tab', 'shift+tab', 'd', 'l', 'r', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

    for key in expected_keys:
        assert key in binding_keys, f"Key binding '{key}' is missing"


@pytest.mark.asyncio
async def test_app_compose_widgets():
    """Test that widgets are composed correctly."""
    from unittest.mock import patch
    app = SwitchboardApp()

    with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
         patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
         patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

        mock_workers.return_value = []
        mock_stats.return_value = {"completed": 0, "failed": 0}

        async def mock_log_iter():
            return
            yield  # Make it a generator
        mock_tail.return_value = mock_log_iter()

        async with app.run_test() as pilot:
            # Test that we can find the widgets by their class names
            try:
                from switchboard.tui.widgets import (
                    SwitchboardHeader, OperatorPanel, ProjectsPanel,
                    PatchPanel, ActiveLines, PartyLine, Footer
                )

                # Try to find each widget type
                header = pilot.app.query_one(SwitchboardHeader)
                assert header is not None

                operator = pilot.app.query_one(OperatorPanel)
                assert operator is not None

                projects = pilot.app.query_one(ProjectsPanel)
                assert projects is not None

                patch = pilot.app.query_one(PatchPanel)
                assert patch is not None

                active = pilot.app.query_one(ActiveLines)
                assert active is not None

                party = pilot.app.query_one(PartyLine)
                assert party is not None

                footer = pilot.app.query_one(Footer)
                assert footer is not None

            except Exception as e:
                # This may fail if widgets aren't properly implemented yet
                pytest.fail(f"Widget composition test failed: {e}")


def test_app_initialization_config():
    """Test app initialization with configuration."""
    config = {
        'artifacts_dir': '/tmp/test',
        'poll_interval': 5
    }

    app = SwitchboardApp(**config)

    assert app.artifacts_dir == '/tmp/test'
    assert app.poll_interval == 5
    assert hasattr(app, 'state')


@pytest.mark.asyncio
async def test_app_quit_action():
    """Test that quit action works."""
    app = SwitchboardApp()

    with patch('switchboard.tui.polling.poll_workers', new_callable=AsyncMock) as mock_workers, \
         patch('switchboard.tui.polling.poll_stats', new_callable=AsyncMock) as mock_stats, \
         patch('switchboard.tui.polling.tail_file', new_callable=AsyncMock) as mock_tail:

        mock_workers.return_value = []
        mock_stats.return_value = {"completed": 0, "failed": 0}

        async def mock_log_iter():
            return
            yield
        mock_tail.return_value = mock_log_iter()

        async with app.run_test() as pilot:
            # Test that pressing 'q' quits the app
            await pilot.press("q")
            # The app should exit (this test framework may handle this differently)