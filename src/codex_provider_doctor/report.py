from __future__ import annotations

from typing import Any

from codex_provider_doctor.common import MODEL_REPORT_FIELDS


ENGLISH_FINDINGS: dict[str, tuple[str, str, str]] = {
    "provider.missing": (
        "The active provider is missing",
        "model_provider points to an ID that has no matching model_providers table.",
        "Add the provider table or select an existing provider ID.",
    ),
    "provider.auth.openai_with_env_key": (
        "OpenAI authentication will ignore the provider environment variable",
        "This provider sets both requires_openai_auth = true and env_key; Codex ignores env_key in this combination.",
        "For a provider-specific API key, remove or disable requires_openai_auth. Use true only for a proxy that actually expects OpenAI authentication.",
    ),
    "provider.auth.multiple_methods": (
        "The provider configures mutually exclusive authentication methods",
        "A clear conflict was found: requires_openai_auth ignores env_key; env_key competes with experimental_bearer_token; command authentication cannot be combined with another provider authentication field.",
        "Remove the explicit conflict. Do not automatically classify the version-sensitive requires_openai_auth plus experimental_bearer_token combination as the same error.",
    ),
    "provider.auth.direct_token": (
        "A direct bearer token is present in the config file",
        "experimental_bearer_token is configured; its value was not read or reported.",
        "Prefer env_key or a command credential helper, then rotate any token stored in plaintext.",
    ),
    "provider.auth.openai_with_direct_token": (
        "The dual-authentication intent is unverified",
        "The active provider sets requires_openai_auth = true plus an explicit third-party token. This retains the official account state while the explicit token takes precedence for provider requests, but the doctor cannot infer user intent without confirmation.",
        "When the user explicitly wants to keep the official sign-in, record it with --problem keep-official-login or --acknowledge provider.auth.openai_with_direct_token. Keep plaintext-token risk as a separate warning.",
    ),
    "provider.auth.requires_openai_auth_misplaced": (
        "requires_openai_auth is in the wrong table",
        "A top-level requires_openai_auth value does not configure the active provider.",
        "For the custom third-party dual-authentication design, move it under [model_providers.<active-id>]. Do not apply the pattern to the built-in OpenAI provider or stack it on an existing env_key/auth method.",
    ),
    "provider.auth.env_missing": (
        "The provider API key environment variable is not set",
        "env_key names a variable, but that variable is absent or empty in the doctor process.",
        "Set the variable in the environment that launches Codex, then restart Codex. Do not put the secret value in screenshots or reports.",
    ),
    "catalog.file_missing": (
        "The model catalog file is missing",
        "The effective model_catalog_json path does not exist.",
        "Confirm the winning config layer and point model_catalog_json to the real catalog file.",
    ),
    "catalog.not_regular_file": (
        "The model catalog path is not a regular file",
        "The effective model_catalog_json path exists, but it is not a readable JSON file.",
        "Point model_catalog_json to the actual model catalog JSON file selected by the winning config layer.",
    ),
    "catalog.invalid_json": (
        "The model catalog is not valid JSON",
        "The catalog could not be parsed.",
        "Fix the JSON syntax and rerun the doctor without sharing files that may contain secrets.",
    ),
    "catalog.model_missing": (
        "The active model is missing from the catalog",
        "The effective model value does not match any models[].slug entry.",
        "Make the model value and catalog slug match exactly, including case and version suffixes.",
    ),
    "catalog.root_not_object": (
        "The model catalog root must be a JSON object",
        "A valid Codex model catalog uses an object containing a models array.",
        "Wrap the catalog entries in an object with a models array.",
    ),
    "catalog.models_not_array": (
        "The model catalog models value must be an array",
        "The JSON parsed, but its models field has the wrong type.",
        "Change models to a JSON array of model objects.",
    ),
    "catalog.model_duplicate": (
        "The active model slug is duplicated in the catalog",
        "More than one models entry matches the effective model value, so the active metadata is ambiguous.",
        "Keep exactly one catalog entry for the active slug.",
    ),
    "catalog.display_name_unclear": (
        "The active model lacks a clear display name",
        "The matching catalog entry has no non-empty display_name, so the model picker may show only an unclear slug.",
        "Add a short, recognizable display_name to the effective catalog entry, restart Codex, and check a new task.",
    ),
    "compat.deepseek_direct_tools.mismatch": (
        "The third-party Responses model differs on fields that need attention",
        "The selected dated case recommends changing supports_search_tool or use_responses_lite. tool_mode is reviewed only when direct tools, skills, or Chrome show symptoms.",
        "Back up the catalog, review suggested_changes, and do not disable top-level web_search because of supports_search_tool. Restart Codex and test each tool surface separately after any edit.",
    ),
    "compat.chrome.exposure_mode_unverified": (
        "supports_search_tool = true does not determine Chrome exposure by itself",
        "Under the official Codex source as of 2026-08-05, this field permits Deferred exposure only when namespace tools are also enabled; otherwise the Direct branch is used. Tool declarations and the live task tool list remain separate evidence.",
        "Check namespace-tool capability, tool_search, and the Chrome tool in a new task on the installed Codex version. Only after runtime evidence confirms a deferred-discovery incompatibility should a backed-up catalog experiment be considered. Do not change top-level web_search or reinstall a plugin because the CLI inventory failed.",
    ),
    "compat.rule_version_differs": (
        "The selected compatibility rule was observed on a different Codex version",
        "The rule remains a troubleshooting clue, but its original version boundary does not match this installation.",
        "Re-test all affected tools on the current version and do not treat the old combination as a permanent default.",
    ),
    "runtime.codex.not_found": (
        "The Codex command was not found",
        "Read-only login and plugin probes could not run.",
        "Put Codex CLI on PATH, or use --no-command-checks for file-only diagnostics.",
    ),
    "runtime.version_probe_failed": (
        "The Codex version could not be read",
        "codex --version did not return a recognizable version; raw output was discarded.",
        "Run codex --version directly and update Codex if the command is broken.",
    ),
    "auth.login_probe_failed": (
        "The Codex login method could not be confirmed",
        "codex login status did not succeed; raw output was discarded.",
        "Run codex login status directly and confirm the active sign-in method.",
    ),
    "auth.login_not_confirmed": (
        "No usable Codex login state was confirmed",
        "The login result was not clearly ChatGPT, API key, or access token.",
        "Run codex login. Do not manually copy, overwrite, or publish auth.json.",
    ),
    "plugins.probe_failed": (
        "The CLI plugin probe could not verify runtime state",
        "codex plugin list --json did not succeed; raw output was discarded. This means the CLI inventory is unavailable; it does not prove that a plugin is absent, disabled, or broken.",
        "Check the Settings or Plugins page and a live invocation first. If either confirms the plugin works, do not reinstall it or clear caches.",
    ),
    "plugins.marketplace_snapshot_invalid": (
        "The CLI plugin probe could not verify runtime state",
        "codex plugin list --json failed because a marketplace directory lacks a manifest supported by that command. Raw paths and command output were discarded. This does not prove that a plugin is absent or broken.",
        "Check the Settings or Plugins page and a live invocation first. If the UI or runtime confirms the plugin works, do not reinstall it or clear caches. Repair the marketplace only when the UI and runtime also fail, and back up before clearing caches.",
    ),
    "plugins.invalid_output": (
        "The CLI plugin probe returned an unrecognized status",
        "The plugin command did not return a supported JSON inventory; raw output was discarded. This means the CLI inventory could not be parsed; it does not prove that a plugin is unavailable.",
        "Check the Settings or Plugins page and a live invocation first. If both work, treat this as a CLI compatibility gap; continue repair only when runtime behavior also fails.",
    ),
    "plugins.chrome.not_installed": (
        "The CLI inventory did not confirm Chrome as installed",
        "The successful CLI inventory did not contain an installed Chrome entry, but this remains lower-priority evidence than Settings or a live invocation.",
        "Check the Plugins page and try a live invocation first. Install or repair Chrome only when stronger evidence also confirms it is unavailable.",
    ),
    "plugins.chrome.disabled": (
        "The CLI inventory reports Chrome as disabled",
        "The CLI inventory marks Chrome disabled, but this remains lower-priority evidence than Settings or a live invocation.",
        "Confirm the state in Plugins and with a live invocation before changing it. If both fail, enable Chrome, restart Codex completely, and open a new task.",
    ),
    "plugins.feature.apps_disabled": (
        "App integrations are disabled",
        "features.apps = false disables app and connector integrations used by plugins.",
        "Enable features.apps in a user-level config, restart Codex, and open a new task.",
    ),
    "plugins.feature.remote_plugin_disabled": (
        "The remote plugin catalog is disabled",
        "features.remote_plugin = false can prevent the remote plugin directory from loading.",
        "Enable features.remote_plugin when you want to browse or use the remote plugin catalog.",
    ),
    "project.config_skipped_untrusted": (
        "Project config was found but skipped",
        "Codex ignores project-scoped .codex/config.toml layers when the project is untrusted.",
        "Keep the project untrusted unless you have reviewed it; trust it only when you intend its config, hooks, and rules to load.",
    ),
    "project.config.ignored_keys": (
        "Codex ignores machine-level keys in project config",
        "A trusted project config contains provider, authentication, profile, notification, or telemetry keys that project scope cannot override.",
        "Move those keys to the user-level config; keep only project-scoped settings in .codex/config.toml.",
    ),
    "config.invalid_toml": (
        "A Codex config layer is not valid TOML",
        "The layer could not be parsed, so it was not applied. File contents and the failing line were not copied into the report.",
        "Fix the TOML syntax in the reported file, then rerun the doctor.",
    ),
    "config.profile_missing": (
        "The requested Codex profile file is missing",
        "A profile was selected, but its <profile>.config.toml file does not exist.",
        "Confirm the profile name or create the matching profile file under CODEX_HOME.",
    ),
    "compact.limit_not_below_window": (
        "The automatic compact limit is not below the effective context window",
        "Automatic compaction needs a trigger threshold lower than the usable context window.",
        "Set the top-level or catalog compact limit to a verified lower value with safety margin.",
    ),
    "history.provider_mismatch": (
        "Some history entries are still bound to another provider",
        "The read-only probe found unarchived threads whose model_provider differs from the active provider. Builds that filter history by provider may hide those threads from the current list.",
        "First confirm the rollout files still exist, then back up the database and its WAL/SHM sidecars. This version reports the mismatch but never updates thread rows.",
    ),
}


