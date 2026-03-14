import argparse
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Add project root to path so shared/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Researcher — Comedy Trend Brief")
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Start persistent scheduler (daily at 07:30) instead of one-shot run",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=7,
        help="Hour for scheduled run (default: 7)",
    )
    parser.add_argument(
        "--minute",
        type=int,
        default=30,
        help="Minute for scheduled run (default: 30)",
    )
    args = parser.parse_args()

    if args.scheduled:
        from agent_researcher.scheduler import start_scheduler

        start_scheduler(hour=args.hour, minute=args.minute)
    else:
        from agent_researcher.runner import run

        asyncio.run(run())


if __name__ == "__main__":
    main()
