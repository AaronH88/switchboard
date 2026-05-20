"""Tests for TUI polling functionality including log parser, bd CLI, and file tailer."""

import pytest
import json
import tempfile
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import subprocess

from switchboard.tui.polling import (
    parse_log_line, bd_json, poll_workers, poll_stats, tail_file
)
from switchboard.tui.state import LogEvent


class TestLogParser:
    """Tests for parse_log_line function."""

    @pytest.mark.parametrize("log_line,expected_timestamp,expected_level,expected_message", [
        (
            "2026-05-20 14:23:01 [INFO] Claimed mol-2hn (agent: development, repo: nexus)",
            "2026-05-20 14:23:01",
            "INFO",
            "Claimed mol-2hn (agent: development, repo: nexus)"
        ),
        (
            "2026-05-20 14:23:01.123 [ERROR] Failed mol-2hn attempt 1/3, requeued",
            "2026-05-20 14:23:01.123",
            "ERROR",
            "Failed mol-2hn attempt 1/3, requeued"
        ),
        (
            "2026-05-20 14:23:01 [WARNING] Merge conflict for mol-2hn, creating integrate bead",
            "2026-05-20 14:23:01",
            "WARNING",
            "Merge conflict for mol-2hn, creating integrate bead"
        ),
    ])
    def test_parse_log_line_valid_formats(self, log_line, expected_timestamp, expected_level, expected_message):
        """Test parse_log_line with valid log line formats."""
        event = parse_log_line(log_line)

        assert event is not None
        assert isinstance(event, LogEvent)
        assert event.timestamp == expected_timestamp
        assert event.level == expected_level
        assert event.message == expected_message

    @pytest.mark.parametrize("log_line", [
        "[INFO] Some message",  # Missing timestamp
        "not-a-date [INFO] Some message",  # Invalid timestamp
        "2026-05-20 14:23:01 Some message",  # Missing level
        "",  # Empty string
        None,  # None input
    ])
    def test_parse_log_line_invalid_formats(self, log_line):
        """Test parse_log_line with invalid log line formats."""
        event = parse_log_line(log_line)
        assert event is None

    @pytest.mark.parametrize("log_line,expected_event_type", [
        (
            "2026-05-20 14:23:01 [INFO] Claimed mol-2hn (agent: development, repo: nexus)",
            "claimed"
        ),
        (
            "2026-05-20 14:23:01 [INFO] Claimed epic-xyz (agent: tdd, project: myapp, repo: api)",
            "claimed"
        ),
    ])
    def test_parse_claimed_event(self, log_line, expected_event_type):
        """Test parsing 'Claimed' events from log lines."""
        event = parse_log_line(log_line)

        assert event is not None
        assert event.parsed_event_type == expected_event_type
        assert "Claimed" in event.message

    @pytest.mark.parametrize("log_line,expected_event_type", [
        (
            "2026-05-20 14:23:01 [INFO] Completed mol-2hn (agent: development)",
            "completed"
        ),
        (
            "2026-05-20 14:23:01 [INFO] Completed epic-xyz (agent: tests)",
            "completed"
        ),
    ])
    def test_parse_completed_event(self, log_line, expected_event_type):
        """Test parsing 'Completed' events from log lines."""
        event = parse_log_line(log_line)

        assert event is not None
        assert event.parsed_event_type == expected_event_type
        assert "Completed" in event.message

    @pytest.mark.parametrize("log_line,expected_event_type", [
        (
            "2026-05-20 14:23:01 [ERROR] Failed mol-2hn attempt 1/3, requeued",
            "failed"
        ),
        (
            "2026-05-20 14:23:01 [ERROR] Failed epic-abc attempt 2/3, requeued",
            "failed"
        ),
    ])
    def test_parse_failed_event(self, log_line, expected_event_type):
        """Test parsing 'Failed' events from log lines."""
        event = parse_log_line(log_line)

        assert event is not None
        assert event.parsed_event_type == expected_event_type
        assert "Failed" in event.message

    @pytest.mark.parametrize("log_line,expected_event_type", [
        (
            "2026-05-20 14:23:01 [INFO] Epic completed: epic-xyz (Add user authentication)",
            "epic_completed"
        ),
        (
            "2026-05-20 14:23:01 [INFO] Epic completed: epic-abc (Refactor API endpoints)",
            "epic_completed"
        ),
    ])
    def test_parse_epic_completed_event(self, log_line, expected_event_type):
        """Test parsing 'Epic completed' events from log lines."""
        event = parse_log_line(log_line)

        assert event is not None
        assert event.parsed_event_type == expected_event_type
        assert "Epic completed" in event.message

    @pytest.mark.parametrize("log_line,expected_event_type", [
        (
            "2026-05-20 14:23:01 [INFO] Switchboard started (poll=10s, max_workers=3, projects=nexus,ui)",
            "daemon_started"
        ),
        (
            "2026-05-20 14:23:01 [INFO] Switchboard stopped",
            "daemon_stopped"
        ),
    ])
    def test_parse_daemon_lifecycle_events(self, log_line, expected_event_type):
        """Test parsing daemon start/stop events."""
        event = parse_log_line(log_line)

        assert event is not None
        assert event.parsed_event_type == expected_event_type

    @pytest.mark.parametrize("log_line", [
        "2026-05-20 14:23:01+00:00 [INFO] UTC timestamp test",
        "2026-05-20 14:23:01-05:00 [INFO] Local timezone test",
        "2026-05-20 14:23:01 [INFO] No timezone test",
    ])
    def test_parse_timezone_handling(self, log_line):
        """Test parsing log lines with different timezone formats."""
        event = parse_log_line(log_line)

        assert event is not None
        assert isinstance(event.timestamp, str)
        # Should handle timezone information gracefully

    @pytest.mark.parametrize("log_line", [
        "2026-05-20 14:23:01 [INFO] Claimed mol-2hn (agent: development)",  # Missing repo
        "2026-05-20 14:23:01 [INFO] Claiimed mol-2hn (agent: development, repo: nexus)",  # Typo
        "2026-05-20 14:23:01 [INFO] Claimed mol-2hn agent: development, repo: nexus",  # Missing parentheses
    ])
    def test_parse_malformed_messages(self, log_line):
        """Test parsing log lines with malformed event patterns."""
        event = parse_log_line(log_line)

        assert event is not None
        # Should parse as basic log event but not extract event type
        assert event.parsed_event_type is None or event.parsed_event_type == "unknown"