ENGLISH_MANUAL_CHECKS = {
    "chrome.same_profile": "Use the same Chrome profile where the ChatGPT extension is installed and enabled.",
    "chrome.computer_use_settings": "Confirm the target site is not blocked in ChatGPT/Codex Computer Use settings.",
    "chrome.new_task": "After config or plugin changes, restart Codex completely and open a new task; old tasks can retain an old tool list.",
    "chrome.separate_acceptance": "Test Chrome, Web Search, and other plugins separately; one passing check does not prove the others work.",
    "plugins.supported_surface": "Use the ChatGPT desktop app or Codex CLI for plugins; plugins are not available in the IDE extension.",
    "plugins.connector_auth": "A plugin can still require connector or MCP authorization after installation and enablement.",
    "chrome.google_chrome_only": "The official Chrome extension currently supports Google Chrome, not other Chromium-based browsers.",
}


def manual_checks() -> list[dict[str, str]]:
    return [
        {
            "code": "chrome.same_profile",
            "status": "manual",
            "instruction": "确认当前使用的 Chrome Profile 正是安装并启用 ChatGPT 扩展的 Profile。",
        },
        {
            "code": "chrome.computer_use_settings",
            "status": "manual",
            "instruction": "在 ChatGPT/Codex 设置的 Computer Use 中确认目标站点没有被阻止。",
        },
        {
            "code": "chrome.new_task",
            "status": "manual",
            "instruction": "配置或插件变化后完全重启 Codex，并新建任务测试；旧任务可能保留旧工具列表。",
        },
        {
            "code": "chrome.separate_acceptance",
            "status": "manual",
            "instruction": "分别测试 Chrome、Web Search 和其他插件，不用其中一项成功代替全部验收。",
        },
        {
            "code": "plugins.supported_surface",
            "status": "manual",
            "instruction": "插件请在 ChatGPT 桌面端或 Codex CLI 使用；IDE 扩展当前不支持插件。",
        },
        {
            "code": "plugins.connector_auth",
            "status": "manual",
            "instruction": "插件安装并开启后，仍要确认它依赖的连接器或 MCP 已完成授权。",
        },
        {
            "code": "chrome.google_chrome_only",
            "status": "manual",
            "instruction": "官方 Chrome 扩展当前只支持 Google Chrome，不支持其他 Chromium 浏览器。",
        },
    ]


def report_origins(config: dict[str, Any], origins: dict[str, str]) -> dict[str, str]:
    keys = {
        "model",
        "model_provider",
        "model_catalog_json",
        "web_search",
        "cli_auth_credentials_store",
        "model_context_window",
        "model_auto_compact_token_limit",
        "model_auto_compact_token_limit_scope",
    }
    provider_id = config.get("model_provider", "openai")
    provider_prefix = f"model_providers.{provider_id}."
    return {
        key: source
        for key, source in origins.items()
        if key in keys or key.startswith(provider_prefix)
    }


