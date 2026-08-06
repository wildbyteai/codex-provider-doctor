from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from typing import Any
from urllib.parse import urlsplit

from codex_provider_doctor.common import Finding, MODEL_REPORT_FIELDS, finding


def inspect_catalog(
    config: dict[str, Any],
    origins: dict[str, str],
    working_directory: Path,
    findings: list[Finding],
) -> tuple[dict[str, Any], Path | None, dict[str, Any] | None]:
    catalog_path: Path | None = None
    selected_model: dict[str, Any] | None = None
    report: dict[str, Any] = {
        "path": None,
        "exists": None,
        "is_file": None,
        "valid": None,
        "model_count": None,
        "selected_model": None,
    }
    configured_catalog = config.get("model_catalog_json")
    if not isinstance(configured_catalog, str):
        return report, catalog_path, selected_model

    catalog_source = Path(origins["model_catalog_json"])
    catalog_path = Path(configured_catalog).expanduser()
    if not catalog_path.is_absolute():
        catalog_base = working_directory if str(catalog_source) == "<command-line>" else catalog_source.parent
        catalog_path = catalog_base / catalog_path
    catalog_path = catalog_path.resolve()
    report = {
        "path": str(catalog_path),
        "exists": catalog_path.exists(),
        "is_file": catalog_path.is_file(),
        "valid": None,
        "model_count": None,
        "selected_model": None,
    }
    if not catalog_path.exists():
        findings.append(
            finding(
                "catalog.file_missing",
                "error",
                "模型目录文件不存在",
                "model_catalog_json 指向的文件没有找到。",
                "确认最终生效的配置层，并把 model_catalog_json 改为实际存在的模型目录路径。",
            )
        )
        return report, catalog_path, selected_model
    if not catalog_path.is_file():
        findings.append(
            finding(
                "catalog.not_regular_file",
                "error",
                "模型目录路径不是普通文件",
                "model_catalog_json 指向的路径存在，但它不是可以读取的普通 JSON 文件。",
                "确认最终生效的配置层，并把 model_catalog_json 改为实际模型目录 JSON 文件的路径。",
            )
        )
        return report, catalog_path, selected_model

    try:
        with catalog_path.open("r", encoding="utf-8") as handle:
            catalog = json.load(handle)
    except json.JSONDecodeError as error:
        report["valid"] = False
        findings.append(
            finding(
                "catalog.invalid_json",
                "error",
                "模型目录不是有效 JSON",
                f"解析失败位置：第 {error.lineno} 行，第 {error.colno} 列。",
                "修正 JSON 语法后重新运行；不要把含 Token 的完整文件粘贴到公开报告。",
            )
        )
        return report, catalog_path, selected_model

    if not isinstance(catalog, dict):
        report["valid"] = False
        findings.append(
            finding(
                "catalog.root_not_object",
                "error",
                "模型目录顶层必须是 JSON 对象",
                "当前 JSON 可以解析，但不是包含 models 数组的对象。",
                "把模型条目放入 {\"models\": [...]} 结构后重新运行。",
            )
        )
        return report, catalog_path, selected_model
    if not isinstance(catalog.get("models"), list):
        report["valid"] = False
        findings.append(
            finding(
                "catalog.models_not_array",
                "error",
                "模型目录的 models 必须是数组",
                "JSON 可以解析，但 models 字段的类型不正确。",
                "把 models 改为由模型对象组成的 JSON 数组。",
            )
        )
        return report, catalog_path, selected_model

    report["valid"] = True
    report["model_count"] = len(catalog["models"])
    requested_model = config.get("model")
    requested_model = requested_model if isinstance(requested_model, str) else ""
    candidates = [
        entry
        for entry in catalog["models"]
        if isinstance(entry, dict)
        and isinstance(entry.get("slug"), str)
        and entry["slug"]
    ]
    matches = [
        entry
        for entry in candidates
        if requested_model.startswith(entry["slug"])
    ]
    if not matches:
        namespace_parts = requested_model.split("/")
        if len(namespace_parts) == 2:
            unprefixed_model = namespace_parts[1]
            matches = [
                entry
                for entry in candidates
                if unprefixed_model.startswith(entry["slug"])
            ]
    if not matches:
        findings.append(
            finding(
                "catalog.model_metadata_fallback",
                "warning",
                "活动模型没有匹配到目录元数据",
                "Codex 会按最长 slug 前缀匹配；首次未命中且 model 只有一层简单命名空间时，会去掉斜杠前缀再试一次。当前两步都没有命中，因此会使用回退模型元数据，而不是阻断请求。",
                "如果需要自定义显示名称或能力字段，增加能被当前 model 前缀命中的目录条目；同时用 App Server model/list 和一次真实请求分别确认显示与路由。",
            )
        )
        return report, catalog_path, selected_model
    longest_length = max(len(entry["slug"]) for entry in matches)
    matches = [entry for entry in matches if len(entry["slug"]) == longest_length]
    if len(matches) > 1:
        findings.append(
            finding(
                "catalog.model_duplicate",
                "error",
                "活动模型 slug 在目录中重复",
                "models 数组中有多个同长度条目成为最长前缀匹配结果，doctor 无法可靠选择对应元数据。",
                "只保留一个获胜的最长前缀条目，或让它们使用不同 slug。",
            )
        )
        return report, catalog_path, selected_model

    selected_model = matches[0]
    report["selected_model"] = {
        field: selected_model.get(field)
        for field in MODEL_REPORT_FIELDS
    }
    display_name = selected_model.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        findings.append(
            finding(
                "catalog.display_name_unclear",
                "warning",
                "活动模型缺少清晰的显示名称",
                "匹配到的模型条目没有非空 display_name，模型选择器可能只能显示难以辨认的 slug。",
                "在实际生效的模型目录条目中补充简短、可辨认的 display_name，然后完全重启 Codex 并新建任务检查模型列表。",
            )
        )
    return report, catalog_path, selected_model


