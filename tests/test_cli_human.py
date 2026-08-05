from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_catalog import FIXTURES, run_doctor
from tests.test_cli_runtime import install_fake_codex


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
        self.assertIn("Catalog model count: 1", result.stdout)
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
        self.assertIn("Plugin inventory status: unverified", result.stdout)
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
      "use_responses_lite": false
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
            self.assertIn("模型目录条目数：1", result.stdout)
            self.assertIn(
                "tool_mode：code_mode_only（案例值 direct；仅在直接工具出现症状时核对）",
                result.stdout,
            )
            self.assertIn("supports_search_tool：true → false（建议修改）", result.stdout)
            self.assertIn("use_responses_lite：false（与案例一致）", result.stdout)
            self.assertNotIn("tool_mode：code_mode_only → direct（建议修改）", result.stdout)
            self.assertIn("不是所有第三方模型的默认值", result.stdout)

    def test_chinese_report_explicitly_keeps_official_model_outside_deepseek_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                """{
  "models": [
    {
      "slug": "gpt-5.6-sol",
      "display_name": "GPT-5.6-Sol",
      "tool_mode": "code_mode_only",
      "supports_search_tool": true,
      "use_responses_lite": false
    }
  ]
}
""",
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "gpt-5.6-sol"',
                        'model_provider = "custom"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
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

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("适用性：不适用于当前选中的模型或 Provider", result.stdout)
            self.assertIn("官方模型可以保持自身的 supports_search_tool 值", result.stdout)
            self.assertNotIn("supports_search_tool：true → false", result.stdout)

    def test_human_report_prioritizes_selected_compatibility_mismatch_over_intent_and_cli_probe_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            bin_directory = root / "bin"
            codex_home.mkdir()
            bin_directory.mkdir()
            secret = "human-report-token-must-not-leak"
            (codex_home / "catalog.json").write_text(
                """{
  "models": [
    {
      "slug": "deepseek-v4-flash",
      "display_name": "DeepSeek V4 Flash",
      "tool_mode": "code_mode_only",
      "supports_search_tool": true,
      "use_responses_lite": false
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
                        'model_provider = "thirdparty"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
                        "requires_openai_auth = true",
                        f'experimental_bearer_token = "{secret}"',
                    ]
                ),
                encoding="utf-8",
            )
            install_fake_codex(bin_directory, plugin_marketplace_failure=True)

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--compat-rule",
                "deepseek-direct-tools-2026-08-03",
                "--acknowledge",
                "provider.auth.openai_with_direct_token",
                extra_env={
                    "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn(secret, result.stdout)
            self.assertIn("首要诊断：第三方 Responses 模型与所选兼容案例存在需处理的字段差异", result.stdout)
            compatibility_index = result.stdout.index("第三方 Responses 模型与所选兼容案例存在需处理的字段差异")
            security_index = result.stdout.index("配置文件中存在直接 Bearer Token")
            intent_index = result.stdout.index("认证组合已确认为有意")
            plugin_index = result.stdout.index("CLI 插件探针未能核验实际状态")
            self.assertLess(compatibility_index, security_index)
            self.assertLess(security_index, intent_index)
            self.assertLess(intent_index, plugin_index)
            self.assertIn("【已确认意图】认证组合已确认为有意", result.stdout)
            self.assertIn("【未核验】CLI 插件探针未能核验实际状态", result.stdout)


if __name__ == "__main__":
    unittest.main()