def localize_report(report: dict[str, Any], language: str) -> dict[str, Any]:
    if language != "en":
        return report
    for item in report["findings"]:
        translated = ENGLISH_FINDINGS.get(item["code"])
        if translated:
            item["title"], item["message"], item["remedy"] = translated
        if (
            item["code"] == "provider.auth.openai_with_direct_token"
            and item.get("status") == "acknowledged"
        ):
            item["title"] = "The dual-authentication configuration is acknowledged as intentional"
            item["message"] = (
                "The user explicitly confirmed the design intent: requires_openai_auth = true under the active model_providers table retains the official ChatGPT/Codex account state, while the explicit bearer token takes precedence for third-party provider requests. Actual plugin availability still requires separate runtime verification."
            )
            item["remedy"] = (
                "Keep the dual-authentication configuration, test official sign-in and third-party model requests separately, and keep plaintext-token risk as an independent warning."
            )
        if (
            item["code"] == "history.provider_mismatch"
            and item.get("status") == "confirmed"
        ):
            item["title"] = "The history visibility root cause is user-confirmed"
            item["message"] = (
                "The user explicitly confirmed that the unarchived threads bound to another provider caused the current history-visibility problem. The automatic probe proves the binding mismatch; the causal conclusion comes from the user's confirmation for this incident."
            )
            item["remedy"] = (
                "Keep the database read-only. Any future repair must first stop relevant Codex processes, back up the database plus WAL/SHM sidecars, show the exact row count and field diff, and obtain a separate explicit confirmation."
            )
        if (
            item["code"] == "provider.auth.direct_token"
            and report["provider"].get("requires_openai_auth") is True
        ):
            item["remedy"] = (
                "If official sign-in is intentionally retained as a separate state while third-party requests use an explicit token, preserve behavior until version-specific tests finish. Then migrate to a credential method that does not store the token in plaintext and rotate the old token."
            )
    for check in report["manual_checks"]:
        translated = ENGLISH_MANUAL_CHECKS.get(check["code"])
        if translated:
            check["instruction"] = translated
    return report


def _value(value: Any, empty: str) -> str:
    if value is None:
        return empty
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _layer_state(layer: dict[str, Any], language: str) -> str:
    if language == "en":
        if layer["applied"]:
            return "applied"
        return "skipped" if layer["exists"] else "not found"
    if layer["applied"]:
        return "已加载"
    return "已发现但未应用" if layer["exists"] else "不存在"


def _finding_sort_key(item: dict[str, Any]) -> int:
    if item.get("severity") == "error":
        return 0
    if item.get("status") == "confirmed" and item.get("category") == "diagnostic":
        return 1
    if item.get("code") == "plugins.feature.apps_disabled":
        return 2
    if item.get("code") == "plugins.feature.remote_plugin_disabled":
        return 3
    if item.get("code") == "compat.deepseek_direct_tools.mismatch":
        return 4
    if item.get("severity") == "warning" and item.get("category") == "diagnostic":
        return 5
    if item.get("severity") == "warning" and item.get("category") == "security":
        return 6
    if item.get("severity") == "warning":
        return 7
    if item.get("status") == "acknowledged":
        return 8
    if item.get("category") == "intent":
        return 9
    if item.get("category") == "verification":
        return 10
    return 11


def _compatibility_reason(reason: Any, language: str) -> str:
    labels = {
        "en": {
            "built_in_openai_provider": "the built-in OpenAI provider is selected",
            "provider_missing": "the selected provider is unavailable",
            "provider_wire_api_not_responses": "the selected provider is not using the Responses API",
            "selected_model_unavailable": "the selected catalog model is unavailable",
            "selected_model_outside_rule_scope": "the selected model is not a third-party DeepSeek model",
        },
        "zh-CN": {
            "built_in_openai_provider": "当前使用内置 OpenAI Provider",
            "provider_missing": "当前选中的 Provider 不可用",
            "provider_wire_api_not_responses": "当前选中的 Provider 不是 Responses 接口",
            "selected_model_unavailable": "当前活动模型目录条目不可用",
            "selected_model_outside_rule_scope": "当前活动模型不是第三方 DeepSeek 模型",
        },
    }
    fallback = "the selected scope does not match" if language == "en" else "当前范围不匹配"
    return labels[language].get(str(reason), fallback)


def _symptom_assessment_label(assessment: Any, language: str) -> str:
    labels = {
        "en": {
            "direct_namespace_branch_forced": "the catalog field forces the Direct namespace branch; live Chrome exposure is unverified",
            "exposure_mode_runtime_dependent": "Direct versus Deferred remains runtime-dependent",
            "not_indicated_by_static_field": "not indicated by this static field",
            "field_unavailable": "the catalog field is unavailable",
            "not_applicable": "not applicable to the selected model or provider",
        },
        "zh-CN": {
            "direct_namespace_branch_forced": "该字段会让 namespace 分支进入 Direct；Chrome 实际暴露仍待核验",
            "exposure_mode_runtime_dependent": "Direct 或 Deferred 仍取决于运行时条件",
            "not_indicated_by_static_field": "该静态字段未指向兼容性问题",
            "field_unavailable": "模型目录字段不可用",
            "not_applicable": "不适用于当前模型或 Provider",
        },
    }
    fallback = "unknown" if language == "en" else "未知"
    return labels[language].get(str(assessment), fallback)


def _primary_diagnostic(findings: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in findings
            if item.get("severity") in {"error", "warning"}
            and item.get("category") == "diagnostic"
        ),
        None,
    )


def _finding_label(item: dict[str, Any], language: str) -> str:
    if item.get("status") == "confirmed" and item.get("category") == "diagnostic":
        return "CONFIRMED ROOT CAUSE" if language == "en" else "已确认根因"
    if item.get("status") == "acknowledged" and item.get("intentional") is True:
        return "ACKNOWLEDGED/INTENTIONAL" if language == "en" else "已确认意图"
    if item.get("status") == "unverified":
        return "UNVERIFIED" if language == "en" else "未核验"
    if language == "en":
        return str(item.get("severity", "info")).upper()
    return {"error": "错误", "warning": "警告", "info": "提示"}.get(
        str(item.get("severity")), str(item.get("severity"))
    )


