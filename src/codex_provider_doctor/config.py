from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any

from codex_provider_doctor.common import Finding, PROJECT_IGNORED_KEYS, finding


@dataclass
class Resolution:
    values: dict[str, Any]
    origins: dict[str, str]
    layers: list[dict[str, Any]]
    project: dict[str, Any]
    findings: list[Finding]
    codex_home: Path
    working_directory: Path


def merge_layer(
    destination: dict[str, Any],
    incoming: dict[str, Any],
    source: Path,
    origins: dict[str, str],
    prefix: str = "",
) -> None:
    for key, value in incoming.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            if not isinstance(destination.get(key), dict):
                destination[key] = {}
            merge_layer(destination[key], value, source, origins, dotted)
            continue
        destination[key] = value
        origins[dotted] = str(source)


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _project_root_markers(config: dict[str, Any]) -> list[str]:
    configured = config.get("project_root_markers")
    if isinstance(configured, list):
        return [item for item in configured if isinstance(item, str) and item]
    return [".git"]


def _find_project_root(working_directory: Path, markers: list[str]) -> Path | None:
    if not markers:
        return working_directory
    for candidate in (working_directory, *working_directory.parents):
        if any((candidate / marker).exists() for marker in markers):
            return candidate
    return None


def _project_trust(config: dict[str, Any], project_root: Path | None) -> str:
    if project_root is None:
        return "not-applicable"
    projects = config.get("projects")
    if not isinstance(projects, dict):
        return "unknown"
    for configured_path, settings in projects.items():
        if not isinstance(configured_path, str) or not isinstance(settings, dict):
            continue
        if Path(configured_path).expanduser().resolve() == project_root:
            value = settings.get("trust_level")
            return value if value in {"trusted", "untrusted"} else "unknown"
    return "unknown"


def _project_config_paths(project_root: Path, working_directory: Path) -> list[Path]:
    relative = working_directory.relative_to(project_root)
    directories = [project_root]
    current = project_root
    for part in relative.parts:
        current = current / part
        directories.append(current)
    return [directory / ".codex" / "config.toml" for directory in directories]


def _parse_override(override: str) -> tuple[dict[str, Any], str]:
    if "=" not in override:
        raise ValueError("config override must use key=value")
    dotted_key, raw_value = override.split("=", 1)
    parts = [part.strip() for part in dotted_key.split(".")]
    if not parts or any(not part for part in parts):
        raise ValueError("config override key is empty")
    try:
        value = tomllib.loads(f"value = {raw_value}")["value"]
    except tomllib.TOMLDecodeError:
        value = raw_value
    nested: dict[str, Any] = {}
    cursor = nested
    for part in parts[:-1]:
        child: dict[str, Any] = {}
        cursor[part] = child
        cursor = child
    cursor[parts[-1]] = value
    return nested, dotted_key.strip()


def _invalid_toml_finding(path: Path, project: bool = False) -> Finding:
    label = "Codex 项目配置" if project else "Codex 配置层"
    return finding(
        "config.invalid_toml",
        "error",
        f"{label}不是有效 TOML",
        f"{path} 无法解析，因此没有进入生效配置；报告没有复制错误行或文件内容。",
        "修正该文件的 TOML 语法后重新运行诊断。",
    )


