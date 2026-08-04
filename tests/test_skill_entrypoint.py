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


if __name__ == "__main__":
    unittest.main()