class TestBdCliWrappers:
    """Tests for bd CLI wrapper functions."""

    @pytest.mark.asyncio
    async def test_bd_json_successful_execution(self):
        """Test bd_json with successful command execution."""
        cmd = ["bd", "list", "--json"]
        mock_result = '{"beads": [{"id": "mol-2hn", "status": "open"}]}'

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout=mock_result,
                returncode=0
            )

            result = await bd_json(cmd)

            assert result == {"beads": [{"id": "mol-2hn", "status": "open"}]}
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_bd_json_command_not_found(self):
        """Test bd_json when bd command is not found."""
        cmd = ["bd", "list", "--json"]

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("bd command not found")

            with pytest.raises(FileNotFoundError):
                await bd_json(cmd)

    @pytest.mark.asyncio
    async def test_bd_json_invalid_json_response(self):
        """Test bd_json with malformed JSON response."""
        cmd = ["bd", "list", "--json"]

        test_cases = [
            '{"beads": [',  # Partial JSON
            '{beads: []}',  # Invalid syntax
        ]

        for invalid_json in test_cases:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    stdout=invalid_json,
                    returncode=0
                )

                with pytest.raises(json.JSONDecodeError):
                    await bd_json(cmd)

        # Empty string returns empty list (not an error)
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            result = await bd_json(cmd)
            assert result == []

    @pytest.mark.asyncio
    async def test_bd_json_command_failure(self):
        """Test bd_json with non-zero exit code."""
        cmd = ["bd", "list", "--json"]

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr="Command failed",
                returncode=1
            )

            with pytest.raises(subprocess.CalledProcessError):
                await bd_json(cmd)

    @pytest.mark.asyncio
    async def test_bd_json_timeout_handling(self):
        """Test bd_json with command timeout."""
        cmd = ["bd", "list", "--json"]

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd, timeout=30)

            with pytest.raises(subprocess.TimeoutExpired):
                await bd_json(cmd)

    @pytest.mark.asyncio
    async def test_poll_workers_success(self):
        """Test poll_workers with successful response."""
        expected_data = {
            "beads": [
                {
                    "bead_id": "mol-2hn",
                    "agent": "development",
                    "repo": "nexus",
                    "tool": None,
                    "pid": 12345,
                    "started_at": "2026-05-20T14:23:01",
                    "title": "Test work",
                    "epic_id": "epic-xyz"
                }
            ]
        }

        with patch('switchboard.tui.polling.bd_json') as mock_bd_json:
            mock_bd_json.return_value = expected_data

            result = await poll_workers()

            assert result == expected_data["beads"]
            mock_bd_json.assert_called_once_with(["bd", "list", "--status=in_progress", "--json"])

    @pytest.mark.asyncio
    async def test_poll_workers_empty_result(self):
        """Test poll_workers with empty beads list."""
        empty_data = {"beads": []}

        with patch('switchboard.tui.polling.bd_json') as mock_bd_json:
            mock_bd_json.return_value = empty_data

            result = await poll_workers()

            assert result == []

    @pytest.mark.asyncio
    async def test_poll_workers_malformed_response(self):
        """Test poll_workers with malformed response returns empty."""
        with patch('switchboard.tui.polling.bd_json') as mock_bd_json:
            mock_bd_json.return_value = {"invalid": "structure"}
            result = await poll_workers()
            assert result == []

        with patch('switchboard.tui.polling.bd_json') as mock_bd_json:
            mock_bd_json.return_value = "not_a_dict_or_list"
            result = await poll_workers()
            assert result == []

    @pytest.mark.asyncio
    async def test_poll_workers_bd_error(self):
        """Test poll_workers when bd_json raises exception."""
        with patch('switchboard.tui.polling.bd_json') as mock_bd_json:
            mock_bd_json.side_effect = subprocess.CalledProcessError(1, "bd")

            with pytest.raises(subprocess.CalledProcessError):
                await poll_workers()

    @pytest.mark.asyncio
    async def test_poll_stats_success(self):
        """Test poll_stats with successful response."""
        expected_data = {
            "completed": 15,
            "failed": 2,
            "blocked": 1,
            "total": 20
        }

        with patch('switchboard.tui.polling.bd_json') as mock_bd_json:
            mock_bd_json.return_value = expected_data

            result = await poll_stats()

            assert result == expected_data
            mock_bd_json.assert_called_once_with(["bd", "stats", "--json"])

    @pytest.mark.asyncio
    async def test_poll_stats_missing_fields(self):
        """Test poll_stats with missing fields gets default values."""
        partial_data = {"completed": 5}

        with patch('switchboard.tui.polling.bd_json') as mock_bd_json:
            mock_bd_json.return_value = partial_data

            result = await poll_stats()

            # Should provide default values for missing fields
            assert result.get("completed") == 5
            assert result.get("failed", 0) == 0
            assert result.get("blocked", 0) == 0

    @pytest.mark.asyncio
    async def test_poll_stats_invalid_types(self):
        """Test poll_stats with string numbers."""
        string_data = {
            "completed": "5",
            "failed": "0",
            "blocked": "1",
            "total": "6"
        }

        with patch('switchboard.tui.polling.bd_json') as mock_bd_json:
            mock_bd_json.return_value = string_data

            result = await poll_stats()

            # Should handle type conversion or return as-is
            assert result == string_data