def provider_report(
    config: dict[str, Any],
    findings: list[Finding],
    acknowledgements: set[str] | None = None,
) -> dict[str, Any]:
    acknowledgements = acknowledgements or set()
    if "requires_openai_auth" in config:
        findings.append(
            finding(
                "provider.auth.requires_openai_auth_misplaced",
                "warning",
                "requires_openai_auth 放错了位置",
                "顶层 requires_openai_auth 不会配置活动 Provider；该字段必须位于 [model_providers.<id>] 内。",
                "如果目标是让活动自定义 Provider 保留官方账户状态，把 requires_openai_auth = true 放到对应 [model_providers.<id>] 块内；第三方请求凭据仍按自身优先级单独判断。",
            )
        )
    provider_id = config.get("model_provider", "openai")
    providers = config.get("model_providers")
    provider = providers.get(provider_id) if isinstance(providers, dict) else None

    if provider_id == "openai" and not isinstance(provider, dict):
        return {
            "id": "openai",
            "exists": True,
            "name": "OpenAI (built-in)",
            "host": None,
            "wire_api": "responses",
            "requires_openai_auth": True,
            "env_key": None,
            "env_key_is_set": None,
            "auth_command_configured": False,
            "direct_bearer_token_configured": False,
            "authentication_intent": None,
        }

    if not isinstance(provider, dict):
        findings.append(
            finding(
                "provider.missing",
                "error",
                "活动 Provider 不存在",
                f"model_provider 指向 {provider_id!r}，但 model_providers 中没有对应配置块。",
                f"添加 [model_providers.{provider_id}]，或把 model_provider 改为已经存在的 ID。",
            )
        )
        return {
            "id": provider_id,
            "exists": False,
            "name": None,
            "host": None,
            "wire_api": None,
            "requires_openai_auth": False,
            "env_key": None,
            "env_key_is_set": None,
            "auth_command_configured": False,
            "direct_bearer_token_configured": False,
            "authentication_intent": None,
        }

    requires_openai_auth = provider.get("requires_openai_auth") is True
    env_key = provider.get("env_key") if isinstance(provider.get("env_key"), str) else None
    env_key_is_set = bool(os.environ.get(env_key)) if env_key else None
    auth_command_configured = isinstance(provider.get("auth"), dict)
    direct_token_configured = "experimental_bearer_token" in provider
    authentication_intent: dict[str, Any] | None = None

    conflicting_methods = auth_command_configured and (
        requires_openai_auth or env_key is not None or direct_token_configured
    )
    if conflicting_methods:
        findings.append(
            finding(
                "provider.auth.multiple_methods",
                "error",
                "Provider 命令认证与其他认证字段冲突",
                "[model_providers.<id>].auth 不能与 env_key、experimental_bearer_token 或 requires_openai_auth 同时配置；Codex 会拒绝该 Provider 配置。",
                "确认第三方接口要使用的请求凭据，只保留命令认证或其他 Provider 认证字段中的一条路径。",
            )
        )
    if (
        requires_openai_auth
        and direct_token_configured
        and env_key is None
        and not auth_command_configured
    ):
        intent_code = "provider.auth.openai_with_direct_token"
        intent_acknowledged = intent_code in acknowledgements
        authentication_intent = {
            "combination": "official_login_retained_with_explicit_provider_token",
            "status": "acknowledged" if intent_acknowledged else "unverified",
            "intentional": True if intent_acknowledged else None,
            "acknowledgement_code": intent_code,
            "official_login_state": "retained_by_requires_openai_auth",
            "provider_request_authentication": "explicit_bearer_token_precedes_official_auth",
            "requires_openai_auth_config_path": f"model_providers.{provider_id}.requires_openai_auth",
            "plaintext_token_risk": "independent_warning",
        }
        findings.append(
            finding(
                intent_code,
                "info",
                "双认证配置已确认为有意" if intent_acknowledged else "双认证配置意图尚未确认",
                (
                    f"用户已明确确认设计意图：[model_providers.{provider_id}] 下的 requires_openai_auth = true 保留官方 ChatGPT/Codex 账户状态，第三方 Provider 请求优先使用显式 Bearer Token，以继续使用官方插件能力；插件是否真实可用仍需独立验证。"
                    if intent_acknowledged
                    else f"当前配置在 [model_providers.{provider_id}] 下同时设置 requires_openai_auth = true 和显式 Provider Token；这会保留官方账户状态，并让显式 Token 优先用于第三方请求，但诊断器不能在没有用户确认时推断这是有意设计。"
                ),
                (
                    "保持这组双认证配置，并分别验证官方登录、第三方模型请求、Skill 和插件；配置文件明文 Token 风险继续作为独立警告处理。"
                    if intent_acknowledged
                    else "用户明确确认这组直接 Token 设计后，使用 --acknowledge provider.auth.openai_with_direct_token 记录确认；在此之前不要自动删除任一字段。"
                ),
                status="acknowledged" if intent_acknowledged else "unverified",
                category="intent",
                intentional=True if intent_acknowledged else None,
            )
        )
    if (
        env_key
        and not env_key_is_set
        and not auth_command_configured
    ):
        findings.append(
            finding(
                "provider.auth.env_missing",
                "warning",
                "Provider 的 API Key 环境变量没有注入",
                f"env_key 指向 {env_key}，但当前启动环境中没有检测到非空值。env_key 优先于直接 Token 和官方认证，缺失时请求会直接失败而不是回退；报告不会读取或显示变量内容。",
                "在真正启动 Codex 的环境中设置该变量，或在确认替代凭据后移除 env_key，然后完全重启 Codex；不要把 Key 写进截图、Issue 或诊断报告。",
            )
        )
    if direct_token_configured:
        remedy = (
            "如果已确认官方登录状态独立保留、第三方 Provider 请求使用显式 Token，先保持行为不变并做版本化验证；随后优先迁移到不把 Token 明文写进配置的凭据方案，并轮换旧 Token。"
            if requires_openai_auth
            else "优先改用 env_key 或命令凭据助手，并轮换已经写入明文配置的 Token。"
        )
        findings.append(
            finding(
                "provider.auth.direct_token",
                "warning",
                "配置文件中存在直接 Bearer Token",
                "检测到 experimental_bearer_token；报告不会读取或显示它的值。",
                remedy,
                category="security",
            )
        )

    base_url = provider.get("base_url")
    host = urlsplit(base_url).hostname if isinstance(base_url, str) else None
    return {
        "id": provider_id,
        "exists": True,
        "name": provider.get("name"),
        "host": host,
        "wire_api": provider.get("wire_api", "responses"),
        "requires_openai_auth": requires_openai_auth,
        "env_key": env_key,
        "env_key_is_set": env_key_is_set,
        "auth_command_configured": auth_command_configured,
        "direct_bearer_token_configured": direct_token_configured,
        "authentication_intent": authentication_intent,
    }


