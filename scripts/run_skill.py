#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


MINIMUM_PYTHON = (3, 11)


def main() -> int:
    if sys.version_info < MINIMUM_PYTHON:
        sys.stderr.write(
            "Codex Provider Doctor 需要 Python 3.11 或更高版本；未执行任何检测或修改。\n"
        )
        return 3

    skill_root = Path(__file__).resolve().parents[1]
    source_root = skill_root / "src"
    package_entry = source_root / "codex_provider_doctor" / "cli.py"
    if not package_entry.is_file():
        sys.stderr.write(
            "Codex Provider Doctor 的内置检测代码不完整；未执行任何检测或修改。\n"
        )
        return 3

    sys.path.insert(0, str(source_root))
    from codex_provider_doctor.cli import main as doctor_main

    return doctor_main()


if __name__ == "__main__":
    raise SystemExit(main())
