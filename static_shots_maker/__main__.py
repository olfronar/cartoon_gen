import argparse
import asyncio
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Suppress noisy gRPC fork/absl warnings from google-genai SDK
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Suppress google_genai AFC info spam
logging.getLogger("google_genai.models").setLevel(logging.WARNING)

# Add project root to path so shared/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Static Shots Maker — Generate static shots from cartoon scripts"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Script date to process (YYYY-MM-DD). Default: latest available.",
    )
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else None

    from static_shots_maker.pipeline.runner import run

    asyncio.run(run(target_date=target_date))


if __name__ == "__main__":
    main()
