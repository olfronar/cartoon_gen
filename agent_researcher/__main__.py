import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Add project root to path so shared/ is importable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_researcher.runner import run  # noqa: E402


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