def _solution_status_label(status: Any, language: str) -> str:
    labels = {
        "en": {
            "configured_with_security_warning": "configured; security warning remains",
            "configured_login_unverified_with_security_warning": "provider configured; official sign-in unverified; security warning remains",
            "configured_official_login_not_confirmed_with_security_warning": "provider configured; official sign-in not confirmed; security warning remains",
            "configured_intent_unverified_with_security_warning": "dual-authentication intent unverified; security warning remains",
            "needs_configuration": "configuration required",
            "needs_auth_method_transition": "authentication method transition required",
            "not_applicable_builtin_provider": "not applicable to the built-in provider",
            "configured": "configured",
            "needs_catalog_change": "catalog change required",
            "needs_catalog_match": "catalog match required",
            "confirmed_root_cause": "confirmed root cause",
            "binding_mismatch_detected": "provider mismatch detected",
            "no_provider_mismatch_detected": "no provider mismatch detected",
            "history_not_checked": "history binding not checked",
            "installation_present_runtime_unverified": "installation found; runtime unverified",
            "installation_present": "installation found",
            "plugin_features_disabled": "plugin features disabled",
            "skill_installation_not_found": "skill installation not found",
            "skill_installation_unverified": "skill installation only partially verified",
            "direct_namespace_branch_runtime_unverified": "Chrome availability needs a live check",
            "exposure_mode_runtime_unverified": "Chrome availability needs a live check",
            "remote_plugin_directory_disabled_runtime_unverified": "remote plugin directory is off; impact needs confirmation",
            "runtime_verification_required": "live verification required",
        },
        "zh-CN": {
            "configured_with_security_warning": "配置正确；仍有安全警告",
            "configured_login_unverified_with_security_warning": "Provider 配置正确；官方登录待核验；仍有安全警告",
            "configured_official_login_not_confirmed_with_security_warning": "Provider 配置正确；未确认官方登录；仍有安全警告",
            "configured_intent_unverified_with_security_warning": "检测到双认证组合；意图待确认；仍有安全警告",
            "needs_configuration": "需要配置",
            "needs_auth_method_transition": "需要迁移认证方式",
            "not_applicable_builtin_provider": "不适用于内置 Provider",
            "configured": "配置正确",
            "needs_catalog_change": "需要修改模型目录",
            "needs_catalog_match": "需要修正目录匹配",
            "confirmed_root_cause": "已确认根因",
            "binding_mismatch_detected": "已发现 Provider 绑定差异",
            "no_provider_mismatch_detected": "未发现 Provider 绑定差异",
            "history_not_checked": "历史 Provider 绑定尚未核验",
            "installation_present_runtime_unverified": "已发现安装；运行状态待核验",
            "installation_present": "已发现安装",
            "plugin_features_disabled": "插件能力被关闭",
            "skill_installation_not_found": "未发现本地 Skill",
            "skill_installation_unverified": "Skill 安装仅部分核验",
            "direct_namespace_branch_runtime_unverified": "Chrome 是否可用待实际验证",
            "exposure_mode_runtime_unverified": "Chrome 是否可用待实际验证",
            "remote_plugin_directory_disabled_runtime_unverified": "远程插件目录已关闭；影响待确认",
            "runtime_verification_required": "需要实际验证",
        },
    }
    return labels[language].get(str(status), str(status))


