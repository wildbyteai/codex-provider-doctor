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
        "The provider requires official sign-in and also configures a direct bearer token",
        "This can be an intentional way to retain the official sign-in surface while supplying an explicit provider request token, but the behavior is version- and implementation-sensitive.",
        "Confirm that the combination is intentional and test sign-in, model requests, skills, and plugins on the current version before removing either field.",
    ),
    "provider.auth.requires_openai_auth_misplaced": (
        "requires_openai_auth is in the wrong table",
        "A top-level requires_openai_auth value does not configure the active provider.",
        "Move it under [model_providers.<active-id>] only when that provider really uses OpenAI authentication; otherwise remove it.",
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
        "The catalog differs from the observed Chrome compatibility combination",
        "This rule is one dated compatibility case, not a universal third-party provider default.",
        "Review the suggested changes after a backup, restart Codex, open a new task, and test Chrome, Web Search, and other plugins separately.",
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
        "Plugin installation state could not be read",
        "codex plugin list --json did not succeed; raw output was discarded.",
        "Confirm Chrome is installed and enabled in Plugins, then open a new task.",
    ),
    "plugins.marketplace_snapshot_invalid": (
        "A configured plugin marketplace snapshot could not be loaded",
        "Codex found a marketplace snapshot whose directory does not contain a supported manifest. Raw paths and command output were discarded.",
        "Refresh or reinstall that marketplace from Plugins. If the problem continues, back up and repair the marketplace cache before testing Chrome in a new task.",
    ),
    "plugins.invalid_output": (
        "Plugin status output could not be parsed",
        "The plugin command did not return expected JSON; raw output was discarded.",
        "Update Codex and retry, or verify Chrome manually in Plugins.",
    ),
    "plugins.chrome.not_installed": (
        "The Chrome plugin was not confirmed as installed",
        "No installed Chrome plugin was found in the plugin list.",
        "Install Chrome from the Plugins Directory and complete the browser extension setup.",
    ),
    "plugins.chrome.disabled": (
        "The Chrome plugin is disabled",
        "Chrome is installed but not enabled.",
        "Enable Chrome in Plugins, restart Codex completely, and open a new task.",
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
            item["code"] == "provider.auth.direct_token"
            and report["provider"].get("requires_openai_auth") is True
        ):
            item["remedy"] = (
                "If this setup intentionally keeps official sign-in while supplying a third-party request token, preserve behavior until you finish version-specific tests. Then migrate to a credential method that does not store the token in plaintext and rotate the old token."
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


def render_human(report: dict[str, Any], language: str) -> str:
    summary = report["summary"]
    effective = report["effective"]
    provider = report["provider"]
    catalog = report["catalog"]
    auth = report["auth"]
    plugins = report["plugins"]
    compact = report["compact"]
    history = report["history"]
    lines = ["Codex Provider Doctor", ""]

    if language == "en":
        lines.extend(
            [
                f"Overall: {summary['status'].upper()}",
                f"Errors: {summary['errors']}  Warnings: {summary['warnings']}",
                "",
                "Effective configuration",
                f"- Model: {_value(effective['model'], '(not set)')}",
                f"- Provider: {_value(effective['model_provider'], '(not set)')}",
                f"- Model catalog: {_value(effective['model_catalog_json'], '(not configured)')}",
                f"- Catalog path exists: {_value(catalog['exists'], '(not configured)')}",
                f"- Catalog is a regular file: {_value(catalog['is_file'], '(not configured)')}",
                f"- Catalog JSON is valid: {_value(catalog['valid'], '(not checked)')}",
                f"- Web Search: {_value(effective['web_search'], '(not set)')}",
                f"- Codex version: {_value(report['runtime']['codex_version'], '(not checked)')}",
                "",
                "Configuration layers",
            ]
        )
        for layer in report["layers"]:
            lines.append(
                f"- [{_layer_state(layer, language)}; parse={layer['parse_status']}] "
                f"{layer['kind']}: {layer['path']}"
            )
        lines.extend(["", "Effective field sources"])
        lines.extend(
            f"- {key}: {source}"
            for key, source in sorted(effective["origins"].items())
        )
        lines.extend(
            [
                "",
                "Provider authentication",
                f"- Endpoint host: {_value(provider['host'], '(built-in or not set)')}",
                f"- requires_openai_auth: {_value(provider['requires_openai_auth'], '(not set)')}",
                f"- env_key: {_value(provider['env_key'], '(not set)')}",
                f"- env_key is set: {_value(provider['env_key_is_set'], '(not applicable)')}",
                "",
                "Official login and plugins",
                f"- Login method: {_value(auth['login_method'], auth['login_probe'])}",
                f"- auth.json exists: {_value(auth['cache_exists'], '(unknown)')}",
                "- auth.json contents: not read",
                f"- Plugin probe: {plugins['probe']}",
                f"- Plugin inventory count: {_value(plugins['inventory_count'], 'not available')}",
                f"- Chrome: {_value(plugins['chrome']['enabled'], 'manual check required')}",
                "",
                "Task history",
                f"- Probe: {history['probe']}",
                f"- Database: {_value(history['database_path'], '(not found)')}",
                f"- Read-only: {_value(history['database_read_only'], '(unknown)')}",
                f"- Current provider: {_value(history['current_provider'], '(not set)')}",
                f"- Threads on another provider: {_value(history['threads_other_providers'], '(not checked)')}",
                f"- Unarchived threads on another provider: {_value(history['active_threads_other_providers'], '(not checked)')}",
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
                if field in catalog["selected_model"]:
                    lines.append(f"- {field}: {_value(catalog['selected_model'][field], '(not set)')}")
        if report["compatibility"]["rules"]:
            lines.extend(["", "Compatibility rules"])
            for rule in report["compatibility"]["rules"]:
                lines.append(f"- {rule['id']} ({rule['scope']})")
                if rule["suggested_changes"]:
                    lines.append("  Suggested changes (not applied automatically):")
                    for change in rule["suggested_changes"]:
                        lines.append(
                            f"  - {change['field']}: {_value(change['from'], '(missing)')} -> {_value(change['to'], '(missing)')}"
                        )
                lines.append("  This dated case is not a default for every third-party model.")
        if report["findings"]:
            lines.extend(["", "Findings"])
            for item in report["findings"]:
                lines.extend(
                    [
                        f"[{item['severity'].upper()}] {item['title']}",
                        f"  {item['message']}",
                        f"  Fix: {item['remedy']}",
                    ]
                )
        lines.extend(["", "Manual checks"])
        lines.extend(f"- {check['instruction']}" for check in report["manual_checks"])
        lines.extend(["", "This report is read-only. It did not modify Codex configuration."])
        return "\n".join(lines) + "\n"

    conclusion = (
        f"结论：发现 {summary['errors']} 个错误，{summary['warnings']} 个警告"
        if summary["errors"] or summary["warnings"]
        else "结论：未发现错误或警告"
    )
    lines.extend(
        [
            conclusion,
            "",
            "生效配置",
            f"- 模型：{_value(effective['model'], '未设置')}",
            f"- Provider：{_value(effective['model_provider'], '未设置')}",
            f"- 模型目录：{_value(effective['model_catalog_json'], '未配置')}",
            f"- 模型目录路径是否存在：{_value(catalog['exists'], '未配置')}",
            f"- 模型目录是否为普通文件：{_value(catalog['is_file'], '未配置')}",
            f"- 模型目录 JSON 是否有效：{_value(catalog['valid'], '未检查')}",
            f"- Web Search：{_value(effective['web_search'], '未设置')}（与 supports_search_tool 分开判断）",
            f"- Codex 版本：{_value(report['runtime']['codex_version'], '未检查')}",
            "",
            "配置层",
        ]
    )
    for layer in report["layers"]:
        lines.append(
            f"- 【{_layer_state(layer, language)}；解析：{layer['parse_status']}】"
            f"{layer['kind']}：{layer['path']}"
        )
    lines.extend(["", "关键字段来源"])
    lines.extend(
        f"- {key}：{source}"
        for key, source in sorted(effective["origins"].items())
    )
    lines.extend(
        [
            "",
            "Provider 认证",
            f"- 接口主机：{_value(provider['host'], '内置或未设置')}",
            f"- requires_openai_auth：{_value(provider['requires_openai_auth'], '未设置')}",
            f"- env_key：{_value(provider['env_key'], '未设置')}",
            f"- env_key 是否已注入：{_value(provider['env_key_is_set'], '不适用')}",
            "",
            "官方登录与插件",
            f"- 登录方式：{_value(auth['login_method'], auth['login_probe'])}",
            f"- auth.json 是否存在：{_value(auth['cache_exists'], '未知')}",
            "- auth.json 内容：未读取",
            f"- 插件探针：{plugins['probe']}",
            f"- 插件总数：{_value(plugins['inventory_count'], '不可用')}",
            f"- Chrome 是否开启：{_value(plugins['chrome']['enabled'], '需要人工确认')}",
            "",
            "历史任务",
            f"- 检测状态：{history['probe']}",
            f"- 任务数据库：{_value(history['database_path'], '未找到')}",
            f"- 数据库访问：{'只读' if history['database_read_only'] else '未知'}",
            f"- 当前 Provider：{_value(history['current_provider'], '未设置')}",
            f"- 绑定其他 Provider 的任务：{_value(history['threads_other_providers'], '未检查')}",
            f"- 其中未归档任务：{_value(history['active_threads_other_providers'], '未检查')}",
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
            if field in catalog["selected_model"]:
                lines.append(f"- {field}：{_value(catalog['selected_model'][field], '未设置')}")
    if report["compatibility"]["rules"]:
        lines.extend(["", "兼容规则"])
        for rule in report["compatibility"]["rules"]:
            lines.append(f"- {rule['id']}（{rule['scope']}）")
            if rule["suggested_changes"]:
                lines.append("  建议修改（不会自动写入）")
                for change in rule["suggested_changes"]:
                    lines.append(
                        f"  - {change['field']}：{_value(change['from'], '缺失')} → {_value(change['to'], '缺失')}"
                    )
            lines.append("  这是带日期和环境边界的排错案例，不是所有第三方模型的默认值。")
    if report["findings"]:
        lines.extend(["", "发现的问题"])
        labels = {"error": "错误", "warning": "警告", "info": "提示"}
        for item in report["findings"]:
            lines.extend(
                [
                    f"【{labels.get(item['severity'], item['severity'])}】{item['title']}",
                    f"  {item['message']}",
                    f"  怎么处理：{item['remedy']}",
                ]
            )
    lines.extend(["", "需要人工确认"])
    lines.extend(f"- {check['instruction']}" for check in report["manual_checks"])
    lines.extend(["", "本报告只读，没有修改任何 Codex 配置。"])
    return "\n".join(lines) + "\n"
