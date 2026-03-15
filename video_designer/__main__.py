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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Video Designer — Generate cartoon videos from static shots"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to process (YYYY-MM-DD). Default: latest available.",
    )
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else None

    from video_designer.pipeline.runner import run

    asyncio.run(run(target_date=target_date))


if __name__ == "__main__":
    main()
