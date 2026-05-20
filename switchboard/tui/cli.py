"""CLI argument parsing for Switchboard TUI."""

import argparse
import sys
from pathlib import Path
from typing import Any


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog='switchboard-tui',
        description='Switchboard TUI - Terminal user interface for monitoring agent pipelines',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_help_text()
    )

    parser.add_argument(
        '--artifacts-dir',
        default='artifacts/',
        help='Directory for artifacts and logs (default: artifacts/)'
    )

    parser.add_argument(
        '--poll-interval',
        type=int,
        default=10,
        metavar='SECONDS',
        help='Polling interval in seconds (default: 10)'
    )

    parser.add_argument(
        '--config',
        metavar='PATH',
        help='Optional path to switchboard.yaml configuration file'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='switchboard-tui 1.0.0'
    )

    try:
        args = parser.parse_args()

        # Validate poll interval
        args.poll_interval = validate_poll_interval(args.poll_interval)

        return args

    except SystemExit as e:
        # Re-raise SystemExit with proper codes
        if e.code == 0:  # Help or version
            raise
        else:  # Error
            sys.exit(2)


def validate_poll_interval(interval: int) -> int:
    """Validate poll interval value."""
    if interval <= 0:
        raise ValueError(f"Poll interval must be positive, got {interval}")

    return interval


def setup_artifacts_directory(artifacts_dir: str) -> bool:
    """Create artifacts directory if it doesn't exist."""
    path = Path(artifacts_dir)

    try:
        if path.exists():
            if not path.is_dir():
                raise ValueError(f"Artifacts path exists but is not a directory: {path}")
            return True

        # Create directory with parents
        path.mkdir(parents=True, exist_ok=True)
        return True

    except PermissionError:
        raise PermissionError(f"Permission denied creating directory: {path}")
    except OSError as e:
        raise OSError(f"Failed to create directory {path}: {e}")


def get_help_text() -> str:
    """Get additional help text."""
    return """
Examples:
  switchboard-tui                           # Use defaults
  switchboard-tui --poll-interval 5        # Poll every 5 seconds
  switchboard-tui --artifacts-dir /tmp     # Custom artifacts directory
  switchboard-tui --config switchboard.yaml # Use configuration file

The TUI monitors agent pipelines by polling the bd CLI and tailing log files.
Press 'q' to quit the application.
"""