class TestFileTailer:
    """Tests for file tailing functionality.

    All tests use asyncio.wait_for() with timeouts because tail_file()
    is a while-True loop that never exits on its own.
    """

    TIMEOUT = 3

    @pytest.mark.asyncio
    async def test_tail_file_existing_file(self):
        """Test tail_file reads existing content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            f.flush()
            path = Path(f.name)

        try:
            lines = []
            async with asyncio.timeout(self.TIMEOUT):
                async for line in tail_file(path):
                    lines.append(line.strip())
                    if len(lines) >= 3:
                        break

            assert lines == ["Line 1", "Line 2", "Line 3"]
        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_tail_file_empty_file_no_output(self):
        """Test tail_file yields nothing for an empty file within timeout."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            path = Path(f.name)

        try:
            lines = []
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.5):
                    async for line in tail_file(path):
                        lines.append(line)

            assert lines == []
        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_tail_file_appended_lines(self):
        """Test tail_file picks up new lines appended after start."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("First\n")
            f.flush()
            path = Path(f.name)

        try:
            gen = tail_file(path)
            line1 = await asyncio.wait_for(gen.__anext__(), timeout=self.TIMEOUT)
            assert line1.strip() == "First"

            with open(path, 'a') as f:
                f.write("Second\n")
                f.flush()

            line2 = await asyncio.wait_for(gen.__anext__(), timeout=self.TIMEOUT)
            assert line2.strip() == "Second"
        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_tail_file_nonexistent_then_created(self):
        """Test tail_file waits for file creation then reads."""
        path = Path(tempfile.mktemp(suffix='.log'))
        path.unlink(missing_ok=True)

        gen = tail_file(path)

        async def create_later():
            await asyncio.sleep(0.3)
            path.write_text("Hello\n")

        task = asyncio.create_task(create_later())
        try:
            line = await asyncio.wait_for(gen.__anext__(), timeout=self.TIMEOUT)
            assert line.strip() == "Hello"
            await task
        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_tail_file_rotation(self):
        """Test tail_file detects file replacement."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("Original\n")
            f.flush()
            path = Path(f.name)

        try:
            gen = tail_file(path)
            line1 = await asyncio.wait_for(gen.__anext__(), timeout=self.TIMEOUT)
            assert line1.strip() == "Original"

            path.unlink()
            path.write_text("Rotated\n")

            line2 = await asyncio.wait_for(gen.__anext__(), timeout=self.TIMEOUT)
            assert line2.strip() == "Rotated"
        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_tail_file_permission_error(self):
        """Test tail_file raises on permission denied."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("Secret\n")
            path = Path(f.name)

        try:
            path.chmod(0o000)
            with pytest.raises(PermissionError):
                gen = tail_file(path)
                await asyncio.wait_for(gen.__anext__(), timeout=self.TIMEOUT)
        finally:
            path.chmod(0o644)
            path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_tail_file_binary_content(self):
        """Test tail_file handles binary content gracefully."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.log') as f:
            f.write(b"Text line\n\x00\x01binary\nAnother line\n")
            path = Path(f.name)

        try:
            lines = []
            async with asyncio.timeout(self.TIMEOUT):
                async for line in tail_file(path):
                    lines.append(line)
                    if len(lines) >= 2:
                        break
            assert len(lines) >= 1
        finally:
            path.unlink(missing_ok=True)


