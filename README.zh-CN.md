# Codex Provider Doctor

[English](README.md)

这是一个围绕 5 个真实痛点设计的 Codex 第三方 Provider 本地只读恢复工具，也是官方 `codex doctor` 的补充：

1. 如何保留官方登录态。
2. 切换后插件、官方插件或 Skill 不可用怎么办。
3. 模型名称显示不正确怎么办。
4. 历史任务消失是什么原因，怎么恢复。
5. Chrome 插件无法调用怎么办。

当前版本只检测、解释、给出建议，不自动修改任何文件或数据库。

## 五个问题，先这样处理

1. **保留官方登录态**：对自定义第三方 Provider，把 `requires_openai_auth = true` 放在该 Provider 的 `[model_providers.<id>]` 内。第三方请求凭据另算：优先使用 `env_key`，其次是 `experimental_bearer_token`，最后才是保留的官方认证；配置了 `env_key` 但没有注入时会直接失败，不会回退。只有命令认证 `auth` 与这些字段互斥。官方登录和明文 Token 风险仍要分别检查。
2. **插件、官方插件或 Skill 不可用**：先检查 `features.plugins`，再检查 Plugins/Settings、授权和新任务工具列表。`features.apps` 只控制 App/连接器，`features.remote_plugin` 只控制远程插件目录，都不是插件总开关。CLI 清单失败不能作为重装依据。
3. **模型名称不正确**：确认实际生效的 `model_catalog_json`，再按 Codex 的最长 `models[].slug` 前缀规则匹配；首次未命中且 `model` 只有一层简单命名空间（如 `vendor/model-name`）时，会去掉前缀重试，仍未命中则使用回退元数据，不会阻断请求。检查命中条目的 `display_name`，但不要只因为 Windows Desktop 显示 `Custom` 就反复改 JSON。
4. **历史任务消失**：只读统计任务绑定的旧 Provider。先切回旧 Provider、使用可用的全部 Provider 视图或升级 Codex；只有确需迁移绑定时，才在退出 Codex、备份数据库及 WAL/SHM、展示字段 diff 并再次确认后处理。
5. **Chrome 无法调用**：先看活动模型的 `supports_search_tool`。第三方 Responses Provider 下，`true` 会把符合条件的 MCP/插件工具放到 `tool_search` 后面；DeepSeek 或第三方接口不能正确使用这条发现路径时，Chrome 可能直接消失或无法调用，所以 `true` 是首要配置兼容性疑点。`false` 不走这条延迟发现路径，符合当前 DeepSeek 实测可用组合。它不是唯一根因，仍要继续核对 `features.plugins`、Plugins/Settings、授权、新任务工具列表和真实调用。

## 默认报告长什么样

doctor 默认不再输出一串技术判断，而是把每个问题固定整理成一张“体检单”：

```text
1. 检查项【状态】
   当前结果：现在到底怎么样
   具体位置/关键参数：哪个文件或界面、哪个字段、当前值是什么
   受什么控制：哪些设置、登录或运行状态决定这个结果
   目标状态：正常时应该是什么样
   怎么处理：按顺序做什么
   怎么确认：用什么实际结果验收
```

默认报告使用普通用户能理解的表达，并直接列出完成排查所需的具体位置和关键参数。路径会安全归一化为 `$CODEX_HOME/...`、`$PROJECT_ROOT/...` 等形式；Token 只显示“已配置/未配置”，不会显示内容。使用 `--details` 才展开完整配置层、字段来源和技术判断。

## 使用 Skill（推荐）

普通用户只要把仓库链接发给 Codex：

```text
帮我安装这个 Skill：https://github.com/wildbyteai/codex-provider-doctor
```

安装完成后新建一个任务；如果技能列表没有刷新，再重启 Codex。然后说：

```text
帮我检查 Codex 切换第三方 API 后，怎么保留官方登录，并恢复插件、Skill、模型名称、历史任务和 Chrome。
```

安装参数、仓库根目录和 Skill 名称由 Agent 自己处理。如果当前任务没有匹配到 Skill，再显式说“使用 `$codex-provider-doctor` 检查”。Agent 会自己运行仓库内置的只读检测入口，再用中文解释结果；不需要用户复制 `codex-provider-doctor` 命令。

Skill 默认直接运行人类可读报告，不再先取 `--json` 后自由总结。Agent 必须保留工具输出的每张体检单及六个固定字段；只有机器集成需要 JSON 时，才读取 `solutions.health_checks`。这样同一份诊断不会因为不同电脑上的 Agent 总结习惯而重新变成散乱技术说明。

