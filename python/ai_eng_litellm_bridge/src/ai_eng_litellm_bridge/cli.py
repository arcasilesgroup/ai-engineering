"""CLI entry — `python -m ai_eng_litellm_bridge serve`.

Stays trivially simple by design. Real arg parsing lives here only so the
Docker `ENTRYPOINT` line stays identical across versions.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .server import serve


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_eng_litellm_bridge",
        description="ai-engineering Docker-isolated LiteLLM HTTP bridge.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve_p = sub.add_parser("serve", help="run the HTTP bridge")
    serve_p.add_argument(
        "--port",
        type=int,
        default=4848,
        help="TCP port to bind on 127.0.0.1 (default: 4848)",
    )
    serve_p.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="bind host; ONLY loopback addresses are accepted (default: 127.0.0.1)",
    )
    serve_p.add_argument(
        "--routing-config",
        dest="routing_config",
        type=str,
        default=None,
        help="path to the routing TOML; falls back to AI_ENGINEERING_ROUTING_PATH env var",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        serve(
            port=args.port,
            host=args.host,
            routing_config_path=args.routing_config,
        )
        return 0
    parser.error(f"unknown command: {args.command!r}")
    return 2  # unreachable — parser.error exits


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
