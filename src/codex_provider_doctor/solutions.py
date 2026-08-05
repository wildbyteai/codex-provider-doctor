from __future__ import annotations

from typing import Any


PROBLEM_IDS = (
    "keep-official-login",
    "plugins-or-skills-unavailable",
    "model-name-incorrect",
    "history-missing",
    "chrome-unavailable",
)


def _disabled_plugin_features(report: dict[str, Any]) -> list[str]:
    plugins = report["plugins"]
    features = plugins.get("features") if isinstance(plugins.get("features"), dict) else {}
    return [
        feature
        for feature in ("apps", "remote_plugin")
        if features.get(feature) is False
    ]


def _keep_official_login_solution(
    report: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    provider = report["provider"]
    auth = report["auth"]
    provider_id = str(provider.get("id") or "<active-id>")
    config_path = f"model_providers.{provider_id}.requires_openai_auth"
    dual_auth_configured = (
        provider.get("requires_openai_auth") is True
        and provider.get("direct_bearer_token_configured") is True
    )
    authentication_intent = provider.get("authentication_intent")
    intent_acknowledged = (
        isinstance(authentication_intent, dict)
        and authentication_intent.get("status") == "acknowledged"
    )
    login_probe = auth.get("login_probe")
    login_method = auth.get("login_method")
    if login_probe == "ok" and login_method == "chatgpt":
        official_login_status = "confirmed"
    elif login_probe == "ok":
        official_login_status = "not_confirmed"
    else:
        official_login_status = "unverified"
    official_login = {
        "probe": login_probe,
        "method": login_method,
        "status": official_login_status,
    }

    built_in_openai = (
        provider.get("id") == "openai"
        and provider.get("name") == "OpenAI (built-in)"
    )
    if built_in_openai:
        if language == "en":
            return {
                "id": "keep-official-login",
                "title": "Keep the official sign-in",
                "status": "not_applicable_builtin_provider",
                "diagnosis": "The built-in OpenAI provider is active, so third-party dual-authentication fields are neither needed nor appropriate on this provider.",
                "config_path": None,
                "required_value": None,
                "official_login": official_login,
                "actions": [
                    "Keep the official ChatGPT/Codex sign-in and verify it separately with codex login status.",
                    "Apply the dual-authentication pattern only after selecting a custom third-party provider, inside that provider's own table.",
                    "Do not add experimental_bearer_token to the built-in OpenAI provider.",
                ],
            }
        return {
            "id": "keep-official-login",
            "title": "保留官方登录态",
            "status": "not_applicable_builtin_provider",
            "diagnosis": "当前使用内置 OpenAI Provider，不需要也不应为它新增第三方 Provider 的双认证字段。",
            "config_path": None,
            "required_value": None,
            "official_login": official_login,
            "actions": [
                "保持官方 ChatGPT/Codex 登录，并单独确认 codex login status。",
                "只有切换到自定义第三方 Provider 后，才在该 Provider 自己的配置块使用双认证模式。",
                "不要在内置 OpenAI Provider 上添加 experimental_bearer_token。",
            ],
        }

    conflicting_auth_fields = [
        field
        for field, configured in (
            ("env_key", provider.get("env_key") is not None),
            ("auth", provider.get("auth_command_configured") is True),
        )
        if configured
    ]
    if conflicting_auth_fields:
        if language == "en":
            fields = ", ".join(conflicting_auth_fields)
            return {
                "id": "keep-official-login",
                "title": "Keep the official sign-in",
                "status": "needs_auth_method_transition",
                "diagnosis": f"The active provider already uses {fields}; adding the dual-authentication fields on top would create competing provider authentication methods.",
                "config_path": config_path,
                "required_value": True,
                "official_login": official_login,
                "conflicting_auth_fields": conflicting_auth_fields,
                "actions": [
                    "Do not stack requires_openai_auth or experimental_bearer_token on the existing env_key/auth method.",
                    f"Back up the config and show the field diff first. If direct-token authentication is confirmed, remove env_key/auth in the same controlled edit, then set requires_openai_auth = true and experimental_bearer_token under [model_providers.{provider_id}].",
                    "Restart Codex and test official sign-in, third-party model requests, and plugins separately; keep plaintext-token risk independent.",
                ],
            }
        return {
            "id": "keep-official-login",
            "title": "保留官方登录态",
            "status": "needs_auth_method_transition",
            "diagnosis": f"当前 Provider 已使用 {', '.join(conflicting_auth_fields)}；直接叠加双认证字段会形成相互竞争的 Provider 认证方式。",
            "config_path": config_path,
            "required_value": True,
            "official_login": official_login,
            "conflicting_auth_fields": conflicting_auth_fields,
            "actions": [
                "不要把 requires_openai_auth 或 experimental_bearer_token 直接叠加到现有 env_key/auth 上。",
                f"先备份配置并展示字段 diff；如果确认改用直接 Token，在同一次受控修改中移除 env_key/auth，再在 [model_providers.{provider_id}] 下设置 requires_openai_auth = true 和 experimental_bearer_token。",
                "修改后完全重启 Codex，分别验证官方登录、第三方模型请求和插件；Token 明文风险继续独立处理。",
            ],
        }

    if language == "en":
        if dual_auth_configured:
            if not intent_acknowledged:
                status = "configured_intent_unverified_with_security_warning"
                diagnosis = "The dual-authentication fields are present, but this run did not confirm that the combination is intentional. Official sign-in remains a separate check, and plaintext token storage remains a separate warning."
            elif official_login_status == "confirmed":
                status = "configured_with_security_warning"
                diagnosis = "The dual-authentication configuration is in place, and the official ChatGPT sign-in was confirmed; the explicit bearer token is used for third-party requests."
            elif official_login_status == "not_confirmed":
                status = "configured_official_login_not_confirmed_with_security_warning"
                diagnosis = f"The dual-authentication configuration is in place, but the login probe reported {login_method or 'unknown'} instead of a confirmed ChatGPT sign-in."
            else:
                status = "configured_login_unverified_with_security_warning"
                diagnosis = "The dual-authentication configuration is in place: requires_openai_auth retains the official account state and the explicit bearer token is used for third-party requests; this run did not verify the official sign-in."
            return {
                "id": "keep-official-login",
                "title": "Keep the official sign-in",
                "status": status,
                "diagnosis": diagnosis,
                "config_path": config_path,
                "required_value": True,
                "official_login": official_login,
                "actions": [
                    (
                        f"Keep requires_openai_auth = true under [model_providers.{provider_id}]."
                        if intent_acknowledged
                        else "Only after the user explicitly confirms this design, record it with --problem keep-official-login or --acknowledge provider.auth.openai_with_direct_token."
                    ),
                    (
                        "Keep experimental_bearer_token in the same provider block; it authenticates third-party requests and its value is never reported."
                        if intent_acknowledged
                        else "Until intent is confirmed, do not automatically remove either field or describe the combination as the fault cause."
                    ),
                    "Separately confirm that codex login status reports ChatGPT sign-in; do not sign out or overwrite the official account state.",
                    "Plaintext token storage remains a separate security risk; do not break the working combination before migrating credentials.",
                ],
            }
        return {
            "id": "keep-official-login",
            "title": "Keep the official sign-in",
            "status": "needs_configuration",
            "diagnosis": "The active provider is not configured with the confirmed dual-authentication pattern.",
            "config_path": config_path,
            "required_value": True,
            "official_login": official_login,
            "actions": [
                f"Place requires_openai_auth = true under [model_providers.{provider_id}], not at the TOML top level.",
                "Place experimental_bearer_token in the same provider block for third-party requests; never paste its value into a report.",
                "Separately confirm that codex login status reports ChatGPT sign-in and keep that official session signed in.",
                "Do not expose the token in screenshots, reports, or issue descriptions.",
            ],
        }

    if dual_auth_configured:
        if not intent_acknowledged:
            status = "configured_intent_unverified_with_security_warning"
            diagnosis = "检测到双认证字段组合，但本次尚未确认这是用户有意设计；官方登录状态仍需单独核验，Token 明文风险也继续独立告警。"
        elif official_login_status == "confirmed":
            status = "configured_with_security_warning"
            diagnosis = "双认证配置已就位，且已确认官方 ChatGPT 登录；显式 Bearer Token 用于第三方请求。"
        elif official_login_status == "not_confirmed":
            status = "configured_official_login_not_confirmed_with_security_warning"
            diagnosis = f"双认证配置已就位，但登录探针显示 {login_method or 'unknown'}，尚未确认 ChatGPT 官方登录。"
        else:
            status = "configured_login_unverified_with_security_warning"
            diagnosis = "双认证配置已就位：requires_openai_auth 保留官方账户状态，显式 Bearer Token 用于第三方请求；本次未运行官方登录状态探针。"
        return {
            "id": "keep-official-login",
            "title": "保留官方登录态",
            "status": status,
            "diagnosis": diagnosis,
            "config_path": config_path,
            "required_value": True,
            "official_login": official_login,
            "actions": [
                (
                    f"保持 [model_providers.{provider_id}] 下的 requires_openai_auth = true。"
                    if intent_acknowledged
                    else "只有用户明确确认该设计后，才用 --problem keep-official-login 或 --acknowledge provider.auth.openai_with_direct_token 记录意图。"
                ),
                (
                    "在同一 Provider 块保留 experimental_bearer_token；它用于第三方请求，值不会进入报告。"
                    if intent_acknowledged
                    else "意图确认前不要自动删除任一字段，也不要把这组配置写成当前故障根因。"
                ),
                "单独确认 codex login status 显示 ChatGPT 登录；不要退出或覆盖官方登录状态。",
                "Token 明文存储仍是独立安全风险；迁移凭据前不要破坏当前可用组合。",
            ],
        }
    return {
        "id": "keep-official-login",
        "title": "保留官方登录态",
        "status": "needs_configuration",
        "diagnosis": "当前活动 Provider 尚未形成已确认的双认证配置。",
        "config_path": config_path,
        "required_value": True,
        "official_login": official_login,
        "actions": [
            f"把 requires_openai_auth = true 放在 [model_providers.{provider_id}] 下，不能放在 TOML 顶层。",
            "把 experimental_bearer_token 放在同一个 Provider 块用于第三方请求；报告不会读取其值。",
            "单独确认 codex login status 显示 ChatGPT 登录，并保持该官方会话不要退出。",
            "不要在截图、报告或 Issue 中暴露 Token。",
        ],
    }


def _model_name_solution(
    report: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    effective = report["effective"]
    catalog = report["catalog"]
    selected = catalog.get("selected_model")
    model_slug = effective.get("model")
    catalog_path = effective.get("model_catalog_json")
    display_name = selected.get("display_name") if isinstance(selected, dict) else None
    built_in_openai = (
        report["provider"].get("id") == "openai"
        and report["provider"].get("name") == "OpenAI (built-in)"
    )

    if built_in_openai and catalog_path is None:
        if language == "en":
            return {
                "id": "model-name-incorrect",
                "title": "Fix the model name",
                "status": "runtime_verification_required",
                "diagnosis": "The built-in OpenAI Provider is active, so no custom model catalog is required. The doctor cannot observe the App Server list or Windows Desktop picker automatically.",
                "catalog_path": None,
                "model_slug": model_slug,
                "actions": [
                    "Do not add model_catalog_json only to change the built-in model label.",
                    "Compare App Server model/list with the Windows Desktop picker.",
                    "Use one real request to confirm routing; the picker label is not proof.",
                ],
            }
        return {
            "id": "model-name-incorrect",
            "title": "修正模型名称",
            "status": "runtime_verification_required",
            "diagnosis": "当前使用内置 OpenAI Provider，无须配置自定义模型目录；doctor 无法自动观察 App Server 列表和 Windows Desktop 下拉框。",
            "catalog_path": None,
            "model_slug": model_slug,
            "actions": [
                "不要只为修改内置模型名称而新增 model_catalog_json。",
                "分别核对 App Server 的 model/list 和 Windows Desktop 下拉框。",
                "用一次真实请求确认路由；界面标签不能作为证明。",
            ],
        }

    if not isinstance(selected, dict):
        if language == "en":
            return {
                "id": "model-name-incorrect",
                "title": "Fix the model name",
                "status": "needs_catalog_match",
                "diagnosis": "The effective model does not uniquely match an entry in the active model catalog.",
                "catalog_path": catalog_path,
                "model_slug": model_slug,
                "actions": [
                    "Confirm that the effective model_catalog_json points to the intended catalog.",
                    "Make the top-level model value match exactly one models[].slug entry.",
                    "Restart Codex completely and open a new task after the catalog is corrected.",
                ],
            }
        return {
            "id": "model-name-incorrect",
            "title": "修正模型名称",
            "status": "needs_catalog_match",
            "diagnosis": "当前生效的 model 没有在实际模型目录中唯一匹配到条目。",
            "catalog_path": catalog_path,
            "model_slug": model_slug,
            "actions": [
                "确认实际生效的 model_catalog_json 指向目标模型目录。",
                "让顶层 model 与唯一一条 models[].slug 完全一致。",
                "修正目录后完全重启 Codex 并新建任务。",
            ],
        }

    display_name_is_clear = isinstance(display_name, str) and bool(display_name.strip())
    if language == "en":
        desktop_picker_reminder = {
            "code": "windows_desktop.model_picker_filtering",
            "status": "manual",
            "automatic_detection": False,
            "condition": "App Server model/list returns the active slug, but Windows Desktop omits it or shows Custom / incorrect metadata.",
            "references": {
                "as_of": "2026-08-05",
                "issues": ["openai/codex#19694", "openai/codex#36582"],
            },
        }
        actions = (
            [
                "No display_name change is needed; first confirm that the UI is loading the reported catalog path and slug.",
                "Windows Desktop reminder: if App Server model/list returns this slug but the picker still omits it or shows Custom / incorrect metadata, prioritize the matching Desktop-picker defect documented in openai/codex#19694 and #36582 as of 2026-08-05. The doctor cannot observe the UI or remote available_models response, so it does not confirm this cause automatically; recheck current issue status before calling it unresolved.",
                f'Safe workaround: switch model and model_provider in config.toml, run codex -m "{model_slug}" when the active provider is already correct, or use separate Profiles. Verify routing with a real request because the UI label is not proof. Never patch app.asar automatically; an experimental patch requires a backup and explicit confirmation.',
            ]
            if display_name_is_clear
            else [
                f'Keep the top-level model = "{model_slug}" exactly aligned with models[].slug.',
                "Set a non-empty display_name on the effective catalog entry.",
                "Restart Codex completely and open a new task; older tasks may keep the previous name.",
            ]
        )
        return {
            "id": "model-name-incorrect",
            "title": "Fix the model name",
            "status": "configured" if display_name_is_clear else "needs_catalog_change",
            "diagnosis": (
                f'The static catalog entry displays as "{display_name.strip()}"; no slug or display_name edit is indicated.'
                if display_name_is_clear
                else "The active model matches its slug, but display_name is blank, so the UI may show only the slug."
            ),
            "catalog_path": catalog_path,
            "model_slug": model_slug,
            "actions": actions,
            **(
                {"manual_reminders": [desktop_picker_reminder]}
                if display_name_is_clear
                else {}
            ),
        }
    desktop_picker_reminder = {
        "code": "windows_desktop.model_picker_filtering",
        "status": "manual",
        "automatic_detection": False,
        "condition": "App Server 的 model/list 已返回活动 slug，但 Windows Desktop 仍遗漏它或只显示 Custom / 错误元数据。",
        "references": {
            "as_of": "2026-08-05",
            "issues": ["openai/codex#19694", "openai/codex#36582"],
        },
    }
    actions = (
        [
            "无需修改 display_name；先确认界面加载的是上述模型目录和 slug。",
            "Windows Desktop 提醒：如果 App Server 的 model/list 已返回该 slug，但下拉框仍遗漏它或只显示 Custom / 错误元数据，应优先参考截至 2026-08-05 的同类缺陷 openai/codex#19694 和 #36582。doctor 无法自动观察界面或远程 available_models 响应，因此不会自动确认为根因；对外表述“仍未解决”前要复核当前 Issue 状态。",
            f'安全绕过：直接切换 config.toml 中的 model 和 model_provider；仅在当前 Provider 已正确时使用 codex -m "{model_slug}"，或建立不同 Profile。用真实请求确认路由，界面名称不能作为判据。不要自动修改 app.asar；实验补丁必须先备份并另行明确确认。',
        ]
        if display_name_is_clear
        else [
            f'保持顶层 model = "{model_slug}" 与 models[].slug 完全一致。',
            "在实际生效的模型目录条目中填写非空 display_name。",
            "完全重启 Codex 并新建任务，旧任务可能继续显示旧名称。",
        ]
    )
    return {
        "id": "model-name-incorrect",
        "title": "修正模型名称",
        "status": "configured" if display_name_is_clear else "needs_catalog_change",
        "diagnosis": (
            f"静态模型目录条目会显示为“{display_name.strip()}”，当前没有需要修改的 slug 或 display_name。"
            if display_name_is_clear
            else "活动模型已匹配 slug，但 display_name 为空，所以界面可能只显示 slug。"
        ),
        "catalog_path": catalog_path,
        "model_slug": model_slug,
        "actions": actions,
        **(
            {"manual_reminders": [desktop_picker_reminder]}
            if display_name_is_clear
            else {}
        ),
    }


def _history_solution(
    report: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    history = report["history"]
    current_provider = str(history.get("current_provider") or "<current>")
    affected = history.get("active_threads_other_providers")
    affected_count = affected if isinstance(affected, int) else 0
    provider_counts = history.get("provider_counts")
    affected_provider_counts: list[dict[str, Any]] = []
    if isinstance(provider_counts, list):
        affected_provider_counts = [
            {
                "provider": str(group.get("provider") or "<unset>"),
                "threads_unarchived": group["threads_unarchived"],
            }
            for group in provider_counts
            if isinstance(group, dict)
            and group.get("provider") != current_provider
            and isinstance(group.get("threads_unarchived"), int)
            and group["threads_unarchived"] > 0
        ]
    confirmed = any(
        item.get("code") == "history.provider_mismatch"
        and item.get("status") == "confirmed"
        for item in report["findings"]
    )

    if history.get("probe") != "ok":
        if language == "en":
            diagnosis = (
                "The read-only task-database probe did not complete, so the doctor cannot determine whether a Provider binding mismatch exists."
                if history.get("probe") == "failed"
                else "No compatible task database containing threads.model_provider was found, so the doctor cannot yet determine whether a Provider binding mismatch exists."
            )
            return {
                "id": "history-missing",
                "title": "Recover task history",
                "status": "history_not_checked",
                "diagnosis": diagnosis,
                "affected_unarchived_threads": None,
                "affected_provider_counts": [],
                "actions": [
                    "Confirm that this diagnosis uses the correct CODEX_HOME and Profile.",
                    "Update Codex and check whether an all-provider task list is available.",
                    "Keep storage read-only until the exact database is identified; do not guess a filename or migrate rows.",
                ],
            }
        diagnosis = (
            "任务数据库只读核验未完成，因此还不能判断是否存在 Provider 绑定差异。"
            if history.get("probe") == "failed"
            else "未找到包含 threads.model_provider 的兼容任务数据库，因此还不能判断是否存在 Provider 绑定差异。"
        )
        return {
            "id": "history-missing",
            "title": "恢复历史任务",
            "status": "history_not_checked",
            "diagnosis": diagnosis,
            "affected_unarchived_threads": None,
            "affected_provider_counts": [],
            "actions": [
                "先确认本次诊断使用了正确的 CODEX_HOME 和 Profile。",
                "升级 Codex，并检查是否提供全部 Provider 的任务列表。",
                "在找到准确数据库前保持只读，不要猜测文件名或迁移记录。",
            ],
        }

    if affected_count:
        status = "confirmed_root_cause" if confirmed else "binding_mismatch_detected"
        provider_names = [item["provider"] for item in affected_provider_counts]
        single_provider = provider_names[0] if len(provider_names) == 1 else None
        if language == "en":
            if single_provider:
                diagnosis = (
                    f"Confirmed: {affected_count} unarchived tasks remain bound to {single_provider} while the active provider is {current_provider}, so they are hidden from the current list."
                    if confirmed
                    else f"Found {affected_count} unarchived tasks bound to {single_provider} while the active provider is {current_provider}; provider-filtered builds can hide them."
                )
                first_action = f"Immediate no-write recovery: switch back to {single_provider}, or use an all-provider view in a version that supports it."
            else:
                counts = ", ".join(
                    f"{item['provider']}: {item['threads_unarchived']}"
                    for item in affected_provider_counts
                ) or "multiple stored providers"
                diagnosis = (
                    f"Confirmed: {affected_count} unarchived tasks are bound to other providers ({counts}) while the active provider is {current_provider}, so they are hidden from the current list."
                    if confirmed
                    else f"Found {affected_count} unarchived tasks bound to other providers ({counts}) while the active provider is {current_provider}; provider-filtered builds can hide them."
                )
                provider_list = ", ".join(provider_names) or "the providers stored on those tasks"
                first_action = f"Immediate no-write recovery: switch back to each stored provider ({provider_list}), or use an all-provider view in a version that supports it."
            return {
                "id": "history-missing",
                "title": "Recover task history",
                "status": status,
                "diagnosis": diagnosis,
                "affected_unarchived_threads": affected_count,
                "affected_provider_counts": affected_provider_counts,
                "actions": [
                    first_action,
                    "Update Codex and check the task list again before editing any database.",
                    "Only if binding migration is necessary: quit Codex, back up the database plus WAL/SHM, show the exact row count and field diff, and obtain another explicit confirmation.",
                ],
            }
        if single_provider:
            diagnosis = (
                f"已确认：{affected_count} 个未归档任务仍绑定 {single_provider}，而当前 Provider 是 {current_provider}，因此它们在当前列表不可见。"
                if confirmed
                else f"发现 {affected_count} 个未归档任务仍绑定 {single_provider}，而当前 Provider 是 {current_provider}；按 Provider 过滤的版本可能隐藏它们。"
            )
            first_action = f"立即无写入恢复：切回 {single_provider}，或在支持的版本中使用全部 Provider 视图查看这些任务。"
        else:
            counts = "，".join(
                f"{item['provider']} {item['threads_unarchived']}"
                for item in affected_provider_counts
            ) or "多个旧 Provider"
            diagnosis = (
                f"已确认：{affected_count} 个未归档任务绑定其他 Provider（{counts}），当前 Provider 是 {current_provider}，因此它们在当前列表不可见。"
                if confirmed
                else f"发现 {affected_count} 个未归档任务绑定其他 Provider（{counts}），当前 Provider 是 {current_provider}；按 Provider 过滤的版本可能隐藏它们。"
            )
            provider_list = "、".join(provider_names) or "任务记录中的对应 Provider"
            first_action = f"立即无写入恢复：分别切回 {provider_list}，或在支持的版本中使用全部 Provider 视图查看这些任务。"
        return {
            "id": "history-missing",
            "title": "恢复历史任务",
            "status": status,
            "diagnosis": diagnosis,
            "affected_unarchived_threads": affected_count,
            "affected_provider_counts": affected_provider_counts,
            "actions": [
                first_action,
                "优先升级 Codex 并重新检查任务列表；不要先改数据库。",
                "只有确需迁移绑定时，先退出 Codex，完整备份数据库及 WAL/SHM，展示精确行数和字段 diff，并再次取得明确确认。",
            ],
        }

    if language == "en":
        return {
            "id": "history-missing",
            "title": "Recover task history",
            "status": "no_provider_mismatch_detected",
            "diagnosis": "The read-only aggregate probe did not find unarchived tasks bound to another provider.",
            "affected_unarchived_threads": affected if isinstance(affected, int) else None,
            "affected_provider_counts": [],
            "actions": [
                "Update Codex and check whether an all-provider task list is available.",
                "Verify the task storage path and active profile without reading task content.",
                "Keep the database read-only until another concrete cause is identified.",
            ],
        }
    return {
        "id": "history-missing",
        "title": "恢复历史任务",
        "status": "no_provider_mismatch_detected",
        "diagnosis": "只读聚合检查没有发现绑定其他 Provider 的未归档任务。",
        "affected_unarchived_threads": affected if isinstance(affected, int) else None,
        "affected_provider_counts": [],
        "actions": [
            "升级 Codex，并检查是否提供全部 Provider 的任务列表。",
            "只核对任务存储路径和活动 Profile，不读取任务内容。",
            "在发现其他明确原因前保持数据库只读。",
        ],
    }


def _plugins_and_skills_solution(
    report: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    skills = report["skills"]
    plugins = report["plugins"]
    skill_count = skills.get("total") if isinstance(skills.get("total"), int) else 0
    skills_coverage = skills.get("coverage", "complete")
    plugin_verified = plugins.get("inventory_status") == "verified"
    disabled_features = _disabled_plugin_features(report)
    if disabled_features:
        if language == "en":
            settings = ", ".join(
                f"features.{feature} = false" for feature in disabled_features
            )
            return {
                "id": "plugins-or-skills-unavailable",
                "title": "Restore plugins and skills",
                "status": "plugin_features_disabled",
                "diagnosis": f"Plugin integration features are disabled: {settings}. Switching providers did not remove Skill installations, but official plugins and connectors may not load.",
                "disabled_features": disabled_features,
                "actions": [
                    "Restore the required feature in user-level configuration, restart Codex completely, and open a new task.",
                    "Then confirm that official plugins are enabled in Plugins/Settings and complete connector or MCP authorization.",
                    "Do not reinstall because the CLI inventory failed; first verify whether the new task exposes the expected tool.",
                ],
            }
        settings = "、".join(
            f"features.{feature} = false" for feature in disabled_features
        )
        return {
            "id": "plugins-or-skills-unavailable",
            "title": "恢复插件与 Skill",
            "status": "plugin_features_disabled",
            "diagnosis": f"插件集成功能被配置关闭：{settings}。切换 Provider 没有删除 Skill 安装，但官方插件和连接器可能无法加载。",
            "disabled_features": disabled_features,
            "actions": [
                "在用户级配置恢复所需 feature，完全重启 Codex 并新建任务。",
                "再在 Plugins/Settings 确认官方插件启用，并完成连接器或 MCP 授权。",
                "不要因为 CLI 清单失败而重装插件；先验证新任务是否实际出现目标工具。",
            ],
        }

    if skills_coverage != "complete":
        status = (
            "installation_present_runtime_unverified"
            if skill_count > 0
            else "skill_installation_unverified"
        )
        if language == "en":
            return {
                "id": "plugins-or-skills-unavailable",
                "title": "Restore plugins and skills",
                "status": status,
                "diagnosis": f"Found at least {skill_count} local skill(s); Skills in an untrusted or unreadable project were not counted, and plugin runtime state is still unverified. Switching providers did not remove the confirmed installations.",
                "skills_coverage": skills_coverage,
                "actions": [
                    "Restart Codex completely and open a new task; older tasks can keep the previous skill and tool list.",
                    "Confirm official plugins remain enabled in Plugins/Settings and that their connector or MCP authorization is complete.",
                    "Review project trust separately before expecting project Skills to load; do not trust a project merely to make the warning disappear.",
                    "If confirmed Skills load but plugin tools do not, inspect the active model catalog and third-party Responses tool compatibility before reinstalling anything.",
                ],
            }
        return {
            "id": "plugins-or-skills-unavailable",
            "title": "恢复插件与 Skill",
            "status": status,
            "diagnosis": f"检测到至少 {skill_count} 个本地 Skill；未受信任项目的 Skill 未计入，插件运行状态也尚未核验。切换 Provider 没有删除已确认的安装。",
            "skills_coverage": skills_coverage,
            "actions": [
                "完全重启 Codex 并新建任务；旧任务可能保留旧 Skill 和工具列表。",
                "在 Plugins/Settings 确认官方插件仍启用，并确认连接器或 MCP 已授权。",
                "单独审查项目可信度后再判断项目 Skill 是否应加载；不要只为消除提示而信任项目。",
                "如果已确认的 Skill 能加载但插件工具没有出现，检查活动模型目录和第三方 Responses 工具兼容性，不要先重装插件。",
            ],
        }

    if skill_count > 0 and not plugin_verified:
        status = "installation_present_runtime_unverified"
    elif skill_count > 0:
        status = "installation_present"
    else:
        status = "skill_installation_not_found"

    if language == "en":
        diagnosis = (
            f"Found {skill_count} local skill(s); plugin runtime state is not verified. Switching providers did not remove the installation, so continue with new-task loading and tool exposure."
            if skill_count > 0 and not plugin_verified
            else f"Found {skill_count} local skill(s); plugin inventory status is {plugins.get('inventory_status', 'unverified')}."
        )
        return {
            "id": "plugins-or-skills-unavailable",
            "title": "Restore plugins and skills",
            "status": status,
            "diagnosis": diagnosis,
            "actions": [
                "Restart Codex completely and open a new task; older tasks can keep the previous skill and tool list.",
                "Confirm official plugins remain enabled in Plugins/Settings and that their connector or MCP authorization is complete.",
                "If the new task discovers the skill but not the plugin tool, inspect the active model catalog and third-party Responses tool compatibility before reinstalling anything.",
            ],
        }
    diagnosis = (
        f"检测到 {skill_count} 个本地 Skill；插件运行状态尚未核验。切换 Provider 没有删除安装，问题应继续从新任务加载和工具暴露排查。"
        if skill_count > 0 and not plugin_verified
        else f"检测到 {skill_count} 个本地 Skill；插件清单状态为 {plugins.get('inventory_status', 'unverified')}。"
    )
    return {
        "id": "plugins-or-skills-unavailable",
        "title": "恢复插件与 Skill",
        "status": status,
        "diagnosis": diagnosis,
        "actions": [
            "完全重启 Codex 并新建任务；旧任务可能保留旧 Skill 和工具列表。",
            "在 Plugins/Settings 确认官方插件仍启用，并确认连接器或 MCP 已授权。",
            "如果新任务能发现 Skill 但没有插件工具，检查活动模型目录和第三方 Responses 工具兼容性，不要先重装插件。",
        ],
    }


def _chrome_solution(
    report: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    selected = report["catalog"].get("selected_model")
    selected = selected if isinstance(selected, dict) else {}
    observed = {
        "supports_search_tool": selected.get("supports_search_tool"),
        "tool_mode": selected.get("tool_mode"),
        "use_responses_lite": selected.get("use_responses_lite"),
    }
    supports_search_tool = observed["supports_search_tool"]
    evidence_scope = {
        "source": "official_codex_source",
        "as_of": "2026-08-05",
        "detected_codex_version": report["runtime"].get("codex_version"),
        "namespace_tools_feature_state": "not_checked",
        "actual_tool_exposure": "runtime_unverified",
        "runtime_verification_required": True,
    }
    disabled_features = _disabled_plugin_features(report)

    if "apps" in disabled_features:
        support_value = (
            "true"
            if supports_search_tool is True
            else "false"
            if supports_search_tool is False
            else "unset"
        )
        if language == "en":
            return {
                "id": "chrome-unavailable",
                "title": "Restore Chrome calls",
                "status": "plugin_features_disabled",
                "diagnosis": f"features.apps = false disables App/connector integration, which is more direct static evidence for missing Chrome capability. supports_search_tool = {support_value} remains separate and does not determine the live tool list by itself.",
                "observed": observed,
                "evidence_scope": evidence_scope,
                "disabled_features": disabled_features,
                "actions": [
                    "Restore features.apps in user-level configuration, restart Codex completely, and open a new task.",
                    "Confirm Chrome in Plugins/Settings and complete connector authorization before reinstalling anything.",
                    "If features.remote_plugin is also false, review it separately only when Chrome depends on the remote Plugins Directory. Then verify namespace tools and a live invocation; do not change top-level web_search.",
                ],
            }
        if support_value == "unset":
            support_value = "未设置"
        return {
            "id": "chrome-unavailable",
            "title": "恢复 Chrome 调用",
            "status": "plugin_features_disabled",
            "diagnosis": f"features.apps = false 已关闭 App/连接器集成，这是 Chrome 能力缺失的更直接静态证据；supports_search_tool = {support_value} 仍是独立字段，不能单独确定真实工具列表。",
            "observed": observed,
            "evidence_scope": evidence_scope,
            "disabled_features": disabled_features,
            "actions": [
                "先在用户级配置恢复 features.apps，完全重启 Codex 并新建任务。",
                "在 Plugins/Settings 确认 Chrome 已启用并完成连接器授权，不要先重装。",
                "如果 features.remote_plugin 也为 false，只有确认 Chrome 依赖远程插件目录时再单独处理；随后核对 namespace tools 和真实调用，不要修改顶层 web_search。",
            ],
        }

    if "remote_plugin" in disabled_features:
        if language == "en":
            return {
                "id": "chrome-unavailable",
                "title": "Restore Chrome calls",
                "status": "remote_plugin_directory_disabled_runtime_unverified",
                "diagnosis": "features.remote_plugin = false may prevent the remote Plugins Directory from loading, but it does not prove that an already installed Chrome tool is unavailable. Model-catalog and live-tool evidence remain separate.",
                "observed": observed,
                "evidence_scope": evidence_scope,
                "disabled_features": disabled_features,
                "actions": [
                    "First confirm in Plugins/Settings whether this Chrome capability comes from the remote Plugins Directory and whether it is already installed.",
                    "Only when that dependency is confirmed, enable features.remote_plugin in user-level configuration, restart Codex, and open a new task.",
                    "Then verify namespace tools, the live Chrome tool, and an actual invocation; do not infer a top-level web_search change or reinstall from CLI evidence alone.",
                ],
            }
        return {
            "id": "chrome-unavailable",
            "title": "恢复 Chrome 调用",
            "status": "remote_plugin_directory_disabled_runtime_unverified",
            "diagnosis": "features.remote_plugin = false 可能使远程 Plugins Directory 无法加载，但不能证明已经安装的 Chrome 工具因此不可用；模型目录和真实工具列表仍需分开核验。",
            "observed": observed,
            "evidence_scope": evidence_scope,
            "disabled_features": disabled_features,
            "actions": [
                "先在 Plugins/Settings 确认当前 Chrome 能力是否来自远程插件目录，以及是否已经安装。",
                "只有确认存在该依赖时，才在用户级配置开启 features.remote_plugin，完全重启 Codex 并新建任务。",
                "随后核对 namespace tools、Chrome 实际工具和真实调用；不要推断顶层 web_search，也不要只凭 CLI 证据重装插件。",
            ],
        }

    if supports_search_tool is False:
        if language == "en":
            return {
                "id": "chrome-unavailable",
                "title": "Restore Chrome calls",
                "status": "direct_namespace_branch_runtime_unverified",
                "diagnosis": "Under the official Codex source as of 2026-08-05, supports_search_tool = false forces the namespace-tool planning branch to Direct. This does not prove that Chrome declares Direct exposure or appears in the live task tool list, so the field is not fault evidence by itself.",
                "observed": observed,
                "evidence_scope": evidence_scope,
                "actions": [
                    "Restart Codex completely and open a new task, then confirm whether the Chrome tool is actually present.",
                    "If the tool is absent, check Plugins/Settings, official sign-in, the Chrome profile, and connector authorization; do not reinstall because a CLI inventory probe failed.",
                    "If the tool is present but invocation fails, inspect the Chrome extension bridge, site blocking rules, and the live invocation error.",
                ],
            }
        return {
            "id": "chrome-unavailable",
            "title": "恢复 Chrome 调用",
            "status": "direct_namespace_branch_runtime_unverified",
            "diagnosis": "按 2026-08-05 官方 Codex 源码，活动模型 supports_search_tool = false 会让 namespace 工具规划分支进入 Direct；这不能证明 Chrome 自身声明为 Direct 或已进入真实任务工具列表，因此该值本身不是故障证据。",
            "observed": observed,
            "evidence_scope": evidence_scope,
            "actions": [
                "完全重启 Codex 并新建任务，确认新任务是否实际出现 Chrome 工具。",
                "工具未出现时，检查 Plugins/Settings、官方登录、Chrome Profile 和连接器授权，不要因为 CLI 清单失败而重装。",
                "工具已经出现但调用失败时，再检查 Chrome 扩展桥接、站点阻止规则和真实调用错误。",
            ],
        }

    if supports_search_tool is True:
        if language == "en":
            return {
                "id": "chrome-unavailable",
                "title": "Restore Chrome calls",
                "status": "exposure_mode_runtime_unverified",
                "diagnosis": "Under the official Codex source as of 2026-08-05, supports_search_tool = true permits Deferred exposure only when namespace tools are also enabled; otherwise the Direct branch remains possible. The field alone cannot determine Chrome exposure or the root cause.",
                "observed": observed,
                "evidence_scope": evidence_scope,
                "actions": [
                    "In a new task, confirm whether tool_search and the Chrome tool are present before treating the plugin as damaged.",
                    "If runtime evidence confirms Deferred discovery and the third-party provider cannot support it, back up the catalog before any controlled experiment, then retest Chrome, skills, and other plugins separately.",
                    "Do not change top-level web_search, and do not reinstall a plugin only because the CLI inventory probe failed.",
                ],
            }
        return {
            "id": "chrome-unavailable",
            "title": "恢复 Chrome 调用",
            "status": "exposure_mode_runtime_unverified",
            "diagnosis": "按 2026-08-05 官方 Codex 源码，supports_search_tool = true 只有在 namespace tools 同时启用时才允许 Deferred；否则仍可能走 Direct。单靠这个字段不能确定 Chrome 暴露路径或故障根因。",
            "observed": observed,
            "evidence_scope": evidence_scope,
            "actions": [
                "先在新任务确认是否出现 tool_search 和 Chrome 工具，再判断插件是否损坏。",
                "只有运行时证据确认实际采用 Deferred 且第三方 Provider 不支持该发现链路后，才在备份模型目录的前提下做受控实验，并逐项回归 Chrome、Skill 和其他插件。",
                "不要修改顶层 web_search，也不要仅因 CLI 插件清单失败而重装插件。",
            ],
        }

    if language == "en":
        return {
            "id": "chrome-unavailable",
            "title": "Restore Chrome calls",
            "status": "runtime_verification_required",
            "diagnosis": "The model-catalog fields do not yet identify a confirmed Chrome root cause.",
            "observed": observed,
            "evidence_scope": evidence_scope,
            "actions": [
                "Open a new task and confirm whether the Chrome tool is exposed.",
                "Check Plugins/Settings, official sign-in, the Chrome profile, and connector authorization.",
                "Keep top-level web_search separate and do not reinstall from CLI inventory evidence alone.",
            ],
        }
    return {
        "id": "chrome-unavailable",
        "title": "恢复 Chrome 调用",
        "status": "runtime_verification_required",
        "diagnosis": "当前模型目录字段尚不能确认 Chrome 故障根因。",
        "observed": observed,
        "evidence_scope": evidence_scope,
        "actions": [
            "新建任务并确认 Chrome 工具是否实际暴露。",
            "检查 Plugins/Settings、官方登录、Chrome Profile 和连接器授权。",
            "顶层 web_search 必须分开判断，也不能只凭 CLI 清单证据重装插件。",
        ],
    }


def build_solutions(
    report: dict[str, Any],
    requested: list[str],
    language: str,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for problem_id in requested:
        if problem_id == "keep-official-login":
            items.append(_keep_official_login_solution(report, language))
        elif problem_id == "model-name-incorrect":
            items.append(_model_name_solution(report, language))
        elif problem_id == "history-missing":
            items.append(_history_solution(report, language))
        elif problem_id == "plugins-or-skills-unavailable":
            items.append(_plugins_and_skills_solution(report, language))
        elif problem_id == "chrome-unavailable":
            items.append(_chrome_solution(report, language))
    return {"requested": requested, "items": items}
