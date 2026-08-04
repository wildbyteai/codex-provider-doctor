# Codex Provider Doctor

[English](README.md)

这是一个专门排查 Codex 第三方 Provider 的本地只读工具，也是官方 `codex doctor` 的补充。

很多人接入第三方 API 后，模型还能正常聊天，但问题集中出现在四个地方：

1. Skill 用不了了。
2. 模型名称显示不清晰。
3. Chrome 插件用不了。
4. 历史任务像是突然不见了。

前三个问题，不能只盯着一行参数。要把最终生效的 `config.toml`，以及它真正引用的模型目录 JSON 一起看。第四个问题还可能和本地任务数据库里保存的 `model_provider` 有关。

当前版本只检测、解释、给出建议，不自动修改任何文件或数据库。

## 使用 Skill（推荐）

普通用户不需要打开终端执行诊断命令。直接对 Codex 说：

```text
使用 $skill-installer，从 GitHub 仓库 wildbyteai/codex-provider-doctor 的根目录（path `.`）安装，并命名为 codex-provider-doctor。
```

安装完成后新建一个任务；如果技能列表没有刷新，再重启 Codex。然后说：

```text
使用 $codex-provider-doctor 检查我接入第三方 API 后，Skill、模型名称、Chrome 插件和历史任务是否正常。
```

也可以直接用自然语言描述上述问题，由 Codex 根据触发描述加载 Skill；显式写 `$codex-provider-doctor` 最可靠。Agent 会自己运行仓库内置的只读检测入口，再用中文解释结果；不需要用户复制 `codex-provider-doctor` 命令。

Skill 和命令行工具使用同一套诊断代码。Skill 不会全局安装 Python 包，不会创建虚拟环境，也不会在诊断阶段修改配置或数据库。当前仍需要本机存在 Python 3.11 或更高版本。

## 它会检查什么

- Codex 到底加载了哪一层配置：系统、用户、Profile、可信项目，还是命令行覆盖。
- 最终生效的 `model_catalog_json` 是什么。
- 不假设文件一定叫 `models.custom.json`、`models.json` 或其他固定名字。
- 相对路径按“声明这个值的配置文件所在目录”解析，不按猜测搜索。
- 当前 `model` 是否能在 `models[].slug` 中唯一匹配。
- `display_name`、`tool_mode`、`supports_search_tool`、`use_responses_lite` 和上下文窗口配置。
- 活动 Provider 的 `requires_openai_auth`、`env_key`、命令认证和明文 Token 冲突。
- 官方 Codex 登录方式、插件总数和 Chrome 开启状态；不会在报告里列出其他插件名称。
- 历史任务数据库中，有多少任务仍绑定其他 Provider。

## 先记住一个最容易配错的地方

`requires_openai_auth = true` 的意思是：这个 Provider 使用 OpenAI 认证。

它不是“保留官方登录态”的通用开关。设置为 `true` 后，Codex 会忽略这个 Provider 的 `env_key`。

也有人同时配置 `requires_openai_auth = true` 和 `experimental_bearer_token`，用来保留官方登录入口，同时给第三方 Provider 请求提供显式 Token。这种做法依赖具体版本，而且 Token 明文保存在配置里。工具会把它标成风险警告，不会直接当成必然错误，更不会自动删除字段。

所以要分开看三件事：

1. Codex 官方登录态：运行 `codex login status`。
2. 第三方 API 怎么认证：看活动 `[model_providers.<id>]`。
3. Chrome、插件、连接器或 MCP 是否安装、开启并完成授权。

## 命令行工具（可选）

需要 Python 3.11 或更高版本。

macOS / Linux：

```shell
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

### 运行命令行工具

直接检测：

```shell
codex-provider-doctor
```

输出 JSON 报告：

```shell
codex-provider-doctor --json
```

如果 Codex 是用某个 Profile 启动的，诊断时也要传同一个 Profile：

```shell
codex-provider-doctor --profile work
```

如果你正在排查 DeepSeek 类第三方接口下的 Skill 或 Chrome 兼容问题，可以显式对比这条带版本边界的案例：

```shell
codex-provider-doctor \
  --compat-rule deepseek-direct-tools-2026-08-03
```

它只会告诉你差异，不会自动写入下面三个值：

```json
{
  "tool_mode": "direct",
  "supports_search_tool": false,
  "use_responses_lite": false
}
```

这组配置只在 Codex `0.146.0-alpha.9.2` 和一个第三方接口组合中实测过。它不是所有第三方模型的默认答案。`supports_search_tool` 也不等于顶层 `web_search`。

## 为什么历史任务会“不见”

任务文件可能还在，只是本地任务索引里的 `model_provider` 仍然是旧值。某些会按 Provider 过滤任务的版本，就可能不在当前列表里显示这些任务。

这个工具会只读统计差异，不读取标题、消息、预览或正文，也不会批量更新数据库。

数据库修复比改 JSON 风险高。必须先退出 Codex，同时备份主数据库、`-wal`、`-shm` 和任务文件，再做明确范围的事务更新。首版故意不提供一键修复。详细说明见 [历史任务与 Provider 绑定](docs/HISTORY-PROVIDER.md)。

## 和官方 `codex doctor` 的关系

官方诊断覆盖安装、配置、认证、运行环境、Git、终端、app-server 和任务清单。建议先运行：

```shell
codex doctor
```

然后再用本工具检查第三方 Provider 的模型目录解析、兼容字段、Chrome/插件和历史 Provider 绑定。

## 没有安装 Skill 时的备用提示词

如果暂时无法安装 Skill，可以把 [这段诊断指令](prompts/agent-doctor.zh-CN.md) 发给 Codex。它要求 Agent 先只读检查、自己定位实际文件名和相对路径，并明确禁止读取 `auth.json` 或修改数据库。

## 隐私

- 不打开 `auth.json`，只判断它是否存在。
- 不展示 Token、Cookie、请求头、MCP 环境变量值或完整私有接口。
- SQLite 只读连接，只做聚合计数。
- 不上传任何配置、日志或报告。

更多说明见 [PRIVACY.md](docs/PRIVACY.md)。

## 开发验证

```shell
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
```

## 许可证

MIT，见 [LICENSE](LICENSE)。