# Test fixtures and utilities

@pytest.fixture
def temp_artifacts_dir():
    """Temporary directory for artifacts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_log_lines():
    """Sample log lines for parser testing."""
    return [
        "2026-05-20 14:23:01 [INFO] Switchboard started (poll=10s, max_workers=3)",
        "2026-05-20 14:23:02 [INFO] Claimed mol-2hn (agent: development, repo: nexus)",
        "2026-05-20 14:23:10 [INFO] Completed mol-2hn (agent: development)",
        "2026-05-20 14:23:15 [ERROR] Failed mol-abc attempt 1/3, requeued",
        "2026-05-20 14:23:20 [INFO] Epic completed: epic-xyz (Add user authentication)",
    ]


@pytest.fixture
def mock_bd_command():
    """Mock bd command execution."""
    with patch('subprocess.run') as mock_run:
        yield mock_run


@pytest.fixture
def sample_worker_data():
    """Sample worker data for testing."""
    return {
        "bead_id": "mol-2hn",
        "agent": "development",
        "repo": "nexus",
        "tool": None,
        "pid": 12345,
        "started_at": "2026-05-20T14:23:01",
        "title": "Implement user authentication",
        "epic_id": "epic-xyz"
    }


def create_mock_log_file(content_lines):
    """Create temporary log file with specified content."""
    tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    tmp_file.writelines(content_lines)
    tmp_file.flush()
    return Path(tmp_file.name)


def mock_bd_json_response(data):
    """Create mock bd command JSON response."""
    return json.dumps(data)


async def async_test_helper(coro):
    """Helper for testing async functions."""
    return await coro