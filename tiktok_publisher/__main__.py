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
        description="TikTok Publisher — Upload cartoon videos to TikTok"
    )
    parser.add_argument(
        "command",
        choices=["auth", "upload"],
        help="Command: auth (OAuth flow) or upload (publish videos)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to process (YYYY-MM-DD). Default: latest available.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        default=False,
        help="Force refresh tokens (auth command only).",
    )
    args = parser.parse_args()

    from shared.config import load_settings

    settings = load_settings()

    if args.command == "auth":
        from tiktok_publisher.auth import authorize, refresh_tokens

        if args.refresh:
            refresh_tokens(settings)
        else:
            authorize(settings)

    elif args.command == "upload":
        target_date = date.fromisoformat(args.date) if args.date else None

        from tiktok_publisher.pipeline.runner import run

        asyncio.run(run(settings=settings, target_date=target_date))


if __name__ == "__main__":
    main()