def compatibility_report(
    rule_ids: list[str],
    symptom_ids: list[str],
    selected_model: dict[str, Any] | None,
    provider: dict[str, Any],
    codex_version: str | None,
    findings: list[Finding],
) -> dict[str, Any]:
    symptom_assessments: list[dict[str, Any]] = []
    for symptom_id in symptom_ids:
        if symptom_id != "chrome-plugin-unavailable":
            continue
        built_in_openai = (
            provider.get("id") == "openai"
            and provider.get("name") == "OpenAI (built-in)"
        )
        if built_in_openai:
            applicability_reason = "built_in_openai_provider"
        elif provider.get("exists") is not True:
            applicability_reason = "provider_missing"
        elif provider.get("wire_api") != "responses":
            applicability_reason = "provider_wire_api_not_responses"
        elif selected_model is None:
            applicability_reason = "selected_model_unavailable"
        else:
            applicability_reason = None
        applicable = applicability_reason is None
        observed = selected_model.get("supports_search_tool") if applicable and selected_model else None
        if not applicable:
            assessment = "not_applicable"
            next_step = "continue_provider_specific_checks"
            exposure_inference = "not_applicable"
        elif observed is False:
            assessment = "deferred_search_disabled"
            next_step = "verify_declared_exposure_and_live_invocation"
            exposure_inference = "deferred_exposure_removed_by_false"
        elif observed is True:
            assessment = "deferred_exposure_eligible"
            next_step = "verify_namespace_tools_and_live_invocation"
            exposure_inference = "deferred_only_if_namespace_tools_enabled"
        else:
            assessment = "field_unavailable"
            next_step = "verify_catalog_field_and_runtime"
            exposure_inference = "undetermined"
        symptom_assessments.append(
            {
                "id": symptom_id,
                "applicability": "applicable" if applicable else "not_applicable",
                "applicability_reason": applicability_reason,
                "evidence_source": "catalog.selected_model.supports_search_tool",
                "observed_supports_search_tool": observed,
                "assessment": assessment,
                "causality": "not_proven",
                "live_smoke_test": "not_run_by_doctor",
                "next_step": next_step,
                "namespace_tools_feature_state": "not_checked",
                "exposure_inference": exposure_inference,
                "semantics_source": "official_codex_source",
                "semantics_as_of": "2026-08-05",
                "detected_codex_version": codex_version,
                "runtime_verification_required": True,
            }
        )
        if applicable and observed is False:
            findings.append(
                finding(
                    "compat.chrome.supports_search_tool_false",
                    "info",
                    "模型关闭了 Deferred 工具发现",
                    "用户报告 Chrome 不可用，且活动第三方 Responses 模型设置 supports_search_tool = false。该值会关闭 search_tool_enabled；namespace tools 开启时，Deferred 暴露会被移除，只剩插件声明允许的 Direct 或 Code 路径。如果 Chrome 依赖 Deferred，它可能不出现在新任务中，因此这是首要兼容性疑点，但不是唯一根因。",
                    "先核对实际模型目录条目、Chrome 的工具暴露证据和新任务工具列表，再做一次最小真实调用。只有证据表明 Chrome 依赖 Deferred 时，才备份模型目录后对 supports_search_tool = true 做受控对照；不要修改顶层 web_search，也不要因 CLI 插件清单失败而重装插件。",
                    status="unverified",
                    category="verification",
                )
            )
    rules: list[dict[str, Any]] = []
    for rule_id in rule_ids:
        if rule_id != "deepseek-direct-tools-2026-08-03":
            continue
        recommended = {
            "tool_mode": "direct",
            "supports_search_tool": False,
            "use_responses_lite": False,
        }
        built_in_openai = (
            provider.get("id") == "openai"
            and provider.get("name") == "OpenAI (built-in)"
        )
        if built_in_openai:
            applicability_reason = "built_in_openai_provider"
        elif provider.get("exists") is not True:
            applicability_reason = "provider_missing"
        elif provider.get("wire_api") != "responses":
            applicability_reason = "provider_wire_api_not_responses"
        elif selected_model is None:
            applicability_reason = "selected_model_unavailable"
        elif not any(
            isinstance(selected_model.get(field), str)
            and "deepseek" in selected_model[field].casefold()
            for field in ("slug", "display_name")
        ):
            applicability_reason = "selected_model_outside_rule_scope"
        else:
            applicability_reason = None
        applicable = applicability_reason is None
        field_assessments: list[dict[str, Any]] = []
        observed_differences: list[dict[str, Any]] = []
        changes: list[dict[str, Any]] = []
        if applicable and selected_model is not None:
            for field, expected in recommended.items():
                observed = selected_model.get(field)
                differs = observed != expected
                if differs:
                    observed_differences.append(
                        {"field": field, "from": observed, "to": expected}
                    )
                if field == "tool_mode":
                    assessment_status = "review_if_symptomatic" if differs else "aligned"
                else:
                    assessment_status = "change_recommended" if differs else "aligned"
                    if differs:
                        changes.append({"field": field, "from": observed, "to": expected})
                field_assessments.append(
                    {
                        "field": field,
                        "observed": observed,
                        "case_value": expected,
                        "status": assessment_status,
                    }
                )
        rules.append(
            {
                "id": rule_id,
                "scope": "Codex 0.146.0-alpha.9.2 + one observed third-party API combination",
                "applicability": "applicable" if applicable else "not_applicable",
                "applicability_reason": applicability_reason,
                "selected_model_available": selected_model is not None,
                "detected_codex_version": codex_version,
                "recommended": recommended,
                "field_assessments": field_assessments,
                "observed_differences": observed_differences,
                "suggested_changes": changes,
                "notes": [
                    "This is a versioned compatibility case, not a universal third-party provider default.",
                    "tool_mode = direct is symptom-driven in this case; code_mode_only does not require a change when direct tools already work.",
                    "supports_search_tool = false applies only to the selected third-party Responses provider case, not the built-in OpenAI provider.",
                    "supports_search_tool is not the same setting as top-level web_search.",
                    "Direct tool exposure can increase the initial tool list and context usage.",
                    "After any edit, restart Codex, open a new task, and test Chrome, Web Search, and other plugins separately.",
                ],
            }
        )
        if applicable and changes:
            findings.append(
                finding(
                    "compat.deepseek_direct_tools.mismatch",
                    "warning",
                    "第三方 Responses 模型与所选兼容案例存在需处理的字段差异",
                    "所选规则来自 2026-08-03 的单机案例；supports_search_tool 或 use_responses_lite 与案例不一致。tool_mode 只在直接工具、Skill 或 Chrome 出现症状时核对。",
                    "先备份模型目录，再人工评估 suggested_changes；不要因为 supports_search_tool 而关闭顶层 web_search。修改后完全重启 Codex、新建任务，并分别测试 Chrome、Web Search 和其他插件。",
                )
            )
        if applicable and codex_version is not None and codex_version != "0.146.0-alpha.9.2":
            findings.append(
                finding(
                    "compat.rule_version_differs",
                    "warning",
                    "当前 Codex 版本与兼容规则的实测版本不同",
                    f"该规则实测于 0.146.0-alpha.9.2，当前检测到 {codex_version}。",
                    "把旧规则当作排错线索，不要当永久默认；在当前版本重新测试 Chrome、Web Search 和其他插件。",
                )
            )
    return {"rules": rules, "symptom_assessments": symptom_assessments}


