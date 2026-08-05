from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tests.test_cli_catalog import run_doctor
from tests.test_cli_runtime import install_fake_codex


class UserProblemGuideTests(unittest.TestCase):
    def test_json_exposes_the_same_six_health_check_fields_as_the_human_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
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
                "--no-command-checks",
                "--json",
            )

            self.assertIn(result.returncode, (0, 1), result.stderr)
            report = json.loads(result.stdout)
            cards = report["solutions"]["health_checks"]
            self.assertEqual(
                [card["id"] for card in cards],
                [
                    "keep-official-login",
                    "plugins-or-skills-unavailable",
                    "model-name-incorrect",
                    "history-missing",
                    "chrome-unavailable",
                ],
            )
            for card in cards:
                self.assertEqual(
                    set(card),
                    {
                        "id",
                        "title",
                        "status",
                        "status_label",
                        "current_result",
                        "exact_targets",
                        "controlled_by",
                        "desired_state",
                        "how_to_change",
                        "how_to_verify",
                    },
                )
                self.assertTrue(card["current_result"])
                self.assertTrue(card["exact_targets"])
                for target in card["exact_targets"]:
                    self.assertEqual(
                        set(target),
                        {"location", "parameter", "current_value"},
                    )
                    self.assertTrue(target["location"])
                    self.assertTrue(target["parameter"])
                    self.assertTrue(target["current_value"])
                self.assertTrue(card["controlled_by"])
                self.assertTrue(card["desired_state"])
                self.assertTrue(card["how_to_change"])
                self.assertTrue(card["how_to_verify"])

            human_result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
            )
            self.assertEqual(human_result.returncode, result.returncode, human_result.stderr)
            for card in cards:
                self.assertIn(
                    f"{card['title']}【{card['status_label']}】",
                    human_result.stdout,
                )
                self.assertIn(
                    f"当前结果：{card['current_result']}",
                    human_result.stdout,
                )
                for target in card["exact_targets"]:
                    self.assertIn(
                        (
                            f"- {target['location']} → {target['parameter']}："
                            f"{target['current_value']}"
                        ),
                        human_result.stdout,
                    )
                for control in card["controlled_by"]:
                    self.assertIn(f"- {control}", human_result.stdout)
                self.assertIn(
                    f"目标状态：{card['desired_state']}",
                    human_result.stdout,
                )
                for action in card["how_to_change"]:
                    self.assertIn(action, human_result.stdout)
                self.assertIn(
                    f"怎么确认：{card['how_to_verify']}",
                    human_result.stdout,
                )

    def test_json_health_checks_do_not_repeat_secrets_private_urls_or_user_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="private-user-path-") as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            secret = "health-check-token-must-never-appear"
            private_path = "private/account/route"
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        f'base_url = "https://api.example.invalid/{private_path}"',
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
                "--problem",
                "keep-official-login",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            health_checks = json.dumps(
                report["solutions"]["health_checks"],
                ensure_ascii=False,
            )
            self.assertNotIn(secret, health_checks)
            self.assertNotIn(private_path, health_checks)
            self.assertNotIn(str(root), health_checks)

    def test_health_checks_name_concrete_files_parameters_and_safe_current_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="doctor-exact-targets-") as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            project = root / "project"
            codex_home.mkdir()
            (codex_home / "skills" / "installed-skill").mkdir(parents=True)
            (codex_home / "skills" / "installed-skill" / "SKILL.md").write_text(
                "# test-only skill\n",
                encoding="utf-8",
            )
            (project / ".git").mkdir(parents=True)
            (project / ".agents" / "skills" / "project-skill").mkdir(parents=True)
            (project / ".agents" / "skills" / "project-skill" / "SKILL.md").write_text(
                "# test-only project skill\n",
                encoding="utf-8",
            )
            secret = "exact-target-token-must-never-appear"
            auth_secret = "auth-json-secret-must-never-appear"
            (codex_home / "auth.json").write_text(
                json.dumps({"token": auth_secret}),
                encoding="utf-8",
            )
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
                                "supports_search_tool": False,
                                "tool_mode": "direct",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "vendor-model-v1"',
                        'model_provider = "custom"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[features]",
                        "apps = true",
                        "remote_plugin = false",
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/private-route"',
                        'wire_api = "responses"',
                        "requires_openai_auth = true",
                        f'experimental_bearer_token = "{secret}"',
                        "",
                        f"[projects.{json.dumps(str(project))}]",
                        'trust_level = "trusted"',
                    ]
                ),
                encoding="utf-8",
            )
            with sqlite3.connect(codex_home / "history.sqlite") as connection:
                connection.execute(
                    """
                    CREATE TABLE threads (
                        id TEXT PRIMARY KEY,
                        model_provider TEXT NOT NULL,
                        archived INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                connection.executemany(
                    "INSERT INTO threads (id, model_provider, archived) VALUES (?, ?, ?)",
                    [
                        ("current-thread", "custom", 0),
                        ("old-thread-1", "openai", 0),
                        ("old-thread-2", "openai", 0),
                    ],
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
            cards = {
                card["id"]: card
                for card in report["solutions"]["health_checks"]
            }

            def target_map(problem_id: str) -> dict[tuple[str, str], str]:
                return {
                    (target["location"], target["parameter"]): target["current_value"]
                    for target in cards[problem_id]["exact_targets"]
                }

            login = target_map("keep-official-login")
            self.assertEqual(
                login[("$CODEX_HOME/config.toml", "[model_providers.custom].requires_openai_auth")],
                "true",
            )
            self.assertEqual(
                login[("$CODEX_HOME/config.toml", "[model_providers.custom].experimental_bearer_token")],
                "已配置（值未读取）",
            )
            self.assertEqual(
                login[("$CODEX_HOME/auth.json", "官方登录缓存")],
                "文件存在；内容未读取",
            )

            plugins = target_map("plugins-or-skills-unavailable")
            self.assertEqual(plugins[("$CODEX_HOME/skills", "已安装 Skill")], "1 个")
            self.assertEqual(plugins[("$PROJECT_ROOT/.agents/skills", "项目 Skill")], "1 个；项目已受信任")
            self.assertEqual(plugins[("$CODEX_HOME/config.toml", "features.apps")], "true")
            self.assertEqual(plugins[("$CODEX_HOME/config.toml", "features.remote_plugin")], "false")
            self.assertEqual(
                plugins[("New task → tool list", "目标 Skill / 插件工具是否出现")],
                "运行时未核验",
            )
            self.assertEqual(
                plugins[("New task → minimal live invocation", "目标 Skill / 插件真实调用")],
                "未执行；需逐项验证",
            )

            model = target_map("model-name-incorrect")
            self.assertEqual(model[("$CODEX_HOME/config.toml", "model")], "vendor-model-v1")
            self.assertEqual(model[("$CODEX_HOME/catalog.json", "models[].slug")], "vendor-model-v1（唯一匹配）")
            self.assertEqual(model[("$CODEX_HOME/catalog.json", "models[].display_name")], "Vendor Model V1")

            history = target_map("history-missing")
            self.assertEqual(history[("$CODEX_HOME/history.sqlite", "threads.model_provider")], "openai：2 个未归档；当前 Provider：custom")
            self.assertEqual(
                history[("$CODEX_HOME/history.sqlite", "threads.model_provider = custom")],
                "总数 1；未归档 1；已归档 0（当前 Provider）",
            )
            self.assertEqual(
                history[("$CODEX_HOME/history.sqlite", "threads.model_provider = openai")],
                "总数 2；未归档 2；已归档 0",
            )
            self.assertEqual(history[("$CODEX_HOME/history.sqlite", "数据库访问方式")], "只读；未读取任务正文")

            chrome = target_map("chrome-unavailable")
            self.assertEqual(chrome[("$CODEX_HOME/catalog.json", "models[].supports_search_tool")], "false（兼容性线索，不是唯一根因）")
            self.assertEqual(chrome[("$CODEX_HOME/catalog.json", "models[].tool_mode")], "direct")
            self.assertEqual(chrome[("$CODEX_HOME/config.toml", "features.apps")], "true")
            self.assertEqual(chrome[("$CODEX_HOME/config.toml", "features.remote_plugin")], "false")

            serialized_cards = json.dumps(cards, ensure_ascii=False)
            self.assertNotIn(secret, serialized_cards)
            self.assertNotIn(auth_secret, serialized_cards)
            self.assertNotIn("private-route", serialized_cards)
            self.assertNotIn(str(root), serialized_cards)

    def test_chrome_health_check_shows_true_and_false_without_claiming_a_unique_root_cause(self) -> None:
        for supports_search_tool in (False, True):
            with self.subTest(supports_search_tool=supports_search_tool):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    root = Path(temporary_directory)
                    codex_home = root / "codex-home"
                    codex_home.mkdir()
                    (codex_home / "catalog.json").write_text(
                        json.dumps(
                            {
                                "models": [
                                    {
                                        "slug": "vendor-model-v1",
                                        "display_name": "Vendor Model V1",
                                        "supports_search_tool": supports_search_tool,
                                    }
                                ]
                            }
                        ),
                        encoding="utf-8",
                    )
                    (codex_home / "config.toml").write_text(
                        "\n".join(
                            [
                                'model = "vendor-model-v1"',
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
                        "--no-command-checks",
                        "--problem",
                        "chrome-unavailable",
                        "--json",
                    )

                    self.assertEqual(result.returncode, 0, result.stderr)
                    report = json.loads(result.stdout)
                    card = report["solutions"]["health_checks"][0]
                    value = "true" if supports_search_tool else "false"
                    self.assertIn(
                        f"supports_search_tool = {value}",
                        card["current_result"],
                    )
                    support_target = next(
                        target
                        for target in card["exact_targets"]
                        if target["parameter"] == "models[].supports_search_tool"
                    )
                    self.assertEqual(
                        support_target["current_value"],
                        f"{value}（兼容性线索，不是唯一根因）",
                    )
                    self.assertNotIn("唯一根因是", card["current_result"])

    def test_provider_fields_keep_their_individual_effective_config_origins(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            secret = "split-origin-token-must-never-appear"
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "vendor-model-v1"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                        "requires_openai_auth = true",
                    ]
                ),
                encoding="utf-8",
            )
            (codex_home / "work.config.toml").write_text(
                "\n".join(
                    [
                        "[model_providers.custom]",
                        f'experimental_bearer_token = "{secret}"',
                    ]
                ),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--profile",
                "work",
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--problem",
                "keep-official-login",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn(secret, result.stdout)
            card = json.loads(result.stdout)["solutions"]["health_checks"][0]
            targets = {
                target["parameter"]: target["location"]
                for target in card["exact_targets"]
            }
            self.assertEqual(
                targets["[model_providers.custom].requires_openai_auth"],
                "$CODEX_HOME/config.toml",
            )
            self.assertEqual(
                targets["[model_providers.custom].experimental_bearer_token"],
                "$CODEX_HOME/work.config.toml",
            )

    def test_builtin_provider_cards_do_not_invent_custom_provider_or_catalog_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                'model = "gpt-example"\n',
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--problem",
                "model-name-incorrect",
                "--problem",
                "chrome-unavailable",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            cards = json.loads(result.stdout)["solutions"]["health_checks"]
            serialized = json.dumps(cards, ensure_ascii=False)
            self.assertNotIn("[model_providers.openai]", serialized)
            self.assertNotIn("$CODEX_HOME/config.toml → models[]", serialized)
            model_card, chrome_card = cards
            self.assertNotIn(
                "models[].slug",
                {target["parameter"] for target in model_card["exact_targets"]},
            )
            self.assertEqual(model_card["status"], "runtime_verification_required")
            self.assertIn("无须配置自定义模型目录", model_card["current_result"])
            self.assertNotIn("修改模型目录", json.dumps(model_card["how_to_change"], ensure_ascii=False))
            self.assertIn(
                {
                    "location": "$CODEX_HOME/config.toml",
                    "parameter": "model_provider",
                    "current_value": "openai（内置 Provider）",
                },
                chrome_card["exact_targets"],
            )

    def test_default_report_does_not_acknowledge_dual_auth_intent_without_user_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                        "requires_openai_auth = true",
                        'experimental_bearer_token = "test-only-placeholder"',
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
            solution = report["solutions"]["items"][0]
            self.assertEqual(
                {
                    "status": solution["status"],
                    "diagnosis": solution["diagnosis"],
                    "provider_intent_status": report["provider"]["authentication_intent"]["status"],
                    "acknowledged": report["summary"]["acknowledged"],
                },
                {
                    "status": "configured_intent_unverified_with_security_warning",
                    "diagnosis": "检测到双认证字段组合，但本次尚未确认这是用户有意设计；官方登录状态仍需单独核验，Token 明文风险也继续独立告警。",
                    "provider_intent_status": "unverified",
                    "acknowledged": 0,
                },
            )

    def test_keep_official_login_problem_recognizes_confirmed_dual_auth_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            secret = "dual-auth-token-must-never-appear"
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
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
                "--problem",
                "keep-official-login",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn(secret, result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(report["solutions"]["requested"], ["keep-official-login"])
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "keep-official-login",
                    "title": "保留官方登录态",
                    "status": "configured_login_unverified_with_security_warning",
                    "diagnosis": "双认证配置已就位：requires_openai_auth 保留官方账户状态，显式 Bearer Token 用于第三方请求；本次未运行官方登录状态探针。",
                    "config_path": "model_providers.custom.requires_openai_auth",
                    "required_value": True,
                    "official_login": {
                        "probe": "skipped",
                        "method": None,
                        "status": "unverified",
                    },
                    "actions": [
                        "保持 [model_providers.custom] 下的 requires_openai_auth = true。",
                        "在同一 Provider 块保留 experimental_bearer_token；它用于第三方请求，值不会进入报告。",
                        "单独确认 codex login status 显示 ChatGPT 登录；不要退出或覆盖官方登录状态。",
                        "Token 明文存储仍是独立安全风险；迁移凭据前不要破坏当前可用组合。",
                    ],
                },
            )
            self.assertEqual(
                report["provider"]["authentication_intent"],
                {
                    "combination": "official_login_retained_with_explicit_provider_token",
                    "status": "acknowledged",
                    "intentional": True,
                    "acknowledgement_code": "provider.auth.openai_with_direct_token",
                    "official_login_state": "retained_by_requires_openai_auth",
                    "provider_request_authentication": "explicit_bearer_token_precedes_official_auth",
                    "requires_openai_auth_config_path": "model_providers.custom.requires_openai_auth",
                    "plaintext_token_risk": "independent_warning",
                },
            )
            self.assertEqual(report["summary"]["unverified"], 0)
            self.assertEqual(report["summary"]["acknowledged"], 1)

    def test_keep_official_login_problem_reports_chatgpt_login_separately_from_provider_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            bin_directory = root / "bin"
            codex_home.mkdir()
            bin_directory.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
                        "requires_openai_auth = true",
                        'experimental_bearer_token = "test-only-placeholder"',
                    ]
                ),
                encoding="utf-8",
            )
            install_fake_codex(bin_directory, login_status="Logged in using ChatGPT")

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--problem",
                "keep-official-login",
                "--json",
                extra_env={
                    "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            solution = report["solutions"]["items"][0]
            self.assertEqual(
                {
                    "status": solution["status"],
                    "diagnosis": solution["diagnosis"],
                    "official_login": solution["official_login"],
                    "plaintext_warning_present": "provider.auth.direct_token"
                    in [finding["code"] for finding in report["findings"]],
                },
                {
                    "status": "configured_with_security_warning",
                    "diagnosis": "双认证配置已就位，且已确认官方 ChatGPT 登录；显式 Bearer Token 用于第三方请求。",
                    "official_login": {
                        "probe": "ok",
                        "method": "chatgpt",
                        "status": "confirmed",
                    },
                    "plaintext_warning_present": True,
                },
            )

    def test_keep_official_login_problem_does_not_apply_third_party_pattern_to_builtin_openai(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                'model = "gpt-example"\n',
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--problem",
                "keep-official-login",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "keep-official-login",
                    "title": "保留官方登录态",
                    "status": "not_applicable_builtin_provider",
                    "diagnosis": "当前使用内置 OpenAI Provider，不需要也不应为它新增第三方 Provider 的双认证字段。",
                    "config_path": None,
                    "required_value": None,
                    "official_login": {
                        "probe": "skipped",
                        "method": None,
                        "status": "unverified",
                    },
                    "actions": [
                        "保持官方 ChatGPT/Codex 登录，并单独确认 codex login status。",
                        "只有切换到自定义第三方 Provider 后，才在该 Provider 自己的配置块使用双认证模式。",
                        "不要在内置 OpenAI Provider 上添加 experimental_bearer_token。",
                    ],
                },
            )
            card = report["solutions"]["health_checks"][0]
            self.assertNotIn(
                "[model_providers.openai]",
                json.dumps(card, ensure_ascii=False),
            )
            self.assertIn(
                {
                    "location": "$CODEX_HOME/config.toml",
                    "parameter": "model_provider",
                    "current_value": "openai（内置 Provider）",
                },
                card["exact_targets"],
            )

    def test_keep_official_login_problem_requires_auth_method_transition_instead_of_stacking_on_env_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
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
                "--problem",
                "keep-official-login",
                "--json",
                extra_env={"THIRD_PARTY_API_KEY": "test-only-placeholder"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            solution = report["solutions"]["items"][0]
            self.assertEqual(
                {
                    "status": solution["status"],
                    "conflicting_auth_fields": solution["conflicting_auth_fields"],
                    "actions": solution["actions"],
                },
                {
                    "status": "needs_auth_method_transition",
                    "conflicting_auth_fields": ["env_key"],
                    "actions": [
                        "不要把 requires_openai_auth 或 experimental_bearer_token 直接叠加到现有 env_key/auth 上。",
                        "先备份配置并展示字段 diff；如果确认改用直接 Token，在同一次受控修改中移除 env_key/auth，再在 [model_providers.custom] 下设置 requires_openai_auth = true 和 experimental_bearer_token。",
                        "修改后完全重启 Codex，分别验证官方登录、第三方模型请求和插件；Token 明文风险继续独立处理。",
                    ],
                },
            )

    def test_keep_official_login_problem_does_not_accept_dual_auth_stacked_on_env_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                        'env_key = "THIRD_PARTY_API_KEY"',
                        "requires_openai_auth = true",
                        'experimental_bearer_token = "test-only-placeholder"',
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
                "--problem",
                "keep-official-login",
                "--json",
                extra_env={"THIRD_PARTY_API_KEY": "test-only-placeholder"},
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            solution = report["solutions"]["items"][0]
            self.assertEqual(solution["status"], "needs_auth_method_transition")
            self.assertEqual(solution["conflicting_auth_fields"], ["env_key"])
            self.assertIn(
                "provider.auth.multiple_methods",
                [finding["code"] for finding in report["findings"]],
            )

    def test_model_name_problem_points_to_the_effective_slug_and_display_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "  ",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
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
                "--problem",
                "model-name-incorrect",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "model-name-incorrect",
                    "title": "修正模型名称",
                    "status": "needs_catalog_change",
                    "diagnosis": "活动模型已匹配 slug，但 display_name 为空，所以界面可能只显示 slug。",
                    "catalog_path": str((codex_home / "catalog.json").resolve()),
                    "model_slug": "vendor-model-v1",
                    "actions": [
                        "保持顶层 model = \"vendor-model-v1\" 与 models[].slug 完全一致。",
                        "在实际生效的模型目录条目中填写非空 display_name。",
                        "完全重启 Codex 并新建任务，旧任务可能继续显示旧名称。",
                    ],
                },
            )

    def test_model_name_problem_does_not_ask_for_a_display_name_change_when_it_is_already_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
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
                "--problem",
                "model-name-incorrect",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            solution = report["solutions"]["items"][0]
            self.assertEqual(solution["status"], "configured")
            self.assertEqual(
                solution["diagnosis"],
                "静态模型目录条目会显示为“Vendor Model V1”，当前没有需要修改的 slug 或 display_name。",
            )
            self.assertEqual(
                solution["actions"],
                [
                    "无需修改 display_name；先确认界面加载的是上述模型目录和 slug。",
                    "Windows Desktop 提醒：如果 App Server 的 model/list 已返回该 slug，但下拉框仍遗漏它或只显示 Custom / 错误元数据，应优先参考截至 2026-08-05 的同类缺陷 openai/codex#19694 和 #36582。doctor 无法自动观察界面或远程 available_models 响应，因此不会自动确认为根因；对外表述“仍未解决”前要复核当前 Issue 状态。",
                    '安全绕过：直接切换 config.toml 中的 model 和 model_provider；仅在当前 Provider 已正确时使用 codex -m "vendor-model-v1"，或建立不同 Profile。用真实请求确认路由，界面名称不能作为判据。不要自动修改 app.asar；实验补丁必须先备份并另行明确确认。',
                ],
            )
            self.assertEqual(
                solution["manual_reminders"],
                [
                    {
                        "code": "windows_desktop.model_picker_filtering",
                        "status": "manual",
                        "automatic_detection": False,
                        "condition": "App Server 的 model/list 已返回活动 slug，但 Windows Desktop 仍遗漏它或只显示 Custom / 错误元数据。",
                        "references": {
                            "as_of": "2026-08-05",
                            "issues": ["openai/codex#19694", "openai/codex#36582"],
                        },
                    }
                ],
            )

    def test_history_problem_gives_no_write_recovery_before_database_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                    ]
                ),
                encoding="utf-8",
            )
            with sqlite3.connect(codex_home / "history.sqlite") as connection:
                connection.execute(
                    """
                    CREATE TABLE threads (
                        id TEXT PRIMARY KEY,
                        model_provider TEXT NOT NULL,
                        archived INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                connection.executemany(
                    "INSERT INTO threads (id, model_provider, archived) VALUES (?, ?, ?)",
                    [(f"old-{index}", "openai", 0) for index in range(9)],
                )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--problem",
                "history-missing",
                "--confirm-cause",
                "history.provider_mismatch",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "history-missing",
                    "title": "恢复历史任务",
                    "status": "confirmed_root_cause",
                    "diagnosis": "已确认：9 个未归档任务仍绑定 openai，而当前 Provider 是 custom，因此它们在当前列表不可见。",
                    "affected_unarchived_threads": 9,
                    "affected_provider_counts": [
                        {"provider": "openai", "threads_unarchived": 9}
                    ],
                    "actions": [
                        "立即无写入恢复：切回 openai，或在支持的版本中使用全部 Provider 视图查看这些任务。",
                        "优先升级 Codex 并重新检查任务列表；不要先改数据库。",
                        "只有确需迁移绑定时，先退出 Codex，完整备份数据库及 WAL/SHM，展示精确行数和字段 diff，并再次取得明确确认。",
                    ],
                },
            )

    def test_history_problem_does_not_claim_no_mismatch_when_database_was_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
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
                "--no-command-checks",
                "--problem",
                "history-missing",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "history-missing",
                    "title": "恢复历史任务",
                    "status": "history_not_checked",
                    "diagnosis": "未找到包含 threads.model_provider 的兼容任务数据库，因此还不能判断是否存在 Provider 绑定差异。",
                    "affected_unarchived_threads": None,
                    "affected_provider_counts": [],
                    "actions": [
                        "先确认本次诊断使用了正确的 CODEX_HOME 和 Profile。",
                        "升级 Codex，并检查是否提供全部 Provider 的任务列表。",
                        "在找到准确数据库前保持只读，不要猜测文件名或迁移记录。",
                    ],
                },
            )

    def test_history_problem_reports_each_old_provider_instead_of_assigning_the_total_to_one(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                    ]
                ),
                encoding="utf-8",
            )
            with sqlite3.connect(codex_home / "history.sqlite") as connection:
                connection.execute(
                    """
                    CREATE TABLE threads (
                        id TEXT PRIMARY KEY,
                        model_provider TEXT NOT NULL,
                        archived INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                connection.executemany(
                    "INSERT INTO threads (id, model_provider, archived) VALUES (?, ?, ?)",
                    [
                        *[(f"openai-{index}", "openai", 0) for index in range(5)],
                        *[(f"legacy-{index}", "legacy", 0) for index in range(4)],
                    ],
                )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--problem",
                "history-missing",
                "--confirm-cause",
                "history.provider_mismatch",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            solution = report["solutions"]["items"][0]
            self.assertEqual(
                {
                    "diagnosis": solution["diagnosis"],
                    "affected_provider_counts": solution["affected_provider_counts"],
                    "first_action": solution["actions"][0],
                },
                {
                    "diagnosis": "已确认：9 个未归档任务绑定其他 Provider（openai 5，legacy 4），当前 Provider 是 custom，因此它们在当前列表不可见。",
                    "affected_provider_counts": [
                        {"provider": "openai", "threads_unarchived": 5},
                        {"provider": "legacy", "threads_unarchived": 4},
                    ],
                    "first_action": "立即无写入恢复：分别切回 openai、legacy，或在支持的版本中使用全部 Provider 视图查看这些任务。",
                },
            )

    def test_plugins_and_skills_problem_distinguishes_installation_from_runtime_exposure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            project = root / "project"
            user_skill = codex_home / "skills" / "private-skill-name-must-not-leak"
            project_skill = project / ".agents" / "skills" / "project-private-skill"
            codex_home.mkdir()
            user_skill.mkdir(parents=True)
            project_skill.mkdir(parents=True)
            (project / ".git").mkdir()
            (user_skill / "SKILL.md").write_text("---\nname: private\n---\n", encoding="utf-8")
            (project_skill / "SKILL.md").write_text(
                "---\nname: project-private\n---\n",
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                        "",
                        f'[projects."{project}"]',
                        'trust_level = "untrusted"',
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
                "--problem",
                "plugins-or-skills-unavailable",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("private-skill-name-must-not-leak", result.stdout)
            self.assertNotIn("project-private-skill", result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["skills"],
                {
                    "probe": "ok",
                    "coverage": "partial",
                    "total": 1,
                    "sources": [
                        {
                            "scope": "user",
                            "path": "$CODEX_HOME/skills",
                            "exists": True,
                            "count": 1,
                            "status": "ok",
                        },
                        {
                            "scope": "project",
                            "path": "$PROJECT_ROOT/.agents/skills",
                            "exists": True,
                            "count": None,
                            "status": "skipped_untrusted",
                            "trust_level": "untrusted",
                        },
                    ],
                },
            )
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "plugins-or-skills-unavailable",
                    "title": "恢复插件与 Skill",
                    "status": "installation_present_runtime_unverified",
                    "diagnosis": "检测到至少 1 个本地 Skill；未受信任项目的 Skill 未计入，插件运行状态也尚未核验。切换 Provider 没有删除已确认的安装。",
                    "skills_coverage": "partial",
                    "actions": [
                        "完全重启 Codex 并新建任务；旧任务可能保留旧 Skill 和工具列表。",
                        "在 Plugins/Settings 确认官方插件仍启用，并确认连接器或 MCP 已授权。",
                        "单独审查项目可信度后再判断项目 Skill 是否应加载；不要只为消除提示而信任项目。",
                        "如果已确认的 Skill 能加载但插件工具没有出现，检查活动模型目录和第三方 Responses 工具兼容性，不要先重装插件。",
                    ],
                },
            )

    def test_plugins_problem_leads_with_disabled_integration_features(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
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
                "--problem",
                "plugins-or-skills-unavailable",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "plugins-or-skills-unavailable",
                    "title": "恢复插件与 Skill",
                    "status": "plugin_features_disabled",
                    "diagnosis": "插件集成功能被配置关闭：features.apps = false、features.remote_plugin = false。切换 Provider 没有删除 Skill 安装，但官方插件和连接器可能无法加载。",
                    "disabled_features": ["apps", "remote_plugin"],
                    "actions": [
                        "在用户级配置恢复所需 feature，完全重启 Codex 并新建任务。",
                        "再在 Plugins/Settings 确认官方插件启用，并完成连接器或 MCP 授权。",
                        "不要因为 CLI 清单失败而重装插件；先验证新任务是否实际出现目标工具。",
                    ],
                },
            )

    def test_chrome_problem_treats_false_as_direct_tool_exposure_not_a_fault(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
                                "tool_mode": "code_mode_only",
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
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
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
                "--no-command-checks",
                "--problem",
                "chrome-unavailable",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["compatibility"]["symptom_assessments"][0]["assessment"],
                "direct_namespace_branch_forced",
            )
            self.assertNotIn(
                "compat.chrome.supports_search_tool_false",
                [finding["code"] for finding in report["findings"]],
            )
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "chrome-unavailable",
                    "title": "恢复 Chrome 调用",
                    "status": "direct_namespace_branch_runtime_unverified",
                    "diagnosis": "按 2026-08-05 官方 Codex 源码，活动模型 supports_search_tool = false 会让 namespace 工具规划分支进入 Direct；这不能证明 Chrome 自身声明为 Direct 或已进入真实任务工具列表，因此该值本身不是故障证据。",
                    "observed": {
                        "supports_search_tool": False,
                        "tool_mode": "code_mode_only",
                        "use_responses_lite": False,
                    },
                    "evidence_scope": {
                        "source": "official_codex_source",
                        "as_of": "2026-08-05",
                        "detected_codex_version": None,
                        "namespace_tools_feature_state": "not_checked",
                        "actual_tool_exposure": "runtime_unverified",
                        "runtime_verification_required": True,
                    },
                    "actions": [
                        "完全重启 Codex 并新建任务，确认新任务是否实际出现 Chrome 工具。",
                        "工具未出现时，检查 Plugins/Settings、官方登录、Chrome Profile 和连接器授权，不要因为 CLI 清单失败而重装。",
                        "工具已经出现但调用失败时，再检查 Chrome 扩展桥接、站点阻止规则和真实调用错误。",
                    ],
                },
            )

    def test_chrome_problem_prioritizes_disabled_app_integration_over_tool_exposure_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
                                "supports_search_tool": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
                        "",
                        "[features]",
                        "apps = false",
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
                "--problem",
                "chrome-unavailable",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            solution = report["solutions"]["items"][0]
            self.assertEqual(
                {
                    "status": solution["status"],
                    "diagnosis": solution["diagnosis"],
                    "first_action": solution["actions"][0],
                    "supports_search_tool": solution["observed"]["supports_search_tool"],
                },
                {
                    "status": "plugin_features_disabled",
                    "diagnosis": "features.apps = false 已关闭 App/连接器集成，这是 Chrome 能力缺失的更直接静态证据；supports_search_tool = false 仍是独立字段，不能单独确定真实工具列表。",
                    "first_action": "先在用户级配置恢复 features.apps，完全重启 Codex 并新建任务。",
                    "supports_search_tool": False,
                },
            )

    def test_chrome_problem_does_not_treat_remote_plugin_directory_as_proof_of_chrome_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
                                "supports_search_tool": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
                        "",
                        "[features]",
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
                "--problem",
                "chrome-unavailable",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            solution = report["solutions"]["items"][0]
            self.assertEqual(
                {
                    "status": solution["status"],
                    "diagnosis": solution["diagnosis"],
                    "disabled_features": solution["disabled_features"],
                },
                {
                    "status": "remote_plugin_directory_disabled_runtime_unverified",
                    "diagnosis": "features.remote_plugin = false 可能使远程 Plugins Directory 无法加载，但不能证明已经安装的 Chrome 工具因此不可用；模型目录和真实工具列表仍需分开核验。",
                    "disabled_features": ["remote_plugin"],
                },
            )

    def test_chrome_problem_keeps_true_exposure_mode_runtime_dependent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
                                "tool_mode": None,
                                "supports_search_tool": True,
                                "use_responses_lite": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
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
                "--no-command-checks",
                "--problem",
                "chrome-unavailable",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            assessment = report["compatibility"]["symptom_assessments"][0]
            self.assertEqual(
                {
                    "assessment": assessment["assessment"],
                    "next_step": assessment["next_step"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "assessment": "exposure_mode_runtime_dependent",
                    "next_step": "verify_namespace_tools_and_live_invocation",
                    "finding_codes": ["compat.chrome.exposure_mode_unverified"],
                },
            )
            self.assertEqual(
                report["solutions"]["items"][0],
                {
                    "id": "chrome-unavailable",
                    "title": "恢复 Chrome 调用",
                    "status": "exposure_mode_runtime_unverified",
                    "diagnosis": "按 2026-08-05 官方 Codex 源码，supports_search_tool = true 只有在 namespace tools 同时启用时才允许 Deferred；否则仍可能走 Direct。单靠这个字段不能确定 Chrome 暴露路径或故障根因。",
                    "observed": {
                        "supports_search_tool": True,
                        "tool_mode": None,
                        "use_responses_lite": True,
                    },
                    "evidence_scope": {
                        "source": "official_codex_source",
                        "as_of": "2026-08-05",
                        "detected_codex_version": None,
                        "namespace_tools_feature_state": "not_checked",
                        "actual_tool_exposure": "runtime_unverified",
                        "runtime_verification_required": True,
                    },
                    "actions": [
                        "先在新任务确认是否出现 tool_search 和 Chrome 工具，再判断插件是否损坏。",
                        "只有运行时证据确认实际采用 Deferred 且第三方 Provider 不支持该发现链路后，才在备份模型目录的前提下做受控实验，并逐项回归 Chrome、Skill 和其他插件。",
                        "不要修改顶层 web_search，也不要仅因 CLI 插件清单失败而重装插件。",
                    ],
                },
            )

    def test_default_human_report_leads_with_five_recovery_guides_and_hides_details(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
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
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
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
                "--no-command-checks",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("检查结果（5 项）", result.stdout)
            for title in (
                "保留官方登录态",
                "恢复插件与 Skill",
                "修正模型名称",
                "恢复历史任务",
                "恢复 Chrome 调用",
            ):
                self.assertIn(title, result.stdout)
            for label in (
                "当前结果：",
                "具体位置/关键参数：",
                "受什么控制：",
                "目标状态：",
                "怎么处理：",
                "怎么确认：",
            ):
                self.assertEqual(result.stdout.count(label), 5)
            self.assertIn("界面标签不能证明", result.stdout)
            self.assertIn("目录已经正确时，不再改 JSON 或反复清缓存", result.stdout)
            self.assertNotIn("技术判断：", result.stdout)
            self.assertIn("requires_openai_auth", result.stdout)
            self.assertIn("model_catalog_json", result.stdout)
            self.assertNotIn("namespace", result.stdout)
            self.assertIn("使用 --details 查看配置层、字段来源和完整诊断证据。", result.stdout)
            self.assertNotIn("生效配置\n", result.stdout)
            self.assertNotIn("配置层\n", result.stdout)

            detailed = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--details",
            )
            self.assertEqual(detailed.returncode, 0, detailed.stderr)
            self.assertIn("检查结果（5 项）", detailed.stdout)
            self.assertIn("技术判断：", detailed.stdout)
            self.assertIn("requires_openai_auth", detailed.stdout)
            self.assertIn("model_catalog_json", detailed.stdout)
            self.assertIn("生效配置\n", detailed.stdout)
            self.assertIn("配置层\n", detailed.stdout)


if __name__ == "__main__":
    unittest.main()
