from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_cli_catalog import FIXTURES


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_FILE = REPO_ROOT / "SKILL.md"
OPENAI_YAML = REPO_ROOT / "agents" / "openai.yaml"
SKILL_RUNNER = REPO_ROOT / "scripts" / "run_skill.py"
README_ZH = REPO_ROOT / "README.zh-CN.md"
README_EN = REPO_ROOT / "README.md"
COMPATIBILITY_DOC = REPO_ROOT / "docs" / "COMPATIBILITY.md"
HISTORY_DOC = REPO_ROOT / "docs" / "HISTORY-PROVIDER.md"
AGENT_PROMPT = REPO_ROOT / "prompts" / "agent-doctor.zh-CN.md"


class SkillEntrypointTests(unittest.TestCase):
    def test_skill_metadata_exposes_natural_language_entrypoint(self) -> None:
        skill_text = SKILL_FILE.read_text(encoding="utf-8")
        frontmatter = skill_text.split("---", 2)[1]
        frontmatter_keys = {
            line.split(":", 1)[0].strip()
            for line in frontmatter.splitlines()
            if ":" in line
        }
        openai_yaml = OPENAI_YAML.read_text(encoding="utf-8")

        self.assertEqual(frontmatter_keys, {"name", "description"})
        self.assertIn("name: codex-provider-doctor", frontmatter)
        self.assertIn("Do not ask the user to copy or execute terminal commands", skill_text)
        self.assertIn("$codex-provider-doctor", openai_yaml)
        self.assertIn("allow_implicit_invocation: true", openai_yaml)

    def test_skill_ranks_live_plugin_evidence_above_cli_probe_failures(self) -> None:
        skill_text = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("live smoke test", skill_text)
        self.assertIn("Settings or Plugins page", skill_text)
        self.assertIn("does not prove that a plugin is absent or broken", skill_text)
        self.assertIn("does not change exit code 0 by itself", skill_text)

    def test_skill_uses_the_structured_human_report_instead_of_free_form_json_summary(self) -> None:
        skill_text = SKILL_FILE.read_text(encoding="utf-8")
        prompt = AGENT_PROMPT.read_text(encoding="utf-8")

        self.assertIn(
            "python3 <skill-directory>/scripts/run_skill.py --problem <problem-id>",
            skill_text,
        )
        self.assertNotIn(
            "python3 <skill-directory>/scripts/run_skill.py --json --problem <problem-id>",
            skill_text,
        )
        self.assertIn("Do not add `--json` for a normal diagnosis", skill_text)
        self.assertIn("preserve every health-check card", skill_text.lower())
        self.assertIn("exact locations/key parameters", skill_text)
        self.assertIn("exact_targets", skill_text)
        self.assertIn("不要为普通诊断添加 `--json`", prompt)
        self.assertIn("具体位置/关键参数", prompt)
        self.assertIn("$CODEX_HOME/...", prompt)
        self.assertIn("solutions.health_checks", prompt)

    def test_skill_and_docs_explain_acknowledged_intent_and_scoped_compatibility(self) -> None:
        skill_text = SKILL_FILE.read_text(encoding="utf-8")
        readme_zh = README_ZH.read_text(encoding="utf-8")
        readme_en = README_EN.read_text(encoding="utf-8")
        compatibility = COMPATIBILITY_DOC.read_text(encoding="utf-8")
        history = HISTORY_DOC.read_text(encoding="utf-8")
        prompt = AGENT_PROMPT.read_text(encoding="utf-8")

        acknowledgement = "--acknowledge provider.auth.openai_with_direct_token"
        chrome_symptom = "--symptom chrome-plugin-unavailable"
        confirmed_history_cause = "--confirm-cause history.provider_mismatch"
        problem_flags = (
            "--problem keep-official-login",
            "--problem plugins-or-skills-unavailable",
            "--problem model-name-incorrect",
            "--problem history-missing",
            "--problem chrome-unavailable",
        )
        self.assertIn(acknowledgement, skill_text)
        self.assertIn(acknowledgement, readme_zh)
        self.assertIn(acknowledgement, readme_en)
        self.assertIn(acknowledgement, prompt)
        for text in (skill_text, readme_zh, readme_en, compatibility, prompt):
            self.assertIn(chrome_symptom, text)
        for text in (skill_text, readme_zh, readme_en, history, prompt):
            self.assertIn(confirmed_history_cause, text)
        for problem_flag in problem_flags:
            for text in (skill_text, readme_zh, readme_en, prompt):
                self.assertIn(problem_flag, text)
        self.assertIn("Catalog model count", readme_en)
        self.assertIn("模型目录条目总数", readme_zh)
        self.assertIn("--details", skill_text)
        self.assertIn("--details", readme_zh)
        self.assertIn("--details", readme_en)
        self.assertIn("[model_providers.<id>]", readme_en)
        self.assertIn("requires_openai_auth = true", readme_en)
        self.assertIn("Do not add it to the built-in `openai` Provider", readme_en)
        self.assertIn("`env_key`, direct bearer token, then the retained official authentication", readme_en)
        self.assertIn("does not confirm intent", readme_en)
        self.assertIn("exact_targets", readme_en)
        self.assertIn("exact_targets", readme_zh)
        self.assertIn("project Skills only when the project is trusted", skill_text)
        self.assertIn("runtime_verification_required: true", compatibility)
        self.assertIn("保留官方登录态", readme_zh)
        self.assertIn("official model", compatibility)
        self.assertIn("review_if_symptomatic", compatibility)
        self.assertIn("Deferred is eligible", compatibility)
        self.assertIn("namespace tools", compatibility)
        self.assertIn("Direct", compatibility)
        self.assertIn("leading static compatibility suspect", compatibility)
        self.assertIn("does not prove a unique root cause", compatibility)
        self.assertIn("provider_counts", history)
        self.assertIn("database plus its WAL/SHM sidecars", history)

    def test_readme_install_prompt_only_requires_the_repository_url(self) -> None:
        readme_zh = README_ZH.read_text(encoding="utf-8")
        readme_en = README_EN.read_text(encoding="utf-8")

        self.assertIn(
            "帮我安装这个 Skill：https://github.com/wildbyteai/codex-provider-doctor",
            readme_zh,
        )
        self.assertIn(
            "Install this Skill for me: https://github.com/wildbyteai/codex-provider-doctor",
            readme_en,
        )
        self.assertNotIn("path `.`", readme_zh)
        self.assertNotIn("repository root (path", readme_en)

    def test_bundled_runner_works_without_an_installed_package(self) -> None:
        codex_home = FIXTURES / "profile-home"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["DEEPSEEK_API_KEY"] = "test-only-placeholder"

        with tempfile.TemporaryDirectory() as unrelated_working_directory:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_RUNNER),
                    "--codex-home",
                    str(codex_home),
                    "--profile",
                    "work",
                    "--system-config",
                    str(FIXTURES / "missing-system.toml"),
                    "--no-command-checks",
                    "--json",
                ],
                cwd=unrelated_working_directory,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["summary"]["status"], "ok")
        self.assertEqual(report["effective"]["model_provider"], "thirdparty")
        self.assertEqual(report["catalog"]["selected_model"]["slug"], "deepseek-v4-flash")

    def test_bundled_runner_defaults_to_the_six_field_human_health_check(self) -> None:
        codex_home = FIXTURES / "profile-home"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["DEEPSEEK_API_KEY"] = "test-only-placeholder"

        result = subprocess.run(
            [
                sys.executable,
                str(SKILL_RUNNER),
                "--codex-home",
                str(codex_home),
                "--profile",
                "work",
                "--system-config",
                str(FIXTURES / "missing-system.toml"),
                "--no-command-checks",
                "--problem",
                "model-name-incorrect",
            ],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(result.stdout.lstrip().startswith("{"))
        for label in (
            "当前结果：",
            "具体位置/关键参数：",
            "受什么控制：",
            "目标状态：",
            "怎么处理：",
            "怎么确认：",
        ):
            self.assertEqual(result.stdout.count(label), 1)


if __name__ == "__main__":
    unittest.main()
