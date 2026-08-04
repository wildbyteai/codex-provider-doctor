from __future__ import annotations

from typing import Any


MODEL_REPORT_FIELDS = (
    "slug",
    "display_name",
    "context_window",
    "effective_context_window_percent",
    "auto_compact_token_limit",
    "tool_mode",
    "supports_search_tool",
    "use_responses_lite",
)


PROJECT_IGNORED_KEYS = {
    "openai_base_url",
    "chatgpt_base_url",
    "apps_mcp_product_sku",
    "model_provider",
    "model_providers",
    "notify",
    "profile",
    "profiles",
    "experimental_realtime_ws_base_url",
    "otel",
}


Finding = dict[str, str]
JsonObject = dict[str, Any]


def finding(code: str, severity: str, title: str, message: str, remedy: str) -> Finding:
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "remedy": remedy,
    }