def resolve_configuration(
    *,
    codex_home: Path,
    working_directory: Path,
    system_config: Path | None,
    profile: str | None,
    overrides: list[str],
) -> Resolution:
    codex_home = codex_home.expanduser().resolve()
    working_directory = working_directory.expanduser().resolve()
    values: dict[str, Any] = {}
    origins: dict[str, str] = {}
    layers: list[dict[str, Any]] = []
    findings: list[Finding] = []

    base_layers: list[tuple[str, Path]] = []
    if system_config is not None:
        base_layers.append(("system", system_config))
    base_layers.append(("user", codex_home / "config.toml"))
    if profile:
        base_layers.append(("profile", codex_home / f"{profile}.config.toml"))

    for kind, path in base_layers:
        path = path.expanduser().resolve()
        if not path.is_file():
            layers.append(
                {
                    "kind": kind,
                    "path": str(path),
                    "exists": False,
                    "applied": False,
                    "parse_status": "not_found",
                }
            )
            if kind == "profile":
                findings.append(
                    finding(
                        "config.profile_missing",
                        "error",
                        "指定的 Codex Profile 文件不存在",
                        f"请求了 Profile {profile!r}，但没有找到 {path}。",
                        "确认 Profile 名称，或创建对应的 <profile>.config.toml 文件。",
                    )
                )
            continue
        try:
            layer_values = _load_toml(path)
        except tomllib.TOMLDecodeError:
            layers.append(
                {
                    "kind": kind,
                    "path": str(path),
                    "exists": True,
                    "applied": False,
                    "parse_status": "invalid_toml",
                }
            )
            findings.append(_invalid_toml_finding(path))
            continue
        merge_layer(values, layer_values, path, origins)
        layers.append(
            {
                "kind": kind,
                "path": str(path),
                "exists": True,
                "applied": True,
                "parse_status": "ok",
            }
        )

    project_root = _find_project_root(working_directory, _project_root_markers(values))
    trust_level = _project_trust(values, project_root)
    if project_root is not None:
        for project_config in _project_config_paths(project_root, working_directory):
            project_config = project_config.resolve()
            if not project_config.is_file():
                continue
            applied = trust_level == "trusted"
            ignored_keys: list[str] = []
            parse_status = "skipped"
            if applied:
                try:
                    project_values = _load_toml(project_config)
                except tomllib.TOMLDecodeError:
                    applied = False
                    parse_status = "invalid_toml"
                    findings.append(_invalid_toml_finding(project_config, project=True))
                else:
                    parse_status = "ok"
                    ignored_keys = sorted(PROJECT_IGNORED_KEYS.intersection(project_values))
                    for ignored_key in ignored_keys:
                        project_values.pop(ignored_key, None)
                    merge_layer(values, project_values, project_config, origins)

            layer: dict[str, Any] = {
                "kind": "project",
                "path": str(project_config),
                "exists": True,
                "applied": applied,
                "parse_status": parse_status,
            }
            if parse_status == "ok":
                layer["ignored_keys"] = ignored_keys
            layers.append(layer)

            if trust_level != "trusted":
                findings.append(
                    finding(
                        "project.config_skipped_untrusted",
                        "info",
                        "发现项目配置，但 Codex 不会加载它",
                        f"项目当前信任状态是 {trust_level}，因此该 .codex/config.toml 没有进入生效配置。",
                        "除非你已经审查并愿意加载项目配置、Hooks 和规则，否则不要为了消除提示而盲目信任项目。",
                    )
                )
            elif ignored_keys:
                findings.append(
                    finding(
                        "project.config.ignored_keys",
                        "warning",
                        "项目配置包含 Codex 明确忽略的机器级字段",
                        f"以下顶层字段不会从项目层生效：{', '.join(ignored_keys)}。",
                        "把 Provider、认证、Profile、通知或遥测字段移到用户级 config.toml；项目层只保留允许的项目设置。",
                    )
                )

    if overrides:
        override_keys: list[str] = []
        for override in overrides:
            override_values, override_key = _parse_override(override)
            merge_layer(values, override_values, Path("<command-line>"), origins)
            override_keys.append(override_key)
        layers.append(
            {
                "kind": "cli",
                "path": "<command-line>",
                "exists": True,
                "applied": True,
                "parse_status": "ok",
                "keys": override_keys,
            }
        )

    return Resolution(
        values=values,
        origins=origins,
        layers=layers,
        project={
            "root": str(project_root) if project_root else None,
            "trust_level": trust_level,
        },
        findings=findings,
        codex_home=codex_home,
        working_directory=working_directory,
    )