SOLUTION_PRESENTATION: dict[str, dict[str, dict[str, Any]]] = {
    "en": {
        "keep-official-login": {
            "controls": (
                "Official account state: the Codex sign-in session.",
                "Third-party request authentication: the active Provider ({provider_id}).",
                "Credential-storage risk: separate from whether the official account stays signed in.",
            ),
            "goal": "Keep the official account signed in while third-party requests use the intended credential, with storage risk handled separately.",
            "actions": (
                "Keep or confirm the official sign-in; do not overwrite the login cache.",
                "Use one request-authentication method on a custom third-party Provider; back up first if an existing method must be migrated.",
                "Test official sign-in, one third-party request, and one official-plugin action separately.",
            ),
            "verification": "All three checks pass independently; one passing check does not prove the others.",
        },
        "plugins-or-skills-unavailable": {
            "controls": (
                "Skill installation: local Skill directories.",
                "Official plugin availability: Plugins/Settings and App integration switches.",
                "Actual use: connector authorization plus the tool list loaded into a new task.",
            ),
            "goal": "Skills remain installed, official plugins are enabled and authorized, and the expected tools appear in a new task.",
            "actions": (
                "Confirm the Skill installation and plugin enablement in the active Codex environment.",
                "Complete connector authorization, restart Codex, and open a new task.",
                "Run one real action before reinstalling plugins or clearing caches.",
            ),
            "verification": "The new task shows both the expected Skill and plugin tool, and one real invocation succeeds.",
        },
        "model-name-incorrect": {
            "controls": (
                "Catalog name: the active model entry for {model_slug}.",
                "Windows picker label: the Desktop selector, which the doctor cannot observe automatically.",
                "Actual routed model: the selected model and Provider plus a real request; the UI label is not proof.",
            ),
            "goal": "The catalog is correct, the request reaches the intended model, and Desktop shows the clearest label the current product supports.",
            "actions": (
                "Correct the catalog only when the selected model does not match one entry or its display name is blank.",
                "When the catalog is already valid, stop editing JSON or clearing caches; use the config switcher, CLI, or separate Profiles.",
                "Verify the actual model with a real request; treat an app patch as a separately approved experiment.",
            ),
            "verification": "Compare the catalog, App Server list, Desktop picker, and one real request separately.",
        },
        "history-missing": {
            "controls": (
                "Current task-list context: the active Provider ({current_provider}).",
                "Stored task ownership: the Provider saved when each task was created.",
                "Visibility: Provider filtering or an all-Provider view in the installed Codex build.",
            ),
            "goal": "Recover visibility without writing the task database; migrate bindings only as a separately approved last resort.",
            "actions": (
                "Confirm the active Codex home/Profile and the read-only Provider counts.",
                "Switch to the stored Provider, use an all-Provider view, or update Codex before changing storage.",
                "Only as a last resort, back up the database plus WAL/SHM and obtain another explicit confirmation.",
            ),
            "verification": "The visible task count matches the read-only aggregate after switching Provider or view.",
        },
        "chrome-unavailable": {
            "controls": (
                "App integration: feature switches and Plugins/Settings.",
                "Model tool loading: selected-model capability metadata plus Codex tool-loading behavior.",
                "Browser bridge: Chrome Profile, connector authorization, site rules, and the new-task tool list.",
            ),
            "goal": "The Chrome tool appears in a new task and one minimal real invocation succeeds.",
            "actions": (
                "Confirm App integration, plugin enablement, connector authorization, and the correct Chrome Profile.",
                "Open a new task and check whether the Chrome tool is actually present.",
                "Run one real Chrome action before reinstalling anything or changing unrelated search settings.",
            ),
            "verification": "The new-task tool list contains Chrome and one minimal smoke test succeeds.",
        },
    },
    "zh-CN": {
        "keep-official-login": {
            "controls": (
                "官方账号是否还登录：由 Codex 自身登录会话控制。",
                "第三方接口请求用什么凭据：由当前 Provider（{provider_id}）控制。",
                "凭据是否明文保存：这是独立安全风险，不等于官方登录状态。",
            ),
            "goal": "官方账号保持登录，第三方请求使用预期凭据，凭据存储风险单独处理。",
            "actions": (
                "保持或确认官方登录，不要覆盖登录缓存。",
                "自定义第三方 Provider 只保留一种请求认证方式；已有方式需要迁移时先备份。",
                "分别测试官方登录、一次第三方模型请求和一次官方插件调用。",
            ),
            "verification": "三项分别通过；其中一项成功不能代替另外两项。",
        },
        "plugins-or-skills-unavailable": {
            "controls": (
                "Skill 是否仍安装：由本地 Skill 目录控制。",
                "官方插件是否可用：由 Plugins/Settings 和 App 集成开关控制。",
                "是否真正能调用：由连接器授权和新任务加载到的工具列表控制。",
            ),
            "goal": "Skill 仍安装，官方插件已启用并授权，而且目标工具在新任务中实际出现。",
            "actions": (
                "确认当前 Codex 环境中的 Skill 安装和插件启用状态。",
                "完成连接器授权，完全重启 Codex，并新建任务。",
                "先做一次真实调用，再考虑重装插件或清缓存。",
            ),
            "verification": "新任务同时出现目标 Skill 和插件工具，并且一次真实调用成功。",
        },
        "model-name-incorrect": {
            "controls": (
                "模型目录中的基础名称：由当前模型 {model_slug} 对应的目录条目控制。",
                "Windows 下拉框最终显示：由 Desktop 选择器控制，doctor 无法自动观察。",
                "真正调用哪个模型：由当前模型、Provider 和真实请求共同确认；界面标签不能证明。",
            ),
            "goal": "模型目录正确、真实请求进入目标模型，Desktop 显示当前版本能支持的最清楚名称。",
            "actions": (
                "只有当前模型无法唯一匹配目录，或显示名称为空时，才修改模型目录。",
                "目录已经正确时，不再改 JSON 或反复清缓存；使用配置切换器、CLI 或独立 Profile。",
                "用真实请求确认实际模型；应用补丁只能作为另行确认的实验方案。",
            ),
            "verification": "分别核对模型目录、App Server 列表、Desktop 下拉框和一次真实请求。",
        },
        "history-missing": {
            "controls": (
                "当前任务列表环境：由当前 Provider（{current_provider}）控制。",
                "历史任务属于哪个 Provider：由任务创建时保存的 Provider 绑定控制。",
                "任务是否显示：由当前版本的 Provider 过滤或全部 Provider 视图控制。",
            ),
            "goal": "优先不写数据库就恢复可见性；只有最后确需迁移绑定时才单独确认。",
            "actions": (
                "确认当前 Codex 目录/Profile，以及只读统计到的 Provider 数量。",
                "先切回旧 Provider、使用全部 Provider 视图或升级 Codex，不要先改数据库。",
                "只有最后确需迁移时，才完整备份数据库及 WAL/SHM，并再次明确确认。",
            ),
            "verification": "切换 Provider 或视图后，可见任务数量与只读聚合数量一致。",
        },
        "chrome-unavailable": {
            "controls": (
                "App 集成是否开启：由功能开关和 Plugins/Settings 控制。",
                "模型怎样加载工具：由模型能力声明和 Codex 的工具加载方式共同控制。",
                "浏览器是否真正接通：由 Chrome Profile、连接器授权、站点限制和新任务工具列表控制。",
            ),
            "goal": "Chrome 工具在新任务中出现，并且一次最小真实调用成功。",
            "actions": (
                "确认 App 集成、插件启用、连接器授权和正确的 Chrome Profile。",
                "新建任务，确认 Chrome 工具是否真的出现。",
                "先做一次真实 Chrome 操作，再考虑重装插件或修改无关搜索设置。",
            ),
            "verification": "新任务工具列表中出现 Chrome，并且一次最小烟雾测试成功。",
        },
    },
}


def _solution_result(
    item: dict[str, Any],
    report: dict[str, Any],
    language: str,
) -> str:
    status = _solution_status_label(item.get("status"), language)
    problem_id = item.get("id")

    if problem_id == "plugins-or-skills-unavailable":
        count = report["skills"].get("total")
        count_text = str(count) if isinstance(count, int) else ("not verified" if language == "en" else "未核验")
        return (
            f"Status: {status}. Local Skills found: {count_text}; real plugin use still depends on a new task."
            if language == "en"
            else f"当前结论是“{status}”。本地 Skill 数量：{count_text}；插件能否调用仍以新任务为准。"
        )

    if problem_id == "model-name-incorrect":
        selected = report["catalog"].get("selected_model")
        display_name = selected.get("display_name") if isinstance(selected, dict) else None
        name_text = str(display_name).strip() if isinstance(display_name, str) and display_name.strip() else ("not confirmed" if language == "en" else "未确认")
        return (
            f"Status: {status}. Catalog display name: {name_text}; the Windows picker and actual request remain separate checks."
            if language == "en"
            else f"当前结论是“{status}”。目录显示名称：{name_text}；Windows 下拉框和真实请求仍需分开确认。"
        )

    if problem_id == "history-missing":
        affected = item.get("affected_unarchived_threads")
        affected_text = str(affected) if isinstance(affected, int) else ("not verified" if language == "en" else "未核验")
        return (
            f"Status: {status}. Unarchived tasks bound to another Provider: {affected_text}."
            if language == "en"
            else f"当前结论是“{status}”。绑定其他 Provider 的未归档任务：{affected_text}。"
        )

    summaries = {
        "en": {
            "keep-official-login": "Official sign-in, third-party request authentication, and credential storage were evaluated separately.",
            "chrome-unavailable": "Static configuration is only a clue; the new-task tool list and a real invocation decide the final result.",
        },
        "zh-CN": {
            "keep-official-login": "官方登录、第三方请求认证和凭据存储已经分开判断。",
            "chrome-unavailable": "静态配置只提供线索；新任务工具列表和真实调用才是最终结果。",
        },
    }
    summary = summaries[language].get(str(problem_id), str(item.get("diagnosis") or ""))
    return f"Status: {status}. {summary}" if language == "en" else f"当前结论是“{status}”。{summary}"


