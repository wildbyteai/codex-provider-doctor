from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


def _run(executable: Path, working_directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(executable), *arguments],
        cwd=working_directory,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )


def _expect_returncode(result: subprocess.CompletedProcess[str], expected: int, label: str) -> None:
    if result.returncode != expected:
        raise SystemExit(f"{label} returned {result.returncode}, expected {expected}")


def _load_json(result: subprocess.CompletedProcess[str], label: str) -> dict[str, object]:
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"{label} did not return JSON") from error
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} did not return a JSON object")
    return payload


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_binary.py <dist-directory>")
    distribution = Path(sys.argv[1])
    candidates = sorted(
        path
        for path in distribution.iterdir()
        if path.is_file() and path.name in {"codex-provider-doctor", "codex-provider-doctor.exe"}
    )
    if len(candidates) != 1:
        raise SystemExit(f"expected one executable, found {len(candidates)}")
    executable = candidates[0].resolve()
    result = _run(executable, distribution, "--help")
    if result.returncode != 0 or "codex-provider-doctor" not in result.stdout:
        raise SystemExit("built executable failed its --help smoke test")

    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        codex_home = root / "codex-home"
        codex_home.mkdir()
        common = (
            "--codex-home",
            str(codex_home),
            "--system-config",
            str(root / "missing-system.toml"),
            "--no-command-checks",
        )

        clean_json = _run(executable, root, *common, "--json")
        _expect_returncode(clean_json, 0, "clean JSON diagnosis")
        clean_payload = _load_json(clean_json, "clean JSON diagnosis")
        if clean_payload.get("summary") != {"status": "ok", "errors": 0, "warnings": 0}:
            raise SystemExit("clean JSON diagnosis returned an unexpected summary")

        clean_human = _run(executable, root, *common, "--lang", "en")
        _expect_returncode(clean_human, 0, "clean human diagnosis")
        if "This report is read-only" not in clean_human.stdout:
            raise SystemExit("clean human diagnosis omitted the read-only statement")

        config_path = codex_home / "config.toml"
        config_path.write_text(
            '\n'.join(['model = "smoke-model"', "", "[features]", "apps = false"]),
            encoding="utf-8",
        )
        warning_json = _run(executable, root, *common, "--json")
        _expect_returncode(warning_json, 1, "warning diagnosis")
        warning_payload = _load_json(warning_json, "warning diagnosis")
        if warning_payload.get("summary", {}).get("status") != "warning":
            raise SystemExit("warning diagnosis did not report warning status")

        config_path.write_text(
            '\n'.join(['model = "smoke-model"', 'model_provider = "missing-provider"']),
            encoding="utf-8",
        )
        error_json = _run(executable, root, *common, "--json")
        _expect_returncode(error_json, 2, "configuration error diagnosis")
        error_payload = _load_json(error_json, "configuration error diagnosis")
        if error_payload.get("summary", {}).get("status") != "error":
            raise SystemExit("configuration error diagnosis did not report error status")

        tool_error = _run(executable, root, *common, "--config", "missing-equals", "--json")
        _expect_returncode(tool_error, 3, "tool failure diagnosis")
        tool_error_payload = _load_json(tool_error, "tool failure diagnosis")
        if tool_error_payload.get("tool_error", {}).get("code") != "doctor.internal_failure":
            raise SystemExit("tool failure diagnosis omitted the stable error code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
