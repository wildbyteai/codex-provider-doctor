from __future__ import annotations

import hashlib
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: write_checksums.py <dist-directory>")
    distribution = Path(sys.argv[1])
    artifacts = sorted(
        path
        for path in distribution.iterdir()
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    if not artifacts:
        raise SystemExit("no build artifacts found")
    lines = []
    for artifact in artifacts:
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        lines.append(f"{digest}  {artifact.name}")
    (distribution / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