Skill 和命令行工具使用同一套诊断代码。Skill 不会全局安装 Python 包，不会创建虚拟环境，也不会在诊断阶段修改配置或数据库。当前仍需要本机存在 Python 3.11 或更高版本。

如果权限限制导致只能从临时仓库副本运行，必须继续使用真实 `CODEX_HOME`、原项目工作目录和同一个 Profile；启动器改变目录时要显式传回 `--cwd`。三者没有核对一致前，不能笼统声称“结果不受影响”，尤其是项目配置和项目级 Skill 的判断可能不同。

## 它会检查什么

- Codex 到底加载了哪一层配置：系统、用户、Profile、可信项目，还是命令行覆盖。
- 最终生效的 `model_catalog_json` 是什么。
- 不假设文件一定叫 `models.custom.json`、`models.json` 或其他固定名字。
- 模型目录条目总数，但不会把所有模型条目完整输出。
- 相对路径按“声明这个值的配置文件所在目录”解析，不按猜测搜索。
- 当前 `model` 最终命中的最长 `models[].slug` 前缀，以及单层命名空间重试和回退元数据情况。
- `display_name`、`tool_mode`、`supports_search_tool`、`use_responses_lite` 和上下文窗口配置。
- 当模型目录字段已经正确时，给出 Windows Desktop 选择器条件式提醒，并明确区分静态目录、App Server 列表、桌面下拉框和真实请求四层证据。
- 默认把 5 个问题分别整理为“当前结果、具体位置/关键参数、受什么控制、目标状态、怎么处理、怎么确认”；默认报告直接给出安全归一化的文件/界面位置、参数和当前值，`--details` 再展开完整配置层与技术证据。
- 只统计用户级和可信项目级本地 Skill 数量，不输出 Skill 名称；项目不可信时不扫描项目 Skill，并明确标记覆盖不完整。
- 面向一般第三方 Responses 模型的 Chrome 症状排查：`supports_search_tool = true` 会把符合条件的插件工具放到 `tool_search` 延迟发现路径，`false` 则保持直接暴露；报告同时保留插件状态和运行时验证边界。
- 活动 Provider 的请求凭据优先级、缺失 `env_key` 不回退、命令认证互斥规则，以及 `requires_openai_auth`、官方登录和明文 Token 风险的独立状态。
- 官方 Codex 登录方式，以及 CLI 只读探针成功时的插件总数和 Chrome 开启状态；探针失败时明确保留为“未核验”，不会在报告里列出其他插件名称。
- 历史任务按 `model_provider` 分组的总数、未归档数和已归档数。

## 插件证据怎么判断

CLI 插件探针只是一个证据来源，不是运行时状态的最终结论。判断顺序应该是：

1. 实际调用成功。
2. 当前任务已经提供目标工具，或设置页面、Plugins 页面能够看到它。
3. `codex plugin list --json` 成功返回。
4. 静态配置和人工推断。

如果 CLI 命令失败或返回当前工具不认识的格式，只能说明插件清单尚未核验。它会被记录为 `info / unverified`，单独出现时不会把退出码从 `0` 变成 `1`。即使 CLI 清单成功但没有确认 Chrome，也仍是低优先级辅助证据，不等于真实调用失败。设置页面或实际调用已经正常时，不要重装插件或清理缓存；只有这些更强证据也失败时，才继续考虑修复。

如果用户明确报告 Chrome 不可用，优先使用 `--problem chrome-unavailable`；底层参数 `--symptom chrome-plugin-unavailable` 继续兼容已有集成。按 2026-08-06 官方源码，`supports_search_tool = true` 会启用 `search_tool_enabled`；namespace MCP tools 开启时，符合条件的插件工具会从初始工具列表移到 `tool_search` 后面的 Deferred 暴露。第三方模型或 Responses Provider 如果不能正确使用这条发现路径，Chrome 就可能不出现或无法调用，因此 `true` 是首要静态兼容性疑点，但不能据此断言唯一根因。`false` 不走这条延迟发现路径，在当前 DeepSeek 实测组合中可恢复 Chrome。设置页面、新任务工具列表和真实调用仍要分开核验；这个检查不会推断或修改顶层 `web_search`。

这几个参数要分开理解：

- `models[].supports_search_tool`：决定插件/MCP 工具是否可能被放到 `tool_search` 后面；当前 DeepSeek 组合应优先使用 `false`。
- `models[].tool_mode`：决定 Direct 或 Code Mode 入口，不负责安装或启用 Chrome。
- `models[].use_responses_lite`：设为 `true` 会停用托管 Responses 工具，但不等于关闭 Chrome 插件。
- 顶层 `web_search`：只控制 Web Search，不控制 Chrome 插件。

## Windows Desktop 模型选择器提醒

