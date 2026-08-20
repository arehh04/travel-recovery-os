"""TR-OS CLI entry point.

Usage:
    python -m tros
    python -m tros demo
"""

from __future__ import annotations


def main() -> None:
    from demo.run_demo import main as run_demo
    run_demo()


if __name__ == "__main__":
    main()
