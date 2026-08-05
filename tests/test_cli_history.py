from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tests.test_cli_catalog import run_doctor


class HistoryProviderTests(unittest.TestCase):
    def test_history_probe_finds_a_nonstandard_database_name_and_reports_provider_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            database_directory = codex_home / "sqlite"
            database_directory.mkdir(parents=True)
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                    ]
                ),
                encoding="utf-8",
            )
            database_path = database_directory / "session-index.prod.db"
            with sqlite3.connect(database_path) as connection:
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
                        ("current-1", "thirdparty", 0),
                        ("current-2", "thirdparty", 1),
                        ("private-task-title-must-not-leak", "openai", 0),
                        ("old-2", "openai", 0),
                        ("old-archived", "openai", 1),
                    ],
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
            self.assertNotIn("private-task-title-must-not-leak", result.stdout)
            self.assertEqual(
                {
                    "history": report["history"],
                    "findings": [
                        {
                            key: finding[key]
                            for key in ("code", "severity", "status", "category")
                        }
                        for finding in report["findings"]
                    ],
                },
                {
                    "history": {
                        "probe": "ok",
                        "database_path": "$CODEX_HOME/sqlite/session-index.prod.db",
                        "database_read_only": True,
                        "current_provider": "thirdparty",
                        "threads_total": 5,
                        "threads_current_provider": 2,
                        "threads_other_providers": 3,
                        "active_threads_other_providers": 2,
                        "provider_counts": [
                            {
                                "provider": "openai",
                                "threads_total": 3,
                                "threads_unarchived": 2,
                                "threads_archived": 1,
                            },
                            {
                                "provider": "thirdparty",
                                "threads_total": 2,
                                "threads_unarchived": 1,
                                "threads_archived": 1,
                            },
                        ],
                    },
                    "findings": [
                        {
                            "code": "history.provider_mismatch",
                            "severity": "warning",
                            "status": "open",
                            "category": "diagnostic",
                        }
                    ],
                },
            )
            self.assertIn("可能不出现在当前列表", report["findings"][0]["message"])
            self.assertNotIn("用户已明确确认", report["findings"][0]["message"])

    def test_explicit_confirmation_marks_history_provider_mismatch_as_confirmed_root_cause(self) -> None:
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
            database_path = codex_home / "history.sqlite"
            with sqlite3.connect(database_path) as connection:
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
                "--confirm-cause",
                "history.provider_mismatch",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            finding = report["findings"][0]
            self.assertEqual(
                {
                    "summary_confirmed_causes": report["summary"]["confirmed_causes"],
                    "code": finding["code"],
                    "severity": finding["severity"],
                    "status": finding["status"],
                    "category": finding["category"],
                    "intentional": finding["intentional"],
                },
                {
                    "summary_confirmed_causes": 1,
                    "code": "history.provider_mismatch",
                    "severity": "warning",
                    "status": "confirmed",
                    "category": "diagnostic",
                    "intentional": False,
                },
            )
            self.assertIn("用户已明确确认", finding["message"])
            self.assertIn("9 个未归档任务", finding["message"])
            self.assertIn("WAL/SHM", finding["remedy"])
            self.assertIn("再次取得明确确认", finding["remedy"])


if __name__ == "__main__":
    unittest.main()
