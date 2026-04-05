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
        description="Caption Maker — Add whisper-based captions to cartoon videos"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to process (YYYY-MM-DD). Default: latest available.",
    )
    parser.add_argument(
        "--compile",
        action="store_true",
        default=False,
        help="Assemble a final video from all captioned videos.",
    )
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else None

    from caption_maker.pipeline.runner import run

    asyncio.run(run(target_date=target_date, compile=args.compile))


if __name__ == "__main__":
    main()
