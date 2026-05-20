"""Tests for Signature Widgets - PatchPanel and PartyLine TUI components."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import List, Dict, Any

# Import Textual testing utilities
try:
    from textual.app import App
    from textual.testing import AppPilot
    from textual.widgets import Widget
except ImportError:
    # Textual not available in test environment - mock it
    App = Mock
    AppPilot = Mock
    Widget = Mock

# Import the widgets we're testing (these don't exist yet - will cause ImportError)
try:
    from switchboard.tui.widgets import PatchPanel, PartyLine
    from switchboard.models import Pipeline, PipelineStep, LogEntry
except ImportError:
    # Components don't exist yet - create mock classes for testing structure
    PatchPanel = Mock
    PartyLine = Mock
    Pipeline = Mock
    PipelineStep = Mock
    LogEntry = Mock


# Mock data fixtures
@pytest.fixture
def empty_pipeline_state():
    """Empty state with no pipelines."""
    return {
        "pipelines": [],
        "active_pipeline": None
    }


@pytest.fixture
def single_pipeline_state():
    """State with a single pipeline having multiple steps."""
    return {
        "pipelines": [
            {
                "id": "pip-001",
                "name": "Deploy Frontend",
                "steps": [
                    {
                        "id": "step-001",
                        "name": "lint",
                        "status": "completed",
                        "tool": "eslint",
                        "elapsed_time": "2.3s"
                    },
                    {
                        "id": "step-002",
                        "name": "test",
                        "status": "running",
                        "tool": "jest",
                        "elapsed_time": "45.7s"
                    },
                    {
                        "id": "step-003",
                        "name": "build",
                        "status": "pending",
                        "tool": "vite",
                        "elapsed_time": None
                    }
                ]
            }
        ],
        "active_pipeline": "pip-001"
    }


@pytest.fixture
def multiple_pipelines_state():
    """State with multiple pipelines at different stages."""
    return {
        "pipelines": [
            {
                "id": "pip-001",
                "name": "Deploy Frontend",
                "steps": [
                    {"id": "step-001", "name": "lint", "status": "completed", "tool": "eslint"},
                    {"id": "step-002", "name": "test", "status": "completed", "tool": "jest"},
                    {"id": "step-003", "name": "build", "status": "running", "tool": "vite"}
                ]
            },
            {
                "id": "pip-002",
                "name": "Deploy Backend",
                "steps": [
                    {"id": "step-004", "name": "typecheck", "status": "failed", "tool": "mypy"},
                    {"id": "step-005", "name": "test", "status": "pending", "tool": "pytest"}
                ]
            },
            {
                "id": "pip-003",
                "name": "Infrastructure",
                "steps": [
                    {"id": "step-006", "name": "terraform", "status": "completed", "tool": "terraform"}
                ]
            }
        ]
    }


@pytest.fixture
def party_line_log_entries():
    """Mock log entries for PartyLine testing."""
    base_time = datetime.now()
    return [
        {
            "timestamp": base_time - timedelta(minutes=5),
            "event_type": "pipeline_start",
            "source": "pip-001",
            "message": "Deploy Frontend initiated",
            "data": {"pipeline_id": "pip-001", "user": "operator1"}
        },
        {
            "timestamp": base_time - timedelta(minutes=4),
            "event_type": "step_complete",
            "source": "pip-001",
            "message": "lint step green light",
            "data": {"step_id": "step-001", "duration": "2.3s"}
        },
        {
            "timestamp": base_time - timedelta(minutes=2),
            "event_type": "step_start",
            "source": "pip-001",
            "message": "test step hot",
            "data": {"step_id": "step-002", "tool": "jest"}
        },
        {
            "timestamp": base_time - timedelta(minutes=1),
            "event_type": "operator_switch",
            "source": "system",
            "message": "Source switched to pip-002",
            "data": {"from": "pip-001", "to": "pip-002"}
        }
    ]


class TestPatchPanel:
    """Tests for PatchPanel widget displaying pipeline status with signal lamps."""

    def test_empty_state_renders_placeholder(self, empty_pipeline_state):
        """Empty state should render a placeholder message."""
        patch_panel = PatchPanel()
        patch_panel.update_state(empty_pipeline_state)

        # Should render placeholder when no pipelines
        rendered = patch_panel.render()
        assert "No pipelines active" in rendered or "placeholder" in rendered.lower()

    def test_single_pipeline_renders_box_structure(self, single_pipeline_state):
        """Single pipeline should render with correct box structure."""
        patch_panel = PatchPanel()
        patch_panel.update_state(single_pipeline_state)

        rendered = patch_panel.render()

        # Should show pipeline name in a box
        assert "Deploy Frontend" in rendered

        # Should show all steps
        assert "lint" in rendered
        assert "test" in rendered
        assert "build" in rendered

        # Should have box drawing characters for structure
        assert any(char in rendered for char in ['│', '┌', '┐', '└', '┘', '├', '┤'])

    def test_multiple_pipelines_render_vertically(self, multiple_pipelines_state):
        """Multiple pipelines should stack vertically."""
        patch_panel = PatchPanel()
        patch_panel.update_state(multiple_pipelines_state)

        rendered = patch_panel.render()

        # All pipeline names should be present
        assert "Deploy Frontend" in rendered
        assert "Deploy Backend" in rendered
        assert "Infrastructure" in rendered

        # Should be arranged vertically (check for multiple box structures)
        lines = rendered.split('\n')
        pipeline_lines = [i for i, line in enumerate(lines) if "Deploy" in line or "Infrastructure" in line]

        # Pipeline names should appear on different lines
        assert len(pipeline_lines) >= 2

    def test_signal_lamps_match_step_statuses(self, single_pipeline_state):
        """Signal lamps should reflect step statuses with correct colors/symbols."""
        patch_panel = PatchPanel()
        patch_panel.update_state(single_pipeline_state)

        # Mock the signal lamp rendering
        lamps = patch_panel.get_signal_lamps()

        # Should have lamp for each step
        assert len(lamps) == 3

        # Completed step should have green/success indicator
        assert lamps[0]["status"] == "completed"
        assert lamps[0]["color"] == "green" or lamps[0]["symbol"] == "●"

        # Running step should have yellow/active indicator
        assert lamps[1]["status"] == "running"
        assert lamps[1]["color"] == "yellow" or lamps[1]["symbol"] == "◐"

        # Pending step should have gray/inactive indicator
        assert lamps[2]["status"] == "pending"
        assert lamps[2]["color"] == "gray" or lamps[2]["symbol"] == "○"

    def test_active_step_shows_connector_with_tool_and_time(self, single_pipeline_state):
        """Active step should display connector with tool name and elapsed time."""
        patch_panel = PatchPanel()
        patch_panel.update_state(single_pipeline_state)

        active_step = patch_panel.get_active_step()

        # Should identify the running step
        assert active_step["id"] == "step-002"
        assert active_step["status"] == "running"

        # Should show connector visual
        connector = patch_panel.get_step_connector("step-002")
        assert connector is not None

        # Should include tool name and elapsed time
        assert "jest" in str(connector)
        assert "45.7s" in str(connector)

        # Should have connector symbols
        assert any(symbol in str(connector) for symbol in ['→', '⟶', '>>'])

    def test_progress_counter_accuracy(self, single_pipeline_state):
        """Progress counter should accurately reflect completed vs total steps."""
        patch_panel = PatchPanel()
        patch_panel.update_state(single_pipeline_state)

        progress = patch_panel.get_progress_counter()

        # 1 completed out of 3 total steps
        assert progress["completed"] == 1
        assert progress["total"] == 3
        assert progress["percentage"] == 33  # 1/3 ≈ 33%

        # Progress display should show fraction
        progress_text = patch_panel.render_progress()
        assert "1/3" in progress_text or "33%" in progress_text

    def test_failed_step_shows_error_indicator(self, multiple_pipelines_state):
        """Failed steps should display error indicators."""
        patch_panel = PatchPanel()
        patch_panel.update_state(multiple_pipelines_state)

        lamps = patch_panel.get_signal_lamps()

        # Find the failed typecheck step
        failed_lamps = [lamp for lamp in lamps if lamp.get("status") == "failed"]
        assert len(failed_lamps) >= 1

        failed_lamp = failed_lamps[0]
        assert failed_lamp["color"] == "red" or failed_lamp["symbol"] == "✗"


class TestPartyLine:
    """Tests for PartyLine widget displaying log entries in operator jargon."""

    def test_log_entries_render_with_timestamps(self, party_line_log_entries):
        """Log entries should render with formatted timestamps."""
        party_line = PartyLine()
        party_line.update_entries(party_line_log_entries)

        rendered = party_line.render()

        # Should contain timestamp formatting
        for entry in party_line_log_entries:
            timestamp_str = entry["timestamp"].strftime("%H:%M")
            assert timestamp_str in rendered

    def test_operator_jargon_formatting_for_event_types(self, party_line_log_entries):
        """Different event types should use appropriate operator jargon."""
        party_line = PartyLine()
        party_line.update_entries(party_line_log_entries)

        jargon_map = party_line.get_jargon_formatting()

        # Pipeline events should use pipeline terminology
        assert "pipeline_start" in jargon_map
        assert any(term in jargon_map["pipeline_start"] for term in ["initiated", "go", "hot"])

        # Step events should use step terminology
        assert "step_complete" in jargon_map
        assert any(term in jargon_map["step_complete"] for term in ["green light", "complete", "done"])

        assert "step_start" in jargon_map
        assert any(term in jargon_map["step_start"] for term in ["hot", "running", "started"])

        # System events should use system terminology
        assert "operator_switch" in jargon_map
        assert any(term in jargon_map["operator_switch"] for term in ["switched", "transfer", "handoff"])

    def test_source_indicator_changes_when_switching_sources(self, party_line_log_entries):
        """Source indicator should update when log source changes."""
        party_line = PartyLine()
        party_line.update_entries(party_line_log_entries)

        # Initially showing pip-001 entries
        current_source = party_line.get_current_source()
        assert current_source in ["pip-001", "pip-002"]  # Could be either depending on latest

        # Switch source explicitly
        party_line.set_source_filter("pip-002")
        assert party_line.get_current_source() == "pip-002"

        # Indicator should update
        indicator = party_line.get_source_indicator()
        assert "pip-002" in indicator

        # Should show visual indicator of active source
        rendered = party_line.render()
        assert "►" in rendered or "●" in rendered  # Active source indicator

    def test_new_entries_append_correctly(self, party_line_log_entries):
        """New log entries should append to the bottom of the list."""
        party_line = PartyLine()
        party_line.update_entries(party_line_log_entries[:2])  # Start with 2 entries

        initial_count = party_line.get_entry_count()
        assert initial_count == 2

        # Add new entries
        new_entries = party_line_log_entries[2:]
        party_line.append_entries(new_entries)

        final_count = party_line.get_entry_count()
        assert final_count == len(party_line_log_entries)

        # Latest entry should be at the bottom
        latest_entry = party_line.get_latest_entry()
        assert latest_entry["event_type"] == "operator_switch"

    def test_log_entry_color_coding(self, party_line_log_entries):
        """Log entries should use color coding based on event type."""
        party_line = PartyLine()
        party_line.update_entries(party_line_log_entries)

        color_scheme = party_line.get_color_scheme()

        # Different event types should have different colors
        assert "pipeline_start" in color_scheme
        assert "step_complete" in color_scheme
        assert "step_start" in color_scheme
        assert "operator_switch" in color_scheme

        # Colors should be appropriate
        assert color_scheme["step_complete"] in ["green", "success"]
        assert color_scheme["pipeline_start"] in ["blue", "info"]
        assert color_scheme["operator_switch"] in ["yellow", "warning"]

    def test_message_truncation_for_long_entries(self):
        """Long log messages should be properly truncated with indicators."""
        party_line = PartyLine()

        long_message = "This is a very long log message that should be truncated because it exceeds the maximum display width for the party line widget and would cause layout issues"

        long_entry = {
            "timestamp": datetime.now(),
            "event_type": "pipeline_start",
            "source": "pip-001",
            "message": long_message,
            "data": {}
        }

        party_line.update_entries([long_entry])
        rendered = party_line.render()

        # Should truncate and add indicator
        assert "..." in rendered or "…" in rendered
        assert len(rendered.split('\n')[0]) <= party_line.max_line_width

    def test_empty_log_state(self):
        """Empty log state should show appropriate placeholder."""
        party_line = PartyLine()
        party_line.update_entries([])

        rendered = party_line.render()
        assert "No activity" in rendered or "quiet" in rendered.lower()


class TestSignatureWidgetIntegration:
    """Integration tests for PatchPanel and PartyLine working together."""

    def test_widgets_sync_on_pipeline_updates(self, single_pipeline_state, party_line_log_entries):
        """Both widgets should update consistently when pipeline state changes."""
        patch_panel = PatchPanel()
        party_line = PartyLine()

        # Initial state
        patch_panel.update_state(single_pipeline_state)
        party_line.update_entries(party_line_log_entries)

        # Both should show the same active pipeline
        assert patch_panel.get_active_pipeline_id() == "pip-001"
        latest_entry = party_line.get_latest_entry()
        assert latest_entry["source"] in ["pip-001", "pip-002", "system"]

    def test_cross_widget_navigation(self):
        """User should be able to navigate between widgets and maintain context."""
        # This would test keyboard navigation between patch panel and party line
        # but would require actual Textual app integration testing
        pass


# Mock implementation helpers for testing (these will fail until real implementation exists)
def test_imports_fail_gracefully():
    """Verify that import failures are handled gracefully in test environment."""
    try:
        from switchboard.tui.widgets import PatchPanel, PartyLine
        # If imports work, widgets should be classes
        assert callable(PatchPanel)
        assert callable(PartyLine)
    except ImportError:
        # Expected to fail until implementation exists
        pytest.skip("Widget implementations not yet available")


def test_textual_dependency():
    """Verify Textual testing framework is available or gracefully mocked."""
    try:
        from textual.testing import AppPilot
        assert AppPilot is not None
    except ImportError:
        # Expected in environments without Textual
        pytest.skip("Textual not available for testing")


if __name__ == "__main__":
    # Run tests in development
    pytest.main([__file__, "-v"])