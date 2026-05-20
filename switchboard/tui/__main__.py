"""Entry point for Switchboard TUI."""

import sys
from typing import NoReturn

from . import cli
from .app import SwitchboardApp


def main() -> None:
    """Main entry point for the TUI application."""
    try:
        # Parse command line arguments
        args = cli.parse_arguments()

        # Setup artifacts directory
        cli.setup_artifacts_directory(args.artifacts_dir)

        # Create and run the application
        app = SwitchboardApp(
            artifacts_dir=args.artifacts_dir,
            poll_interval=args.poll_interval,
            config=getattr(args, 'config', None)
        )

        app.run()

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT

    except ImportError as e:
        print(f"Error: Missing dependency: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()