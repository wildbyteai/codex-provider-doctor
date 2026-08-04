from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import textwrap
import unittest

from tests.test_cli_catalog import run_doctor


def install_fake_codex(
    bin_directory: Path,
    version: str = "0.146.0-alpha.9.2",
    plugin_marketplace_failure: bool = False,
    login_status: str = "Logged in using ChatGPT",
    plugin_items: list[dict[str, object]] | None = None,
) -> None:
    if plugin_items is None:
        plugin_items = [
            {
                "name": "chrome",
                "installed": True,
                "enabled": True,
                "internal_token": "raw-command-output-must-not-leak",
            },
            {
                "name": "browser",
                "installed": True,
                "enabled": False,
            },
        ]
    implementation = bin_directory / "fake_codex.py"
    implementation.write_text(
        textwrap.dedent(
            """
            import json
            import sys

            secret = "raw-command-output-must-not-leak"
            if sys.argv[1:] == ["--version"]:
                print("codex-cli __FAKE_VERSION__")
                raise SystemExit(0)
            if sys.argv[1:] == ["login", "status"]:
                print(__LOGIN_STATUS__, file=sys.stderr)
                print(secret, file=sys.stderr)
                raise SystemExit(0)
            if sys.argv[1:] == ["plugin", "list", "--json"]:
                if __PLUGIN_MARKETPLACE_FAILURE__:
                    print(
                        "Error: marketplace root /private/path/secret-marketplace "
                        "does not contain a supported manifest",
                        file=sys.stderr,
                    )
                    raise SystemExit(1)
                print(json.dumps({
                    "installed": __PLUGIN_ITEMS__,
                    "available": [],
                }))
                raise SystemExit(0)
            raise SystemExit(4)
            """
        )
        .lstrip()
        .replace("__FAKE_VERSION__", version)
        .replace("__PLUGIN_MARKETPLACE_FAILURE__", repr(plugin_marketplace_failure))
        .replace("__LOGIN_STATUS__", repr(login_status))
        .replace("__PLUGIN_ITEMS__", repr(plugin_items)),
        encoding="utf-8",
    )

    if os.name == "nt":
        (bin_directory / "codex.cmd").write_text(
            f'@"{sys.executable}" "{implementation}" %*\r\n',
            encoding="utf-8",
        )
    else:
        executable = bin_directory / "codex"
        executable.write_text(
            f'#!{sys.executable}\nexec(compile(open({str(implementation)!r}, "rb").read(), {str(implementation)!r}, "exec"))\n',
            encoding="utf-8",
        )
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)


class RuntimeProbeTests(unittest.TestCase):
    def test_login_and_plugin_probes_keep_only_safe_status_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            bin_directory = root / "bin"
            codex_home.mkdir()
            bin_directory.mkdir()
            (codex_home / "config.toml").write_text(
                '\n'.join(['model = "gpt-5.6"', 'cli_auth_credentials_store = "file"']),
                encoding="utf-8",
            )
            auth_secret = "auth-json-content-must-not-leak"
            (codex_home / "auth.json").write_text(
                json.dumps({"token": auth_secret}),
                encoding="utf-8",
            )
            install_fake_codex(bin_directory)

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--json",
                extra_env={
                    "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertNotIn(auth_secret, serialized)
            self.assertNotIn("raw-command-output-must-not-leak", serialized)
            self.assertEqual(
                {
                    "auth": report["auth"],
                    "plugins": report["plugins"],
                    "runtime": report["runtime"],
                },
                {
                    "auth": {
                        "credentials_store": "file",
                        "cache_path": "$CODEX_HOME/auth.json",
                        "cache_exists": True,
                        "cache_read": False,
                        "login_probe": "ok",
                        "login_method": "chatgpt",
                    },
                    "plugins": {
                        "probe": "ok",
                        "features": {"apps": True, "remote_plugin": True},
                        "inventory_count": 2,
                        "chrome": {"found": True, "installed": True, "enabled": True},
                    },
                    "runtime": {
                        "codex_command_found": True,
                        "version_probe": "ok",
                        "codex_version": "0.146.0-alpha.9.2",
                    },
                },
            )

    def test_private_plugin_name_is_hidden_and_not_mistaken_for_chrome(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            bin_directory = root / "bin"
            codex_home.mkdir()
            bin_directory.mkdir()
            (codex_home / "config.toml").write_text('model = "gpt-5.6"\n', encoding="utf-8")
            private_name = "company-private-chrome-helper"
            install_fake_codex(
                bin_directory,
                plugin_items=[
                    {"name": private_name, "installed": True, "enabled": True},
                ],
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--json",
                extra_env={
                    "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertNotIn(private_name, json.dumps(report, ensure_ascii=False))
            self.assertEqual(
                {
                    "inventory_count": report["plugins"]["inventory_count"],
                    "chrome": report["plugins"]["chrome"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "inventory_count": 1,
                    "chrome": {"found": False, "installed": False, "enabled": False},
                    "finding_codes": ["plugins.chrome.not_installed"],
                },
            )

    def test_signed_out_login_status_wins_over_api_key_words(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            bin_directory = root / "bin"
            codex_home.mkdir()
            bin_directory.mkdir()
            (codex_home / "config.toml").write_text('model = "gpt-5.6"\n', encoding="utf-8")
            install_fake_codex(
                bin_directory,
                login_status="Not logged in; API key not found",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--json",
                extra_env={
                    "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "login_method": report["auth"]["login_method"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "login_method": "signed_out",
                    "finding_codes": ["auth.login_not_confirmed"],
                },
            )

    def test_disabled_plugin_features_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "gpt-5.6"',
                        "",
                        "[features]",
                        "apps = false",
                        "remote_plugin = false",
                    ]
                ),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "features": report["plugins"]["features"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "features": {"apps": False, "remote_plugin": False},
                    "finding_codes": [
                        "plugins.feature.apps_disabled",
                        "plugins.feature.remote_plugin_disabled",
                    ],
                },
            )

    def test_invalid_plugin_marketplace_snapshot_is_reported_without_leaking_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            bin_directory = root / "bin"
            codex_home.mkdir()
            bin_directory.mkdir()
            (codex_home / "config.toml").write_text('model = "gpt-5.6"\n', encoding="utf-8")
            install_fake_codex(bin_directory, plugin_marketplace_failure=True)

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--json",
                extra_env={
                    "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertNotIn("secret-marketplace", serialized)
            self.assertEqual(
                {
                    "plugin_probe": report["plugins"]["probe"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "plugin_probe": "failed",
                    "finding_codes": ["plugins.marketplace_snapshot_invalid"],
                },
            )

    def test_versioned_compatibility_rule_warns_on_a_different_codex_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            bin_directory = root / "bin"
            codex_home.mkdir()
            bin_directory.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "deepseek-v4-flash",
                                "display_name": "DeepSeek V4 Flash",
                                "tool_mode": "direct",
                                "supports_search_tool": False,
                                "use_responses_lite": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "deepseek-v4-flash"',
                        'model_provider = "custom"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                    ]
                ),
                encoding="utf-8",
            )
            install_fake_codex(bin_directory, version="0.200.0")

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--compat-rule",
                "deepseek-direct-tools-2026-08-03",
                "--json",
                extra_env={
                    "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "version": report["runtime"]["codex_version"],
                    "suggested_changes": report["compatibility"]["rules"][0]["suggested_changes"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "version": "0.200.0",
                    "suggested_changes": [],
                    "finding_codes": ["compat.rule_version_differs"],
                },
            )


if __name__ == "__main__":
    unittest.main()
