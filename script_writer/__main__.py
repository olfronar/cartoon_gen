import argparse
import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Add project root to path so shared/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _parse_pick(value: str) -> list[int]:
    """Parse comma-separated 1-based item numbers into 0-based indices."""
    indices = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        num = int(part)
        if num < 1:
            raise argparse.ArgumentTypeError(f"Item numbers must be >= 1, got {num}")
        indices.append(num - 1)  # convert to 0-based
    return indices


def main() -> None:
    parser = argparse.ArgumentParser(description="Script Writer — Generate cartoon scripts")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Brief date to process (YYYY-MM-DD). Default: latest available.",
    )
    parser.add_argument(
        "--pick",
        type=str,
        default=None,
        help=(
            "Comma-separated item numbers from the brief to use (1-based). "
            "Numbers 1-5 are top picks, 6-15 are also-notable. "
            "Example: --pick 1,3,7. Default: auto top-5."
        ),
    )
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else None
    pick_indices = _parse_pick(args.pick) if args.pick else None

    from script_writer.pipeline.runner import run

    asyncio.run(run(target_date=target_date, pick_indices=pick_indices))


if __name__ == "__main__":
    main()
