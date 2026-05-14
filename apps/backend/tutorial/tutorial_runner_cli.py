#!/usr/bin/env python3
"""
Tutorial Runner CLI
===================

Command-line interface for running the tutorial from the Electron frontend.
Emits JSON events to stdout for IPC communication.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from tutorial_runner import TutorialRunner, PhaseEvent


def emit_json_event(event_type: str, data: dict) -> None:
    """Emit JSON event to stdout for IPC communication."""
    event = {
        "type": event_type,
        "timestamp": data.get("timestamp", ""),
        **data,
    }
    print(json.dumps(event), flush=True)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run tutorial build")
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Project root directory",
    )
    parser.add_argument(
        "--json-events",
        action="store_true",
        help="Emit JSON events to stdout for IPC communication",
    )
    args = parser.parse_args()

    # Configure logging (to stderr to avoid polluting stdout JSON)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    try:
        # Initialize tutorial runner
        runner = TutorialRunner(project_dir=args.project_dir)

        # Register event callbacks (emit JSON to stdout)
        if args.json_events:
            def on_phase_start(event: PhaseEvent) -> None:
                emit_json_event("phase_start", {
                    "phase": event.phase.value,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                })

            def on_phase_progress(event: PhaseEvent) -> None:
                emit_json_event("phase_progress", {
                    "phase": event.phase.value,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                })

            def on_phase_complete(event: PhaseEvent) -> None:
                emit_json_event("phase_complete", {
                    "phase": event.phase.value,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                })

            runner.on_phase_start(on_phase_start)
            runner.on_phase_progress(on_phase_progress)
            runner.on_phase_complete(on_phase_complete)

        # Run tutorial
        result = runner.run()

        # Emit completion event
        if args.json_events:
            if result["status"] == "success":
                emit_json_event("complete", result)
            elif result["status"] == "cancelled":
                emit_json_event("cancelled", result)
            else:
                emit_json_event("error", {
                    "message": result.get("error", "Tutorial failed"),
                    **result,
                })

        # Return exit code
        if result["status"] == "success":
            return 0
        else:
            return 1

    except KeyboardInterrupt:
        logging.info("Tutorial cancelled by user")
        if args.json_events:
            emit_json_event("cancelled", {"message": "Tutorial cancelled by user"})
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logging.error(f"Tutorial failed: {e}", exc_info=True)
        if args.json_events:
            emit_json_event("error", {
                "message": str(e),
                "error_type": type(e).__name__,
            })
        return 1


if __name__ == "__main__":
    sys.exit(main())
