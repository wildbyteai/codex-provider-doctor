from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def run_doctor(*arguments: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "codex_provider_doctor", *arguments],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class CatalogResolutionTests(unittest.TestCase):
    def test_profile_overrides_user_catalog_and_selects_active_model(self) -> None:
        codex_home = FIXTURES / "profile-home"

        result = run_doctor(
            "--codex-home",
            str(codex_home),
            "--profile",
            "work",
            "--system-config",
            str(FIXTURES / "missing-system.toml"),
            "--no-command-checks",
            "--json",
            extra_env={"DEEPSEEK_API_KEY": "test-only-placeholder"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            {
                "model": report["effective"]["model"],
                "catalog_source": report["effective"]["origins"]["model_catalog_json"],
                "catalog_model_count": report["catalog"]["model_count"],
                "catalog_model": report["catalog"]["selected_model"]["slug"],
                "supports_search_tool": report["catalog"]["selected_model"]["supports_search_tool"],
            },
            {
                "model": "deepseek-v4-flash",
                "catalog_source": str(codex_home / "work.config.toml"),
                "catalog_model_count": 1,
                "catalog_model": "deepseek-v4-flash",
                "supports_search_tool": False,
            },
        )

    def test_trusted_project_config_overrides_user_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            project = root / "project"
            working_directory = project / "packages" / "app"
            codex_home.mkdir()
            working_directory.mkdir(parents=True)
            (project / ".git").mkdir()
            (project / ".codex").mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {"slug": "base", "display_name": "Base"},
                            {"slug": "project-model", "display_name": "Project Model"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "base"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        f"[projects.{json.dumps(str(project))}]",
                        'trust_level = "trusted"',
                    ]
                ),
                encoding="utf-8",
            )
            project_config = project / ".codex" / "config.toml"
            project_config.write_text('model = "project-model"\n', encoding="utf-8")

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--cwd",
                str(working_directory),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "model": report["effective"]["model"],
                    "model_origin": report["effective"]["origins"]["model"],
                    "project_trust": report["project"]["trust_level"],
                    "project_layer_applied": next(
                        layer["applied"]
                        for layer in report["layers"]
                        if layer["path"] == str(project_config.resolve())
                    ),
                },
                {
                    "model": "project-model",
                    "model_origin": str(project_config.resolve()),
                    "project_trust": "trusted",
                    "project_layer_applied": True,
                },
            )

    def test_empty_project_root_markers_treats_working_directory_as_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            project = root / "project-without-vcs-marker"
            codex_home.mkdir()
            (project / ".codex").mkdir(parents=True)
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "base-model"',
                        "project_root_markers = []",
                        "",
                        f"[projects.{json.dumps(str(project))}]",
                        'trust_level = "trusted"',
                    ]
                ),
                encoding="utf-8",
            )
            project_config = project / ".codex" / "config.toml"
            project_config.write_text('model = "project-model"\n', encoding="utf-8")

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--cwd",
                str(project),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "model": report["effective"]["model"],
                    "project_root": report["project"]["root"],
                    "project_layer_applied": next(
                        layer["applied"]
                        for layer in report["layers"]
                        if layer["path"] == str(project_config.resolve())
                    ),
                },
                {
                    "model": "project-model",
                    "project_root": str(project.resolve()),
                    "project_layer_applied": True,
                },
            )

    def test_untrusted_project_config_is_reported_but_not_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            project = root / "project"
            codex_home.mkdir()
            (project / ".git").mkdir(parents=True)
            (project / ".codex").mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "base-model"',
                        "",
                        f"[projects.{json.dumps(str(project))}]",
                        'trust_level = "untrusted"',
                    ]
                ),
                encoding="utf-8",
            )
            project_config = project / ".codex" / "config.toml"
            project_config.write_text('model = "ignored-model"\n', encoding="utf-8")

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--cwd",
                str(project),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "model": report["effective"]["model"],
                    "project_trust": report["project"]["trust_level"],
                    "project_layer_applied": next(
                        layer["applied"]
                        for layer in report["layers"]
                        if layer["path"] == str(project_config.resolve())
                    ),
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "model": "base-model",
                    "project_trust": "untrusted",
                    "project_layer_applied": False,
                    "finding_codes": ["project.config_skipped_untrusted"],
                },
            )

    def test_project_provider_keys_are_ignored_even_when_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            project = root / "project"
            codex_home.mkdir()
            (project / ".git").mkdir(parents=True)
            (project / ".codex").mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "base-model"',
                        'model_provider = "user-provider"',
                        "",
                        "[model_providers.user-provider]",
                        'base_url = "https://api.example.invalid/v1"',
                        "",
                        f"[projects.{json.dumps(str(project))}]",
                        'trust_level = "trusted"',
                    ]
                ),
                encoding="utf-8",
            )
            project_config = project / ".codex" / "config.toml"
            project_config.write_text(
                "\n".join(
                    [
                        'model = "project-model"',
                        'model_provider = "ignored-provider"',
                        "",
                        "[model_providers.ignored-provider]",
                        'base_url = "https://ignored.example.invalid/v1"',
                    ]
                ),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--cwd",
                str(project),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            project_layer = next(
                layer
                for layer in report["layers"]
                if layer["path"] == str(project_config.resolve())
            )
            self.assertEqual(
                {
                    "model": report["effective"]["model"],
                    "provider": report["effective"]["model_provider"],
                    "ignored_keys": project_layer["ignored_keys"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "model": "project-model",
                    "provider": "user-provider",
                    "ignored_keys": ["model_provider", "model_providers"],
                    "finding_codes": ["project.config.ignored_keys"],
                },
            )

    def test_missing_catalog_returns_a_diagnostic_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        'model_catalog_json = "missing.json"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
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

            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "catalog_path": report["catalog"]["path"],
                    "catalog_exists": report["catalog"]["exists"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "catalog_path": str((codex_home / "missing.json").resolve()),
                    "catalog_exists": False,
                    "finding_codes": ["catalog.file_missing"],
                },
            )

    def test_catalog_directory_is_distinguished_from_a_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            catalog_path = codex_home / "catalog.json"
            catalog_path.mkdir()
            (codex_home / "config.toml").write_text(
                '\n'.join(['model = "active-model"', 'model_catalog_json = "catalog.json"']),
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

            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "exists": report["catalog"]["exists"],
                    "is_file": report["catalog"]["is_file"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "exists": True,
                    "is_file": False,
                    "finding_codes": ["catalog.not_regular_file"],
                },
            )

    def test_blank_model_display_name_is_reported_as_unclear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps({"models": [{"slug": "active-model", "display_name": "  "}]}),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                '\n'.join(['model = "active-model"', 'model_catalog_json = "catalog.json"']),
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
                    "display_name": report["catalog"]["selected_model"]["display_name"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "display_name": "  ",
                    "finding_codes": ["catalog.display_name_unclear"],
                },
            )

    def test_invalid_catalog_json_returns_a_diagnostic_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "broken.json").write_text('{"models": [', encoding="utf-8")
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        'model_catalog_json = "broken.json"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
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

            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "catalog_valid": report["catalog"]["valid"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "catalog_valid": False,
                    "finding_codes": ["catalog.invalid_json"],
                },
            )

    def test_catalog_without_active_model_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps({"models": [{"slug": "different-model"}]}),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "active-model"',
                        'model_provider = "thirdparty"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
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

            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                [finding["code"] for finding in report["findings"]],
                ["catalog.model_missing"],
            )

    def test_catalog_models_value_must_be_an_array(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps({"models": {"slug": "active-model"}}),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                '\n'.join(['model = "active-model"', 'model_catalog_json = "catalog.json"']),
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

            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                [finding["code"] for finding in report["findings"]],
                ["catalog.models_not_array"],
            )

    def test_active_model_slug_must_be_unique(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {"slug": "active-model", "supports_search_tool": True},
                            {"slug": "active-model", "supports_search_tool": False},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                '\n'.join(['model = "active-model"', 'model_catalog_json = "catalog.json"']),
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

            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "selected_model": report["catalog"]["selected_model"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "selected_model": None,
                    "finding_codes": ["catalog.model_duplicate"],
                },
            )


if __name__ == "__main__":
    unittest.main()