def _solution_presentation(
    item: dict[str, Any],
    report: dict[str, Any],
    language: str,
    *,
    details: bool,
) -> dict[str, Any]:
    problem_id = str(item.get("id"))
    template = SOLUTION_PRESENTATION[language].get(problem_id, {})
    values = {
        "provider_id": str(report["provider"].get("id") or "current"),
        "model_slug": str(report["effective"].get("model") or "current model"),
        "current_provider": str(
            report["history"].get("current_provider")
            or report["provider"].get("id")
            or "current"
        ),
    }

    def render(value: str) -> str:
        return value.format(**values)

    return {
        "controls": [render(value) for value in template.get("controls", ())],
        "goal": render(str(template.get("goal", ""))),
        "actions": (
            list(item.get("actions", []))
            if details
            else [render(value) for value in template.get("actions", ())]
        ),
        "verification": render(str(template.get("verification", ""))),
    }


def _append_solution_guides(
    lines: list[str],
    report: dict[str, Any],
    language: str,
    *,
    details: bool,
) -> None:
    items = report.get("solutions", {}).get("items", [])
    heading = (
        f"Action checklist ({len(items)} items)"
        if language == "en"
        else f"检查结果（{len(items)} 项）"
    )
    lines.extend(["", heading])
    for index, item in enumerate(items, start=1):
        status = _solution_status_label(item.get("status"), language)
        lines.append(f"{index}. {item['title']} [{status}]" if language == "en" else f"{index}. {item['title']}【{status}】")
        result = _solution_result(item, report, language)
        presentation = _solution_presentation(
            item,
            report,
            language,
            details=details,
        )
        controls = presentation["controls"]
        goal = presentation["goal"]
        verification = presentation["verification"]
        actions = presentation["actions"]
        if language == "en":
            lines.append(f"   Current result: {result}")
            lines.append("   Controlled by:")
            lines.extend(f"   - {control}" for control in controls)
            lines.append(f"   Desired state: {goal}")
            lines.append("   How to change:")
            lines.extend(
                f"   {action_index}. {action}"
                for action_index, action in enumerate(actions, start=1)
            )
            lines.append(f"   How to verify: {verification}")
            if details:
                lines.append(f"   Technical diagnosis: {item['diagnosis']}")
        else:
            lines.append(f"   当前结果：{result}")
            lines.append("   受什么控制：")
            lines.extend(f"   - {control}" for control in controls)
            lines.append(f"   目标状态：{goal}")
            lines.append("   怎么处理：")
            lines.extend(
                f"   {action_index}. {action}"
                for action_index, action in enumerate(actions, start=1)
            )
            lines.append(f"   怎么确认：{verification}")
            if details:
                lines.append(f"   技术判断：{item['diagnosis']}")
        if index != len(items):
            lines.append("")


def _finish_compact_report(
    lines: list[str],
    attention: list[dict[str, Any]],
    language: str,
) -> str:
    if attention:
        lines.extend(["", "Other findings requiring attention" if language == "en" else "其他需要处理"])
        for item in attention:
            lines.extend(
                [
                    f"[{_finding_label(item, language)}] {item['title']}" if language == "en" else f"【{_finding_label(item, language)}】{item['title']}",
                    f"  Action: {item['remedy']}" if language == "en" else f"  怎么处理：{item['remedy']}",
                ]
            )
    lines.extend(
        [
            "",
            "Use --details to view configuration layers, field origins, and complete diagnostic evidence."
            if language == "en"
            else "使用 --details 查看配置层、字段来源和完整诊断证据。",
            "This report is read-only. It did not modify Codex configuration."
            if language == "en"
            else "本报告只读，没有修改任何 Codex 配置。",
        ]
    )
    return "\n".join(lines) + "\n"