这个问题目前不适合伪装成全自动检测。doctor 不能只从 `config.toml` 和模型目录判断 Windows Desktop 实际拿到了什么远程 `available_models` 响应，也不能自动观察下拉框最终显示结果。

只有下面的人工证据链同时成立时，才把 Desktop 选择器额外过滤作为首要已知兼容性疑点：

1. 实际生效的模型目录中，活动 `model` 已按最长前缀规则命中预期 `slug`，且 `display_name` 非空。
2. App Server 的 `model/list` 已经返回该模型。
3. Windows Desktop 下拉框仍遗漏模型，或只显示 `Custom`、`Custom High/Max`、错误名称或错误元数据。
4. 如果要证明模型实际可用，还要用新任务真实请求或 CLI 调用完成烟雾测试；界面标签不能证明实际路由。

截至 2026-08-05，OpenAI 官方仓库中的 [#19694](https://github.com/openai/codex/issues/19694) 与 [#36582](https://github.com/openai/codex/issues/36582) 记录了同类现象。报告会把它们作为带日期的参考快照，并提醒在对外表述“仍未解决”前重新核对当前状态，而不是永久写死结论。

安全绕过顺序：

1. 用配置切换器直接修改 `config.toml` 中的 `model` 和 `model_provider`。
2. 当前 Provider 已正确时使用 `codex -m <slug>`；跨 Provider 切换时，为官方模型和第三方模型建立不同 Profile。
3. 新建任务并发起真实请求，核对实际模型行为，不把 Desktop 显示名称当作判据。
4. 只有 App Server 列表或真实请求也失败时，才回到 Profile、配置优先级和 Provider 请求链排查。

doctor 不会自动修改 `app.asar`。任何实验性 Desktop 补丁都必须先备份、取得明确确认，并提供可恢复路径；它不是默认修复方案。

## 如何保留官方登录态

已经确认的双认证配置必须这样放：

```toml
model = "vendor-model"
model_provider = "vendor"

[model_providers.vendor]
base_url = "https://provider.example/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "<第三方 Token>"
```

这套写法只适用于自定义第三方 Provider，不要套到内置 `openai` Provider。`requires_openai_auth` 可以与 `env_key` 或 `experimental_bearer_token` 共存。请求凭据优先级是 `env_key` → 直接 Token → 保留的官方认证；配置了 `env_key` 但没有注入时，请求直接失败，不会回退。只有 `[model_providers.<id>.auth]` 命令认证与这三个字段互斥，切换时才需要先备份并展示逐字段迁移 diff。

关键是 `requires_openai_auth = true` 必须位于活动 `[model_providers.<id>]` 内，不能放在 TOML 顶层。截至 2026-08-05，[当前 Codex Provider 认证源码](https://github.com/openai/codex/blob/main/codex-rs/model-provider/src/provider.rs)会保留官方 ChatGPT/Codex 账户状态，同时让显式 Provider Token 优先用于第三方请求。插件是否真实可用仍需新任务和实际调用验证；明文 Token 风险也必须继续单独警告。

所以要分开看三件事：

1. Codex 官方登录态：运行 `codex login status`。
2. 第三方 Provider 请求怎么认证：看活动 `[model_providers.<id>]`。
3. 配置文件明文 Token 风险：无论设计意图是否已确认，只要直接保存 `experimental_bearer_token`，就继续保留独立 warning。

Chrome、插件、连接器或 MCP 是否安装、开启并完成授权，属于认证之外的另一组运行时能力检查。

用户明确要保留官方登录态时，直接运行：

```shell
codex-provider-doctor --problem keep-official-login
```

这只会选择对应体检项，不会自动确认当前直接 Token 组合是用户有意设计。只有用户明确确认后，再加 `--acknowledge provider.auth.openai_with_direct_token`；确认也不会隐藏明文 Token 警告。

旧的显式确认参数继续兼容：

```shell
codex-provider-doctor \
  --acknowledge provider.auth.openai_with_direct_token
```

这个参数只把认证组合标记为“已确认且有意”，不会隐藏 `experimental_bearer_token` 明文存储的独立警告。

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

默认报告会直接显示 5 张结构一致的体检单。只排查一个问题时使用：

```shell
codex-provider-doctor --problem keep-official-login
codex-provider-doctor --problem plugins-or-skills-unavailable
codex-provider-doctor --problem model-name-incorrect
codex-provider-doctor --problem history-missing
codex-provider-doctor --problem chrome-unavailable
```

需要展开配置层、字段来源和完整技术证据时再加：

```shell
codex-provider-doctor --details
```

输出 JSON 报告：

```shell
codex-provider-doctor --json
```

JSON 中的 `solutions.health_checks` 与默认人类报告一一对应，每项固定包含：`current_result`、`exact_targets`、`controlled_by`、`desired_state`、`how_to_change` 和 `how_to_verify`。`exact_targets` 中每条记录包含 `location`、`parameter` 和 `current_value`，路径已归一化，敏感值已脱敏。面向普通用户时优先直接使用默认报告，不要从原始 finding 重新组织一份自由格式总结。

如果 Codex 是用某个 Profile 启动的，诊断时也要传同一个 Profile：

```shell
codex-provider-doctor --profile work
```

底层 Chrome 症状参数继续供已有集成使用：

```shell
codex-provider-doctor \
  --symptom chrome-plugin-unavailable
```

如果只读报告已发现历史 Provider 绑定不一致，并且用户明确确认这就是本次历史任务不可见的根因：

```shell
codex-provider-doctor \
  --confirm-cause history.provider_mismatch
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

这组配置只在 Codex `0.146.0-alpha.9.2` 和一个第三方 DeepSeek Responses 接口组合中实测过。只有当前选中的模型也属于 DeepSeek、并且使用第三方 Responses Provider 时，规则才进入评估。即使官方模型出现在同一个自定义模型目录中，也不会套用这条规则。

三项字段的处理并不相同：

- `supports_search_tool = false`：只作为当前第三方 DeepSeek 案例的建议；官方模型可以保持 `true`。
- `use_responses_lite = false`：属于同一日期案例的建议值。
- `tool_mode = direct`：状态为 `review_if_symptomatic`；如果 `code_mode_only` 下直接工具已经正常，就不把它写成必须修改。

`supports_search_tool` 是模型目录字段，不等于顶层 `web_search`，也不构成关闭 Web Search 的理由。

## 为什么历史任务会“不见”

任务文件可能还在，只是本地任务索引里的 `model_provider` 仍然是旧值。某些会按 Provider 过滤任务的版本，就可能不在当前列表里显示这些任务。

这个工具会只读统计每个 `model_provider` 的全部、未归档和已归档数量，不读取标题、消息、预览或正文，也不会批量更新数据库。

没有用户明确确认时，报告只说这些绑定差异“可能”导致 Provider 过滤后的列表不可见。用户确认本次因果关系后，`--confirm-cause history.provider_mismatch` 才会把它写成“已确认根因”；自动探针证明的是绑定差异，因果结论来自用户对本次现象的确认。

数据库修复比改 JSON 风险高。必须先退出 Codex，同时备份准确的主数据库、`-wal`、`-shm` 和任务文件，展示精确行数与字段 diff，并再次取得明确确认后，才可能做范围受限的事务更新。首版故意不提供一键修复。详细说明见 [历史任务与 Provider 绑定](docs/HISTORY-PROVIDER.md)。

## 和官方 `codex doctor` 的关系

官方诊断覆盖安装、配置、认证、运行环境、Git、终端、app-server 和任务清单。建议先运行：

```shell
codex doctor
```

然后再用本工具检查第三方 Provider 的模型目录解析、兼容字段、Chrome/插件和历史 Provider 绑定。

## Finding 分级与 JSON 兼容性

`schema_version` 继续保持为 `1`，现有顶层字段与插件 `probe` 字段保留。本轮以新增字段为主：

- 每条 finding 新增 `status`、`category` 和 `intentional`，并继续保留 `severity`。
- summary 新增 `info`、`unverified`、`acknowledged`、`confirmed_causes` 和 `intentional` 计数。
- 插件报告新增 `inventory_status`；命令失败、JSON 无效或 JSON 结构不受支持时，`probe` 保持为 `failed`，清单状态诚实地保持为 `unverified`。
- 模型目录报告新增 `model_count`。
- 历史任务报告新增 `provider_counts`。
- 报告新增本地 `skills` 数量，以及面向 5 个问题的 `solutions`；`solutions.health_checks` 固定保存与人类报告一致的六栏体检单，其中 `exact_targets` 提供安全归一化的位置、字段和当前值。登录方案包含独立的官方登录核验状态，历史方案包含受影响旧 Provider 的聚合数量。
- 兼容报告新增一般 Chrome 排查使用的 `symptom_assessments`，以及带日期规则使用的 `field_assessments` 和 `observed_differences`；`suggested_changes` 不包含只按症状观察的字段。
- JSON finding 数组保持诊断生成顺序；优先级排序只用于人类可读报告，不改变机器输出顺序。

退出码仍只由 error 和 warning 决定：没有两者时为 `0`，有 warning 时为 `1`，有 error 时为 `2`，工具无法安全完成时为 `3`。

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
