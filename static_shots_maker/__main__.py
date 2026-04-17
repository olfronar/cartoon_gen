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
    parser.add_argument(
        "--model",
        type=str,
        choices=["opus", "grok"],
        default="opus",
        help="LLM for prompt rewriting: opus (claude-opus-4-7) or grok.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=False,
        help="Enable visual verification of generated shots via Claude vision.",
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=None,
        help="Number of candidate images per scene (default 1, max 3). Implies --verify.",
    )
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else None
    model_override = "grok-4.20-beta-latest-reasoning" if args.model == "grok" else None

    from static_shots_maker.pipeline.runner import run

    asyncio.run(
        run(
            target_date=target_date,
            model_override=model_override,
            verify=args.verify,
            candidates=args.candidates,
        )
    )


if __name__ == "__main__":
    main()
