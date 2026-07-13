from __future__ import annotations

from .config import load_config
from .service import SentinelService


def main() -> None:
    SentinelService(load_config()).serve_forever()


if __name__ == "__main__":
    main()
