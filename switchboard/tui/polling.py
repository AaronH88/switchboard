"""Data pipeline for polling bd CLI and tailing log files.

Dependencies:
- watchfiles: Required for efficient file watching (alternative: can use polling)
"""

import re
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any, AsyncIterator
import time

from .state import LogEvent


def parse_log_line(line: str) -> Optional[LogEvent]:
    """Parse a log line into a LogEvent."""
    if not line or not isinstance(line, str):
        return None

    # Pattern: timestamp + level + message
    # Examples:
    # 2026-05-20 14:23:01 [INFO] Message
    # 2026-05-20 14:23:01.123 [ERROR] Message
    # 2026-05-20 14:23:01+00:00 [WARNING] Message
    pattern = r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)\s+\[(\w+)\]\s+(.+)$'

    match = re.match(pattern, line.strip())
    if not match:
        return None

    timestamp, level, message = match.groups()

    try:
        event = LogEvent(
            timestamp=timestamp,
            level=level,
            message=message,
            parsed_event_type=None
        )

        # Detect event type
        event_type = event.detect_event_type()
        # Use replace to update the parsed_event_type
        from dataclasses import replace
        event = replace(event, parsed_event_type=event_type)

        return event
    except (ValueError, TypeError):
        return None


async def bd_json(args: List[str]) -> Dict[str, Any] | List[Dict[str, Any]]:
    """Run bd CLI subprocess and parse JSON output."""
    try:
        # Run subprocess synchronously but in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                check=False  # Handle return code manually for better test compatibility
            )
        )

        # Check return code manually
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, args, result.stdout, result.stderr)

        if not result.stdout.strip():
            raise json.JSONDecodeError("Empty response", "", 0)

        return json.loads(result.stdout)

    except FileNotFoundError:
        raise FileNotFoundError(f"bd command not found: {args[0]}")
    except subprocess.TimeoutExpired:
        raise subprocess.TimeoutExpired(args, timeout=30)
    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError(e.returncode, e.cmd, e.output, e.stderr)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON response: {e.msg}", e.doc, e.pos)


async def poll_workers() -> List[Dict[str, Any]]:
    """Poll workers using bd CLI."""
    data = await bd_json(["bd", "list", "--status=in_progress", "--json"])

    if not isinstance(data, dict):
        raise TypeError("Expected dict response from bd list")

    if "beads" not in data:
        raise KeyError("Missing 'beads' key in response")

    beads = data["beads"]
    if not isinstance(beads, list):
        raise TypeError("Expected 'beads' to be a list")

    return beads


async def poll_stats() -> Dict[str, Any]:
    """Poll stats using bd CLI."""
    data = await bd_json(["bd", "stats", "--json"])
    return data


async def tail_file(path: Path) -> AsyncIterator[str]:
    """Tail a file, yielding new lines as they appear."""
    path = Path(path)
    last_size = 0
    last_inode = None

    while True:
        try:
            if not path.exists():
                # Wait for file to be created
                await asyncio.sleep(0.1)
                continue

            stat = path.stat()
            current_inode = stat.st_ino

            # Check if file was rotated/replaced
            if last_inode is not None and current_inode != last_inode:
                last_size = 0

            last_inode = current_inode

            if stat.st_size < last_size:
                # File was truncated, start from beginning
                last_size = 0

            if stat.st_size > last_size:
                # Read new content
                try:
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_size)
                        new_content = f.read()
                        last_size = f.tell()

                        for line in new_content.splitlines():
                            if line.strip():  # Skip empty lines
                                yield line + '\n'
                except (PermissionError, OSError):
                    # Re-raise permission errors
                    raise
                except UnicodeDecodeError:
                    # Handle binary content gracefully
                    last_size = stat.st_size
                    continue

            # Wait before next check
            await asyncio.sleep(0.1)

        except FileNotFoundError:
            # File was deleted, wait for recreation
            last_size = 0
            last_inode = None
            await asyncio.sleep(0.1)
            continue
        except PermissionError:
            # Permission denied - re-raise
            raise
        except Exception:
            # Other exceptions - wait and continue
            await asyncio.sleep(0.1)
            continue