def compact_report(
    config: dict[str, Any],
    origins: dict[str, str],
    selected_model: dict[str, Any] | None,
    catalog_path: Path | None,
    findings: list[Finding],
) -> dict[str, Any]:
    configured_context = config.get("model_context_window")
    if isinstance(configured_context, int) and not isinstance(configured_context, bool):
        context_window = configured_context
        context_source = origins.get("model_context_window")
        effective_context_window = context_window
    else:
        catalog_context = selected_model.get("context_window") if selected_model else None
        context_window = catalog_context if isinstance(catalog_context, int) else None
        context_source = (
            f"{catalog_path}#models[{selected_model.get('slug')}]"
            if context_window is not None and catalog_path is not None and selected_model is not None
            else None
        )
        percent = selected_model.get("effective_context_window_percent") if selected_model else None
        if context_window is not None and isinstance(percent, (int, float)) and 0 < percent <= 100:
            effective_context_window = int(context_window * percent / 100)
        else:
            effective_context_window = context_window

    configured_limit = config.get("model_auto_compact_token_limit")
    if isinstance(configured_limit, int) and not isinstance(configured_limit, bool):
        compact_limit = configured_limit
        limit_source = origins.get("model_auto_compact_token_limit")
    else:
        catalog_limit = selected_model.get("auto_compact_token_limit") if selected_model else None
        compact_limit = catalog_limit if isinstance(catalog_limit, int) else None
        limit_source = (
            f"{catalog_path}#models[{selected_model.get('slug')}]"
            if compact_limit is not None and catalog_path is not None and selected_model is not None
            else None
        )

    scope = config.get("model_auto_compact_token_limit_scope", "total")
    scope_source = origins.get("model_auto_compact_token_limit_scope", "default")
    valid: bool | None = None
    if effective_context_window is not None and compact_limit is not None:
        valid = 0 < compact_limit < effective_context_window
        if not valid:
            findings.append(
                finding(
                    "compact.limit_not_below_window",
                    "error",
                    "自动 Compact 阈值没有低于有效上下文窗口",
                    f"当前有效窗口是 {effective_context_window}，自动压缩阈值是 {compact_limit}。",
                    "根据模型真实窗口留出安全余量，把顶层 model_auto_compact_token_limit 或目录中的 auto_compact_token_limit 调低。",
                )
            )
    return {
        "context_window": context_window,
        "context_source": context_source,
        "effective_context_window": effective_context_window,
        "auto_compact_token_limit": compact_limit,
        "limit_source": limit_source,
        "scope": scope,
        "scope_source": scope_source,
        "valid": valid,
    }


