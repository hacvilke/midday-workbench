from __future__ import annotations

import argparse
import sys

from .agent import Agent


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run the Midday Workbench CLI.")
    parser.add_argument("prompt", nargs="*", help="Prompt for the agent")
    args = parser.parse_args()
    prompt = " ".join(args.prompt).strip() or input("agent> ")
    print(Agent().run(prompt))


if __name__ == "__main__":
    main()