def render_human(report: dict[str, Any], language: str, *, details: bool = False) -> str:
    summary = report["summary"]
    effective = report["effective"]
    provider = report["provider"]
    catalog = report["catalog"]
    auth = report["auth"]
    plugins = report["plugins"]
    compact = report["compact"]
    history = report["history"]
    symptom_assessments = report["compatibility"].get("symptom_assessments", [])
    findings = sorted(report["findings"], key=_finding_sort_key)
    primary = _primary_diagnostic(findings)
    attention = [item for item in findings if item.get("severity") in {"error", "warning"}]
    context = [item for item in findings if item.get("severity") == "info"]
    intent = provider.get("authentication_intent")
    lines = ["Codex Provider Doctor", ""]

    if language == "en":
        lines.extend(
            [
                f"Overall: {summary['status'].upper()}",
                f"Errors: {summary['errors']}  Warnings: {summary['warnings']}  Info: {summary['info']}",
                f"Unverified: {summary['unverified']}  Acknowledged: {summary['acknowledged']}  Confirmed causes: {summary['confirmed_causes']}  Intentional: {summary['intentional']}",
                (
                    f"Confirmed root cause: {primary['title']}"
                    if primary and primary.get("status") == "confirmed"
                    else f"Primary diagnosis: {primary['title']}"
                    if primary
                    else "Primary diagnosis: no confirmed configuration fault was identified."
                ),
            ]
        )
        _append_solution_guides(lines, report, language, details=details)
        if not details:
            return _finish_compact_report(lines, attention, language)
        lines.extend(
            [
                "",
                "Effective configuration",
                f"- Model: {_value(effective['model'], '(not set)')}",
                f"- Provider: {_value(effective['model_provider'], '(not set)')}",
                f"- Model catalog: {_value(effective['model_catalog_json'], '(not configured)')}",
                f"- Catalog path exists: {_value(catalog['exists'], '(not configured)')}",
                f"- Catalog is a regular file: {_value(catalog['is_file'], '(not configured)')}",
                f"- Catalog JSON is valid: {_value(catalog['valid'], '(not checked)')}",
                f"- Catalog model count: {_value(catalog.get('model_count'), '(not checked)')}",
                f"- Web Search: {_value(effective['web_search'], '(not set)')} (separate from supports_search_tool)",
                f"- Codex version: {_value(report['runtime']['codex_version'], '(not checked)')}",
                "",
                "Configuration layers",
            ]
        )
        for layer in report["layers"]:
            lines.append(f"- [{_layer_state(layer, language)}; parse={layer['parse_status']}] {layer['kind']}: {layer['path']}")
        lines.extend(["", "Effective field sources"])
        lines.extend(f"- {key}: {source}" for key, source in sorted(effective["origins"].items()))
        intent_value = (
            "not applicable"
            if intent is None
            else "acknowledged / intentional"
            if intent.get("status") == "acknowledged"
            else "unverified"
        )
        lines.extend(
            [
                "",
                "Provider request authentication",
                f"- Endpoint host: {_value(provider['host'], '(built-in or not set)')}",
                f"- requires_openai_auth: {_value(provider['requires_openai_auth'], '(not set)')} (under [model_providers.{provider['id']}]; true retains the official account state)",
                f"- env_key: {_value(provider['env_key'], '(not set)')}",
                f"- env_key is set: {_value(provider['env_key_is_set'], '(not applicable)')}",
                f"- Explicit bearer token: {'configured (value not read)' if provider['direct_bearer_token_configured'] else 'not configured'}",
                f"- Authentication combination intent: {intent_value}",
                "",
                "Official ChatGPT/Codex sign-in state",
                f"- Login method: {_value(auth['login_method'], auth['login_probe'])}",
                f"- auth.json exists: {_value(auth['cache_exists'], '(unknown)')}",
                "- auth.json contents: not read",
                "",
                "Plugins and Chrome",
                f"- Plugin CLI probe: {plugins['probe']}",
                f"- Plugin inventory status: {plugins.get('inventory_status', 'unverified')}",
                f"- Plugin inventory count: {_value(plugins['inventory_count'], 'not available')}",
                f"- Chrome CLI inventory value: {_value(plugins['chrome']['enabled'], 'manual check required')}",
                "",
                "Task history",
                f"- Probe: {history['probe']}",
                f"- Database: {_value(history['database_path'], '(not found)')}",
                f"- Read-only: {_value(history['database_read_only'], '(unknown)')}",
                f"- Current provider: {_value(history['current_provider'], '(not set)')}",
                f"- All threads: {_value(history['threads_total'], '(not checked)')}",
                f"- Threads on another provider: {_value(history['threads_other_providers'], '(not checked)')}",
                f"- Unarchived threads on another provider: {_value(history['active_threads_other_providers'], '(not checked)')}",
            ]
        )
        if history.get("provider_counts"):
            lines.append("- Provider counts (aggregate only):")
            for group in history["provider_counts"]:
                lines.append(
                    f"  - {group['provider']}: total {group['threads_total']}, unarchived {group['threads_unarchived']}, archived {group['threads_archived']}"
                )
        lines.extend(
            [
                "",
                "Automatic compact",
                f"- Effective context window: {_value(compact['effective_context_window'], '(unknown)')}",
                f"- Compact limit: {_value(compact['auto_compact_token_limit'], '(unknown)')}",
                f"- Valid relationship: {_value(compact['valid'], '(not verifiable)')}",
            ]
        )
        if catalog.get("selected_model"):
            lines.extend(["", "Selected catalog model"])
            for field in MODEL_REPORT_FIELDS:
                lines.append(f"- {field}: {_value(catalog['selected_model'].get(field), '(not set)')}")
        if symptom_assessments:
            lines.extend(["", "Chrome / plugin compatibility triage"])
            for assessment in symptom_assessments:
                lines.extend(
                    [
                        "- Reported symptom: Chrome plugin unavailable",
                        f"- supports_search_tool: {_value(assessment['observed_supports_search_tool'], '(unavailable)')}",
                        f"- Assessment: {_symptom_assessment_label(assessment['assessment'], language)}",
                        "- Evidence type: static model-catalog field",
                        f"- Namespace-tools feature state: {assessment.get('namespace_tools_feature_state', 'not checked')}",
                        "- Live smoke test: not run by the doctor",
                        "- Boundary: plugin inventory, Settings visibility, and live invocation remain separate evidence; this field alone does not prove a unique root cause.",
                    ]
                )
        if report["compatibility"]["rules"]:
            lines.extend(["", "Compatibility rules"])
            for rule in report["compatibility"]["rules"]:
                lines.append(f"- {rule['id']} ({rule['scope']})")
                if rule.get("applicability") != "applicable":
                    reason = _compatibility_reason(rule.get("applicability_reason"), language)
                    lines.append(
                        f"  - Applicability: not applicable to the selected model or provider ({reason})."
                    )
                    lines.append(
                        "  - The selected model keeps its own value; official models can keep "
                        "supports_search_tool=true. No field change is suggested by this rule."
                    )
                    continue
                for assessment in rule.get("field_assessments", []):
                    observed = _value(assessment["observed"], "(missing)")
                    case_value = _value(assessment["case_value"], "(missing)")
                    if assessment["status"] == "aligned":
                        lines.append(f"  - {assessment['field']}: {observed} (matches the case)")
                    elif assessment["status"] == "review_if_symptomatic":
                        lines.append(f"  - {assessment['field']}: {observed} (case value {case_value}; review only if direct-tool symptoms exist)")
                    else:
                        lines.append(f"  - {assessment['field']}: {observed} -> {case_value} (suggested change)")
                lines.append("  This dated Responses-provider case is not a default for every third-party model, and supports_search_tool is not top-level web_search.")
        if attention:
            lines.extend(["", "Findings requiring attention"])
            for item in attention:
                lines.extend([f"[{_finding_label(item, language)}] {item['title']}", f"  {item['message']}", f"  Action: {item['remedy']}"])
        if context:
            lines.extend(["", "Information and verification status"])
            for item in context:
                lines.extend([f"[{_finding_label(item, language)}] {item['title']}", f"  {item['message']}", f"  Next: {item['remedy']}"])
        lines.extend(["", "Manual checks"])
        lines.extend(f"- {check['instruction']}" for check in report["manual_checks"])
        lines.extend(["", "This report is read-only. It did not modify Codex configuration."])
        return "\n".join(lines) + "\n"

    conclusion = (
        f"结论：发现 {summary['errors']} 个错误，{summary['warnings']} 个警告"
        if summary["errors"] or summary["warnings"]
        else "结论：未发现错误或警告"
    )
    if summary["info"]:
        conclusion += f"；另有 {summary['info']} 条信息（{summary['unverified']} 条未核验，{summary['acknowledged']} 条已确认意图）"
    if summary["confirmed_causes"]:
        conclusion += f"；已确认根因 {summary['confirmed_causes']} 项"
    primary_line = (
        f"已确认根因：{primary['title']}"
        if primary and primary.get("status") == "confirmed"
        else f"首要诊断：{primary['title']}"
        if primary
        else "首要诊断：未发现足以判定当前故障的配置证据。"
    )
    lines.extend(
        [
            conclusion,
            primary_line,
        ]
    )
    _append_solution_guides(lines, report, language, details=details)
    if not details:
        return _finish_compact_report(lines, attention, language)
    lines.extend(
        [
            "",
            "生效配置",
            f"- 模型：{_value(effective['model'], '未设置')}",
            f"- Provider：{_value(effective['model_provider'], '未设置')}",
            f"- 模型目录：{_value(effective['model_catalog_json'], '未配置')}",
            f"- 模型目录路径是否存在：{_value(catalog['exists'], '未配置')}",
            f"- 模型目录是否为普通文件：{_value(catalog['is_file'], '未配置')}",
            f"- 模型目录 JSON 是否有效：{_value(catalog['valid'], '未检查')}",
            f"- 模型目录条目数：{_value(catalog.get('model_count'), '未检查')}",
            f"- Web Search：{_value(effective['web_search'], '未设置')}（与 supports_search_tool 分开判断）",
            f"- Codex 版本：{_value(report['runtime']['codex_version'], '未检查')}",
            "",
            "配置层",
        ]
    )
    for layer in report["layers"]:
        lines.append(f"- 【{_layer_state(layer, language)}；解析：{layer['parse_status']}】{layer['kind']}：{layer['path']}")
    lines.extend(["", "关键字段来源"])
    lines.extend(f"- {key}：{source}" for key, source in sorted(effective["origins"].items()))
    intent_value = (
        "不适用"
        if intent is None
        else "已确认且有意"
        if intent.get("status") == "acknowledged"
        else "未核验"
    )
    lines.extend(
        [
            "",
            "Provider 请求认证",
            f"- 接口主机：{_value(provider['host'], '内置或未设置')}",
            f"- requires_openai_auth：{_value(provider['requires_openai_auth'], '未设置')}（位于 [model_providers.{provider['id']}]；为 true 时保留官方账户状态）",
            f"- env_key：{_value(provider['env_key'], '未设置')}",
            f"- env_key 是否已注入：{_value(provider['env_key_is_set'], '不适用')}",
            f"- 显式 Bearer Token：{'已配置（值未读取）' if provider['direct_bearer_token_configured'] else '未配置'}",
            f"- 认证组合意图：{intent_value}",
            "",
            "官方 ChatGPT/Codex 登录状态",
            f"- 登录方式：{_value(auth['login_method'], auth['login_probe'])}",
            f"- auth.json 是否存在：{_value(auth['cache_exists'], '未知')}",
            "- auth.json 内容：未读取",
            "",
            "插件与 Chrome",
            f"- 插件 CLI 探针：{plugins['probe']}",
            f"- 插件清单核验状态：{plugins.get('inventory_status', 'unverified')}",
            f"- 插件总数：{_value(plugins['inventory_count'], '不可用')}",
            f"- Chrome CLI 清单值：{_value(plugins['chrome']['enabled'], '需要人工确认')}",
            "",
            "历史任务",
            f"- 检测状态：{history['probe']}",
            f"- 任务数据库：{_value(history['database_path'], '未找到')}",
            f"- 数据库访问：{'只读' if history['database_read_only'] else '未知'}",
            f"- 当前 Provider：{_value(history['current_provider'], '未设置')}",
            f"- 全部任务：{_value(history['threads_total'], '未检查')}",
            f"- 绑定其他 Provider 的任务：{_value(history['threads_other_providers'], '未检查')}",
            f"- 其中未归档任务：{_value(history['active_threads_other_providers'], '未检查')}",
        ]
    )
    if history.get("provider_counts"):
        lines.append("- 按 Provider 分组（仅聚合）：")
        for group in history["provider_counts"]:
            lines.append(
                f"  - {group['provider']}：全部 {group['threads_total']}，"
                f"未归档 {group['threads_unarchived']}，已归档 {group['threads_archived']}"
            )
    lines.extend(
        [
            "",
            "自动 Compact",
            f"- 有效上下文窗口：{_value(compact['effective_context_window'], '未知')}",
            f"- 自动压缩阈值：{_value(compact['auto_compact_token_limit'], '未知')}",
            f"- 阈值关系是否有效：{_value(compact['valid'], '无法确认')}",
        ]
    )
    if catalog.get("selected_model"):
        lines.extend(["", "活动模型目录字段"])
        for field in MODEL_REPORT_FIELDS:
            lines.append(f"- {field}：{_value(catalog['selected_model'].get(field), '未设置')}")
    if symptom_assessments:
        lines.extend(["", "Chrome / 插件兼容性排查"])
        for assessment in symptom_assessments:
            lines.extend(
                [
                    "- 用户报告症状：Chrome 插件不可用",
                    f"- supports_search_tool：{_value(assessment['observed_supports_search_tool'], '不可用')}",
                    f"- 当前判断：{_symptom_assessment_label(assessment['assessment'], language)}",
                    "- 证据类型：模型目录静态字段",
                    f"- namespace-tools 功能状态：{assessment.get('namespace_tools_feature_state', '未检查')}",
                    "- 真实调用烟雾测试：诊断器未执行",
                    "- 证据边界：插件清单、设置页面和真实调用必须分开核对；这个字段本身不能证明唯一根因。",
                ]
            )
    if report["compatibility"]["rules"]:
        lines.extend(["", "兼容规则"])
        for rule in report["compatibility"]["rules"]:
            lines.append(f"- {rule['id']}（{rule['scope']}）")
            if rule.get("applicability") != "applicable":
                reason = _compatibility_reason(rule.get("applicability_reason"), language)
                lines.append(f"  - 适用性：不适用于当前选中的模型或 Provider（{reason}）。")
                lines.append(
                    "  - 当前模型保持自身值；官方模型可以保持自身的 supports_search_tool "
                    "值（包括 true），本规则不会给出字段修改建议。"
                )
                continue
            for assessment in rule.get("field_assessments", []):
                observed = _value(assessment["observed"], "缺失")
                case_value = _value(assessment["case_value"], "缺失")
                if assessment["status"] == "aligned":
                    lines.append(f"  - {assessment['field']}：{observed}（与案例一致）")
                elif assessment["status"] == "review_if_symptomatic":
                    lines.append(f"  - {assessment['field']}：{observed}（案例值 {case_value}；仅在直接工具出现症状时核对）")
                else:
                    lines.append(f"  - {assessment['field']}：{observed} → {case_value}（建议修改）")
            lines.append("  这是带日期、Codex 版本和第三方 Responses 接口边界的案例，不是所有第三方模型的默认值；supports_search_tool 也不等于顶层 web_search。")
    if attention:
        lines.extend(["", "需要处理"])
        for item in attention:
            lines.extend([f"【{_finding_label(item, language)}】{item['title']}", f"  {item['message']}", f"  怎么处理：{item['remedy']}"])
    if context:
        lines.extend(["", "信息与核验状态"])
        for item in context:
            lines.extend([f"【{_finding_label(item, language)}】{item['title']}", f"  {item['message']}", f"  下一步：{item['remedy']}"])
    lines.extend(["", "需要人工确认"])
    lines.extend(f"- {check['instruction']}" for check in report["manual_checks"])
    lines.extend(["", "本报告只读，没有修改任何 Codex 配置。"])
    return "\n".join(lines) + "\n"