def _run_codex(codex_binary: str, arguments: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        result = subprocess.run(
            [codex_binary, *arguments],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if len(result.stdout) > 2_000_000:
        return None
    return result


def runtime_report(
    command_checks: bool,
    codex_binary: str | None,
    findings: list[Finding],
) -> dict[str, Any]:
    if not command_checks:
        return {"codex_command_found": None, "version_probe": "skipped", "codex_version": None}
    if codex_binary is None:
        return {"codex_command_found": False, "version_probe": "unavailable", "codex_version": None}
    result = _run_codex(codex_binary, ["--version"])
    if result is None or result.returncode != 0:
        findings.append(
            finding(
                "runtime.version_probe_failed",
                "warning",
                "无法读取 Codex 版本",
                "codex --version 没有成功返回；原始输出已丢弃。",
                "在终端单独运行 codex --version，并在命令异常时更新 Codex。",
            )
        )
        return {"codex_command_found": True, "version_probe": "failed", "codex_version": None}
    match = re.search(r"\b(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9._-]+)?)\b", result.stdout)
    if match is None:
        findings.append(
            finding(
                "runtime.version_probe_failed",
                "warning",
                "无法识别 Codex 版本",
                "codex --version 返回成功，但没有可识别的版本号；原始输出已丢弃。",
                "在终端单独运行 codex --version，确认安装来源和版本格式。",
            )
        )
        return {"codex_command_found": True, "version_probe": "failed", "codex_version": None}
    return {
        "codex_command_found": True,
        "version_probe": "ok",
        "codex_version": match.group(1),
    }


def auth_report(
    config: dict[str, Any],
    codex_home: Path,
    command_checks: bool,
    codex_binary: str | None,
    findings: list[Finding],
) -> dict[str, Any]:
    report = {
        "credentials_store": config.get("cli_auth_credentials_store", "file"),
        "cache_path": "$CODEX_HOME/auth.json",
        "cache_exists": (codex_home / "auth.json").is_file(),
        "cache_read": False,
        "login_probe": "skipped",
        "login_method": None,
    }
    if not command_checks:
        return report
    if codex_binary is None:
        report["login_probe"] = "unavailable"
        findings.append(
            finding(
                "runtime.codex.not_found",
                "warning",
                "找不到 Codex 命令",
                "无法运行只读登录与插件状态检查。",
                "确认 Codex CLI 已安装并位于 PATH，或使用 --no-command-checks 只做文件诊断。",
            )
        )
        return report
    result = _run_codex(codex_binary, ["login", "status"])
    if result is None or result.returncode != 0:
        report["login_probe"] = "failed"
        findings.append(
            finding(
                "auth.login_probe_failed",
                "warning",
                "无法确认 Codex 登录方式",
                "codex login status 没有成功返回；原始输出已丢弃。",
                "在终端单独运行 codex login status，确认显示 ChatGPT、API key 或 access token 登录。",
            )
        )
        return report

    normalized = f"{result.stdout}\n{result.stderr}".lower()
    if "not logged" in normalized or "signed out" in normalized:
        method = "signed_out"
    elif "chatgpt" in normalized:
        method = "chatgpt"
    elif "api key" in normalized or "api-key" in normalized:
        method = "api_key"
    elif "access token" in normalized:
        method = "access_token"
    else:
        method = "unknown"
    report["login_probe"] = "ok"
    report["login_method"] = method
    if method in {"signed_out", "unknown"}:
        findings.append(
            finding(
                "auth.login_not_confirmed",
                "warning",
                "没有确认到可用的 Codex 登录态",
                "登录状态不是明确的 ChatGPT、API key 或 access token。",
                "运行 codex login 并完成官方登录；不要手工复制、覆盖或公开 auth.json。",
            )
        )
    return report


def _record_unverified_plugin_inventory(findings: list[Finding]) -> None:
    findings.append(
        finding(
            "plugins.invalid_output",
            "info",
            "CLI 插件探针返回了无法解析的状态",
            "插件命令没有返回当前工具支持的 JSON 清单结构；原始输出已丢弃。这个结果只表示 CLI 清单无法解析，不能据此判断插件不可用。",
            "优先查看 Codex 设置页面并进行实际功能测试。如果两者正常，把这项视为 CLI 兼容性缺口；只有实际功能也失败时才继续修复。",
            status="unverified",
            category="verification",
        )
    )


def plugins_report(
    config: dict[str, Any],
    command_checks: bool,
    codex_binary: str | None,
    findings: list[Finding],
) -> dict[str, Any]:
    features = config.get("features") if isinstance(config.get("features"), dict) else {}
    plugins_enabled = features.get("plugins", True) is not False
    apps_enabled = features.get("apps", True) is not False
    remote_plugin_enabled = features.get("remote_plugin", True) is not False
    report: dict[str, Any] = {
        "probe": "skipped",
        "inventory_status": "unverified",
        "features": {
            "plugins": plugins_enabled,
            "apps": apps_enabled,
            "remote_plugin": remote_plugin_enabled,
        },
        "inventory_count": None,
        "chrome": {"found": None, "installed": None, "enabled": None},
    }
    if not plugins_enabled:
        findings.append(
            finding(
                "plugins.feature.plugins_disabled",
                "warning",
                "插件系统被关闭",
                "features.plugins = false 会阻止插件清单和插件包中的工具或 Skill 加载。",
                "如果要使用插件，请在用户级配置把 features.plugins 设为 true 或删除显式 false，完全重启 Codex 并新建任务。",
            )
        )
    if not apps_enabled:
        findings.append(
            finding(
                "plugins.feature.apps_disabled",
                "warning",
                "App 与连接器能力被关闭",
                "features.apps = false 只关闭 App/连接器集成，不等于关闭全部插件、MCP 或独立 Skill。",
                "只有缺失能力属于 App/连接器时，才在用户级配置开启 features.apps，完全重启 Codex 并新建任务。",
            )
        )
    if not remote_plugin_enabled:
        findings.append(
            finding(
                "plugins.feature.remote_plugin_disabled",
                "warning",
                "远程插件目录被关闭",
                "features.remote_plugin = false 可能使远程 Plugins Directory 无法加载。",
                "需要浏览或使用远程插件目录时，开启 features.remote_plugin 后重启 Codex。",
            )
        )
    if not command_checks:
        return report
    if codex_binary is None:
        report["probe"] = "unavailable"
        return report

    result = _run_codex(codex_binary, ["plugin", "list", "--json"])
    if result is None or result.returncode != 0:
        report["probe"] = "failed"
        normalized = (
            f"{result.stdout}\n{result.stderr}".lower()
            if result is not None
            else ""
        )
        if "marketplace" in normalized and "supported manifest" in normalized:
            findings.append(
                finding(
                    "plugins.marketplace_snapshot_invalid",
                    "info",
                    "CLI 插件探针未能核验实际状态",
                    "codex plugin list --json 因一个插件市场目录缺少当前命令支持的 manifest 而失败；原始路径和输出已丢弃。这个结果只表示 CLI 清单不可用，不能据此判断插件不可用。",
                    "优先查看 Codex 设置页面并进行实际功能测试。如果设置页面可见或实际调用正常，无需重装或清理缓存；只有界面和运行时也失败时，才考虑刷新或重新安装插件市场，清理缓存前先备份。",
                    status="unverified",
                    category="verification",
                )
            )
            return report
        findings.append(
            finding(
                "plugins.probe_failed",
                "info",
                "CLI 插件探针未能核验实际状态",
                "codex plugin list --json 没有成功返回；原始输出已丢弃。这个结果只表示 CLI 清单不可用，不能据此判断插件不存在、未开启或损坏。",
                "优先查看 Codex 设置页面并进行实际功能测试。如果界面或实际调用已经确认插件正常，不要重装或清理缓存。",
                status="unverified",
                category="verification",
            )
        )
        return report
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        report["probe"] = "failed"
        _record_unverified_plugin_inventory(findings)
        return report

    installed_collection = False
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("installed"), list):
        raw_items = payload["installed"]
        installed_collection = True
    elif isinstance(payload, dict) and isinstance(payload.get("plugins"), list):
        raw_items = payload["plugins"]
    else:
        report["probe"] = "failed"
        _record_unverified_plugin_inventory(findings)
        return report
    items: list[dict[str, Any]] = []
    unrecognized_item_seen = False
    for item in raw_items:
        if not isinstance(item, dict):
            unrecognized_item_seen = True
            continue
        name = item.get("name") or item.get("id") or item.get("slug")
        if not isinstance(name, str) or not name.strip():
            unrecognized_item_seen = True
            continue
        items.append(
            {
                "name": name,
                "installed": item.get("installed", True if installed_collection else None),
                "enabled": item.get("enabled"),
            }
        )
    if unrecognized_item_seen:
        report["probe"] = "failed"
        _record_unverified_plugin_inventory(findings)
        return report
    chrome = next(
        (item for item in items if item["name"].strip().casefold() == "chrome"),
        None,
    )
    report["probe"] = "ok"
    report["inventory_status"] = "verified"
    report["inventory_count"] = len(items)
    report["chrome"] = (
        {"found": True, "installed": chrome["installed"], "enabled": chrome["enabled"]}
        if chrome is not None
        else {"found": False, "installed": False, "enabled": False}
    )
    if chrome is None or chrome.get("installed") is False:
        findings.append(
            finding(
                "plugins.chrome.not_installed",
                "info",
                "没有确认 Chrome 插件已经安装",
                "插件列表中没有找到已安装的 Chrome 插件。",
                "先查看 Plugins 设置页并尝试一次实际调用；只有更强证据也确认不可用时，才考虑安装或修复 Chrome 插件。",
                status="unverified",
                category="verification",
            )
        )
    elif chrome.get("enabled") is False:
        findings.append(
            finding(
                "plugins.chrome.disabled",
                "info",
                "Chrome 插件处于关闭状态",
                "CLI 插件清单把 Chrome 标记为未启用，但这只是低优先级辅助证据。",
                "先在 Plugins 设置页核对并尝试一次实际调用；只有更强证据也确认未启用时，再打开 Chrome、完全重启 Codex并新建任务。",
                status="unverified",
                category="verification",
            )
        )
    return report


def _count_skill_manifests(root: Path) -> tuple[int | None, str]:
    if not root.is_dir():
        return 0, "not_found"
    try:
        return sum(1 for path in root.rglob("SKILL.md") if path.is_file()), "ok"
    except OSError:
        return None, "failed"


def skills_report(
    codex_home: Path,
    project_root: str | None,
    project_trust: str,
) -> dict[str, Any]:
    user_root = codex_home / "skills"
    project_skill_root = (
        Path(project_root) / ".agents" / "skills" if project_root else None
    )
    user_count, user_status = _count_skill_manifests(user_root)
    user_source = {
        "scope": "user",
        "path": "$CODEX_HOME/skills",
        "exists": user_root.is_dir(),
        "count": user_count,
        "status": user_status,
    }

    project_exists = project_skill_root.is_dir() if project_skill_root else False
    if project_skill_root is None:
        project_count: int | None = 0
        project_status = "not_applicable"
    elif not project_exists:
        project_count = 0
        project_status = "not_found"
    elif project_trust != "trusted":
        project_count = None
        project_status = f"skipped_{project_trust.replace('-', '_')}"
    else:
        project_count, project_status = _count_skill_manifests(project_skill_root)
    project_source = {
        "scope": "project",
        "path": "$PROJECT_ROOT/.agents/skills",
        "exists": project_exists,
        "count": project_count,
        "status": project_status,
        "trust_level": project_trust,
    }
    sources = [user_source, project_source]
    coverage = (
        "complete"
        if all(source["status"] in {"ok", "not_found", "not_applicable"} for source in sources)
        else "partial"
    )
    probe = "partial" if any(source["status"] == "failed" for source in sources) else "ok"
    return {
        "probe": probe,
        "coverage": coverage,
        "total": sum(
            source["count"] for source in sources if isinstance(source["count"], int)
        ),
        "sources": sources,
    }


def _history_database_candidates(codex_home: Path) -> list[Path]:
    candidates: list[Path] = []
    search_directories = [codex_home, codex_home / "sqlite"]
    for directory in search_directories:
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                candidates.append(path.resolve())
    return sorted(
        set(candidates),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )


def _display_codex_home_path(path: Path, codex_home: Path) -> str:
    try:
        relative = path.relative_to(codex_home)
    except ValueError:
        return "<outside-$CODEX_HOME>"
    return f"$CODEX_HOME/{relative.as_posix()}"


def history_report(
    config: dict[str, Any],
    codex_home: Path,
    findings: list[Finding],
    confirmed_causes: set[str] | None = None,
) -> dict[str, Any]:
    confirmed_causes = confirmed_causes or set()
    current_provider = config.get("model_provider", "openai")
    empty_report: dict[str, Any] = {
        "probe": "not_found",
        "database_path": None,
        "database_read_only": True,
        "current_provider": current_provider,
        "threads_total": None,
        "threads_current_provider": None,
        "threads_other_providers": None,
        "active_threads_other_providers": None,
        "provider_counts": None,
    }
    if not isinstance(current_provider, str):
        return empty_report

    compatible_database_seen = False
    for database_path in _history_database_candidates(codex_home):
        try:
            uri = f"{database_path.as_uri()}?mode=ro"
            with sqlite3.connect(uri, uri=True, timeout=1) as connection:
                connection.execute("PRAGMA query_only = ON")
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(threads)")
                    if len(row) > 1 and isinstance(row[1], str)
                }
                if not {"model_provider"}.issubset(columns):
                    continue
                compatible_database_seen = True
                archived_expression = "COALESCE(archived, 0)" if "archived" in columns else "0"
                row = connection.execute(
                    f"""
                    SELECT
                        COUNT(*),
                        COALESCE(SUM(CASE WHEN model_provider = ? THEN 1 ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN model_provider <> ? THEN 1 ELSE 0 END), 0),
                        COALESCE(SUM(
                            CASE
                                WHEN model_provider <> ? AND {archived_expression} = 0 THEN 1
                                ELSE 0
                            END
                        ), 0)
                    FROM threads
                    """,
                    (current_provider, current_provider, current_provider),
                ).fetchone()
                provider_rows = connection.execute(
                    f"""
                    SELECT
                        model_provider,
                        COUNT(*),
                        COALESCE(SUM(
                            CASE WHEN {archived_expression} = 0 THEN 1 ELSE 0 END
                        ), 0),
                        COALESCE(SUM(
                            CASE WHEN {archived_expression} <> 0 THEN 1 ELSE 0 END
                        ), 0)
                    FROM threads
                    GROUP BY model_provider
                    ORDER BY COUNT(*) DESC, model_provider ASC
                    """
                ).fetchall()
        except (OSError, sqlite3.Error):
            if compatible_database_seen:
                empty_report["probe"] = "failed"
            continue

        if row is None:
            continue
        threads_total, current_count, other_count, active_other_count = (int(value) for value in row)
        report = {
            "probe": "ok",
            "database_path": _display_codex_home_path(database_path, codex_home),
            "database_read_only": True,
            "current_provider": current_provider,
            "threads_total": threads_total,
            "threads_current_provider": current_count,
            "threads_other_providers": other_count,
            "active_threads_other_providers": active_other_count,
            "provider_counts": [
                {
                    "provider": provider_id if isinstance(provider_id, str) else "<unset>",
                    "threads_total": int(total),
                    "threads_unarchived": int(unarchived),
                    "threads_archived": int(archived),
                }
                for provider_id, total, unarchived, archived in provider_rows
            ],
        }
        if active_other_count:
            finding_code = "history.provider_mismatch"
            cause_confirmed = finding_code in confirmed_causes
            findings.append(
                finding(
                    finding_code,
                    "warning",
                    (
                        "历史任务不可见的根因已由用户确认"
                        if cause_confirmed
                        else "部分历史任务仍绑定其他 Provider"
                    ),
                    (
                        f"用户已明确确认：这 {active_other_count} 个未归档任务的 model_provider 与当前 Provider 不一致，就是本次历史任务不可见的根因。自动检查本身只证明绑定差异；根因结论来自用户对本次现象的确认。"
                        if cause_confirmed
                        else f"只读检查发现 {active_other_count} 个未归档任务的 model_provider 与当前 Provider 不同；在会按 Provider 过滤任务的版本中，它们可能不出现在当前列表里。"
                    ),
                    (
                        "保持数据库只读。任何未来修复都必须先退出相关 Codex 进程，完整备份数据库及 WAL/SHM 旁路文件，展示精确行数和字段 diff，并再次取得明确确认。"
                        if cause_confirmed
                        else "先确认任务文件仍在，再完整备份数据库和 WAL/SHM 旁路文件。首版只解释和统计，不会自动更新任何任务记录。"
                    ),
                    status="confirmed" if cause_confirmed else "open",
                )
            )
        return report

    if compatible_database_seen:
        empty_report["probe"] = "failed"
    return empty_report
