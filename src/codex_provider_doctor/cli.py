from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from codex_provider_doctor.config import resolve_configuration
from codex_provider_doctor.diagnostics import (
    auth_report,
    compact_report,
    compatibility_report,
    history_report,
    inspect_catalog,
    plugins_report,
    provider_report,
    runtime_report,
    skills_report,
)
from codex_provider_doctor.report import (
    localize_report,
    manual_checks,
    render_human,
    report_origins,
)
from codex_provider_doctor.solutions import PROBLEM_IDS, build_solutions


ACKNOWLEDGEABLE_FINDINGS = ("provider.auth.openai_with_direct_token",)
CONFIRMABLE_CAUSES = ("history.provider_mismatch",)
REPORTABLE_SYMPTOMS = ("chrome-plugin-unavailable",)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-provider-doctor")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--system-config", type=Path, default=Path("/etc/codex/config.toml"))
    parser.add_argument(
        "--compat-rule",
        choices=["deepseek-direct-tools-2026-08-03"],
        action="append",
        default=[],
    )
    parser.add_argument(
        "--symptom",
        choices=REPORTABLE_SYMPTOMS,
        action="append",
        default=[],
        help="Add an explicitly reported runtime symptom to static compatibility triage.",
    )
    parser.add_argument(
        "--problem",
        choices=PROBLEM_IDS,
        action="append",
        default=[],
        help="Select a user-facing recovery guide. Repeat the option to diagnose multiple problems.",
    )
    parser.add_argument("--no-command-checks", action="store_true")
    parser.add_argument(
        "--acknowledge",
        choices=ACKNOWLEDGEABLE_FINDINGS,
        action="append",
        default=[],
        help="Record an explicitly confirmed diagnostic intent without hiding separate risks.",
    )
    parser.add_argument(
        "--confirm-cause",
        choices=CONFIRMABLE_CAUSES,
        action="append",
        default=[],
        help="Record a user-confirmed root cause without changing the underlying read-only finding.",
    )
    parser.add_argument("-c", "--config", dest="config_overrides", action="append", default=[])
    parser.add_argument("--lang", choices=["zh-CN", "en"], default="zh-CN")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--details",
        action="store_true",
        help="Expand the human report with configuration layers, field origins, and complete evidence.",
    )
    return parser


def _execute(args: argparse.Namespace) -> int:
    codex_home = (
        args.codex_home or Path(os.environ.get("CODEX_HOME", "~/.codex"))
    ).expanduser().resolve()
    working_directory = args.cwd.expanduser().resolve()
    resolution = resolve_configuration(
        codex_home=codex_home,
        working_directory=working_directory,
        system_config=args.system_config,
        profile=args.profile,
        overrides=args.config_overrides,
    )
    config = resolution.values
    findings = list(resolution.findings)

    catalog, catalog_path, selected_model = inspect_catalog(
        config,
        resolution.origins,
        working_directory,
        findings,
    )
    explicitly_requested_problems = list(dict.fromkeys(args.problem))
    requested_problems = explicitly_requested_problems or list(PROBLEM_IDS)
    acknowledgements = set(args.acknowledge)
    if "keep-official-login" in explicitly_requested_problems:
        acknowledgements.add("provider.auth.openai_with_direct_token")
    provider = provider_report(config, findings, acknowledgements)
    command_checks = not args.no_command_checks
    codex_binary = shutil.which("codex") if command_checks else None
    runtime = runtime_report(command_checks, codex_binary, findings)
    reported_symptoms = list(dict.fromkeys(args.symptom))
    if "chrome-unavailable" in explicitly_requested_problems:
        reported_symptoms = list(
            dict.fromkeys([*reported_symptoms, "chrome-plugin-unavailable"])
        )
    compatibility = compatibility_report(
        args.compat_rule,
        reported_symptoms,
        selected_model,
        provider,
        runtime["codex_version"],
        findings,
    )
    compact = compact_report(
        config,
        resolution.origins,
        selected_model,
        catalog_path,
        findings,
    )
    auth = auth_report(config, codex_home, command_checks, codex_binary, findings)
    plugins = plugins_report(config, command_checks, codex_binary, findings)
    skills = skills_report(
        codex_home,
        resolution.project.get("root"),
        str(resolution.project.get("trust_level") or "unknown"),
    )
    history = history_report(config, codex_home, findings, set(args.confirm_cause))

    error_count = sum(item["severity"] == "error" for item in findings)
    warning_count = sum(item["severity"] == "warning" for item in findings)
    info_count = sum(item["severity"] == "info" for item in findings)
    unverified_count = sum(item["status"] == "unverified" for item in findings)
    acknowledged_count = sum(item["status"] == "acknowledged" for item in findings)
    confirmed_cause_count = sum(
        item["status"] == "confirmed" and item["category"] == "diagnostic"
        for item in findings
    )
    intentional_count = sum(item["intentional"] is True for item in findings)
    status = "error" if error_count else "warning" if warning_count else "ok"
    report = {
        "schema_version": 1,
        "effective": {
            "model": config.get("model"),
            "model_provider": config.get("model_provider", "openai"),
            "model_catalog_json": str(catalog_path) if catalog_path else None,
            "web_search": config.get("web_search"),
            "origins": report_origins(config, resolution.origins),
        },
        "catalog": catalog,
        "provider": provider,
        "compatibility": compatibility,
        "auth": auth,
        "plugins": plugins,
        "skills": skills,
        "runtime": runtime,
        "compact": compact,
        "history": history,
        "layers": resolution.layers,
        "project": resolution.project,
        "manual_checks": manual_checks(),
        "findings": findings,
        "summary": {
            "status": status,
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
            "unverified": unverified_count,
            "acknowledged": acknowledged_count,
            "confirmed_causes": confirmed_cause_count,
            "intentional": intentional_count,
        },
    }

    report = localize_report(report, args.lang)
    report["solutions"] = build_solutions(report, requested_problems, args.lang)
    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_human(report, args.lang, details=args.details))
    if error_count:
        return 2
    if warning_count:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _execute(args)
    except Exception:
        message = (
            "The doctor could not finish safely. Error details were hidden; check arguments, file permissions, and file formats."
            if args.lang == "en"
            else "诊断工具未能安全完成；异常细节已隐藏，请检查参数、文件权限和文件格式。"
        )
        if args.json:
            json.dump(
                {
                    "schema_version": 1,
                    "summary": {
                        "status": "tool_error",
                        "errors": 0,
                        "warnings": 0,
                        "info": 0,
                        "unverified": 0,
                        "acknowledged": 0,
                        "confirmed_causes": 0,
                        "intentional": 0,
                    },
                    "tool_error": {
                        "code": "doctor.internal_failure",
                        "message": message,
                    },
                },
                sys.stdout,
                ensure_ascii=False,
                indent=2,
            )
            sys.stdout.write("\n")
        else:
            sys.stderr.write(f"Codex Provider Doctor\n\n{message}\n")
        return 3
