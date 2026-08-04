from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_catalog import run_doctor


class ProviderAuthenticationTests(unittest.TestCase):
    def test_conflicting_provider_auth_is_an_error_without_leaking_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {"models": [{"slug": "deepseek-chat", "display_name": "DeepSeek Chat"}]}
                ),
                encoding="utf-8",
            )
            secret = "must-never-appear-in-report"
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "deepseek-chat"',
                        'model_provider = "deepseek"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.deepseek]",
                        'name = "DeepSeek"',
                        'base_url = "https://api.deepseek.com/v1"',
                        'wire_api = "responses"',
                        "requires_openai_auth = true",
                        'env_key = "DEEPSEEK_API_KEY"',
                        f'experimental_bearer_token = "{secret}"',
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
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertNotIn(secret, serialized)
            self.assertEqual(
                {
                    "provider": report["provider"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                    "errors": report["summary"]["errors"],
                },
                {
                    "provider": {
                        "id": "deepseek",
                        "exists": True,
                        "name": "DeepSeek",
                        "host": "api.deepseek.com",
                        "wire_api": "responses",
                        "requires_openai_auth": True,
                        "env_key": "DEEPSEEK_API_KEY",
                        "env_key_is_set": False,
                        "auth_command_configured": False,
                        "direct_bearer_token_configured": True,
                    },
                    "finding_codes": [
                        "provider.auth.openai_with_env_key",
                        "provider.auth.multiple_methods",
                        "provider.auth.openai_with_direct_token",
                        "provider.auth.direct_token",
                    ],
                    "errors": 2,
                },
            )

    def test_missing_provider_environment_variable_is_a_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            env_key = "CODEX_PROVIDER_DOCTOR_TEST_KEY_THAT_IS_NOT_SET"
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                        f'env_key = "{env_key}"',
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
                    "env_key": report["provider"]["env_key"],
                    "env_key_is_set": report["provider"]["env_key_is_set"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "env_key": env_key,
                    "env_key_is_set": False,
                    "finding_codes": ["provider.auth.env_missing"],
                },
            )

    def test_top_level_requires_openai_auth_is_reported_as_misplaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        "requires_openai_auth = true",
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                        'env_key = "THIRD_PARTY_API_KEY"',
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
                extra_env={"THIRD_PARTY_API_KEY": "test-only-placeholder"},
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "effective_provider_value": report["provider"]["requires_openai_auth"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "effective_provider_value": False,
                    "finding_codes": ["provider.auth.requires_openai_auth_misplaced"],
                },
            )

    def test_openai_auth_with_direct_token_is_version_sensitive_but_not_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            secret = "version-sensitive-token-must-not-leak"
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                        "requires_openai_auth = true",
                        f'experimental_bearer_token = "{secret}"',
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
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertNotIn(secret, serialized)
            self.assertEqual(
                {
                    "errors": report["summary"]["errors"],
                    "warnings": report["summary"]["warnings"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "errors": 0,
                    "warnings": 2,
                    "finding_codes": [
                        "provider.auth.openai_with_direct_token",
                        "provider.auth.direct_token",
                    ],
                },
            )


if __name__ == "__main__":
    unittest.main()
