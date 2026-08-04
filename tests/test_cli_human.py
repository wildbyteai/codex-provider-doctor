from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tests.test_cli_catalog import FIXTURES, run_doctor


class HumanReportTests(unittest.TestCase):
    def test_chinese_report_explains_provider_auth_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                        "requires_openai_auth = true",
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
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("结论：发现 2 个错误，0 个警告", result.stdout)
            self.assertIn("OpenAI 认证会忽略第三方环境变量", result.stdout)
            self.assertIn("如果该接口使用自己的 API Key", result.stdout)
            self.assertIn("auth.json 内容：未读取", result.stdout)

    def test_english_report_has_the_same_public_sections(self) -> None:
        codex_home = FIXTURES / "profile-home"
        result = run_doctor(
            "--codex-home",
            str(codex_home),
            "--profile",
            "work",
            "--system-config",
            str(FIXTURES / "missing-system.toml"),
            "--no-command-checks",
            "--lang",
            "en",
            extra_env={"DEEPSEEK_API_KEY": "test-only-placeholder"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Overall: OK", result.stdout)
        self.assertIn("Effective configuration", result.stdout)
        self.assertIn("Catalog path exists: true", result.stdout)
        self.assertIn("Catalog is a regular file: true", result.stdout)
        self.assertIn("Catalog JSON is valid: true", result.stdout)
        self.assertIn("Configuration layers", result.stdout)
        self.assertIn(str(codex_home / "work.config.toml"), result.stdout)
        self.assertIn("parse=not_found", result.stdout)
        self.assertIn("parse=ok", result.stdout)
        self.assertIn("Effective field sources", result.stdout)
        self.assertIn(
            f"model_providers.thirdparty.base_url: {codex_home / 'config.toml'}",
            result.stdout,
        )
        self.assertIn("Manual checks", result.stdout)
        self.assertIn("Plugin inventory count: not available", result.stdout)
        self.assertIn("auth.json contents: not read", result.stdout)

    def test_chinese_report_shows_compatibility_changes_without_editing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                """{
  "models": [
    {
      "slug": "deepseek-v4-flash",
      "display_name": "DeepSeek V4 Flash",
      "tool_mode": "code_mode_only",
      "supports_search_tool": true,
      "use_responses_lite": true
    }
  ]
}
""",
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

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--compat-rule",
                "deepseek-direct-tools-2026-08-03",
                "--no-command-checks",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("建议修改（不会自动写入）", result.stdout)
            self.assertIn("supports_search_tool：true → false", result.stdout)
            self.assertIn("不是所有第三方模型的默认值", result.stdout)


if __name__ == "__main__":
    unittest.main()
