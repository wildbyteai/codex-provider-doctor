# 交给 Agent 的 Codex 第三方 Provider 诊断指令

把下面整段复制给 Codex。默认只检查，不修改。

```text
请对我当前电脑上的 Codex 第三方 Provider 做一次只读诊断，优先解决下面五个问题：

1. 如何保留官方 ChatGPT/Codex 登录态，同时让第三方 Provider 使用直接 Token。
2. 切换后插件、官方插件或 Skill 不可用。
3. Windows Desktop 模型名称只显示 `Custom`、错误名称或不清楚的 slug。
4. 切换 Provider 后历史任务不见了。
5. Chrome 插件无法调用。

安全边界：

- 先只读检查，不修改 config.toml、模型目录 JSON、数据库、插件或登录状态。
- 不读取、复制或输出 auth.json 的内容，只能判断文件是否存在。
- 不输出 Token、Cookie、Authorization、请求头、MCP 环境变量值或完整私有接口 URL。
- base_url 最多显示主机名。
- 不读取或输出历史任务的标题、首条消息、预览、正文、rollout 内容或动态工具 schema。
- 不要运行可能回显密钥、MCP 环境变量或完整私有配置的命令。
- 如果后面需要修改，先给出备份方案和逐字段 diff，等我明确确认后再做。数据库写入本轮禁止执行。

请按下面顺序检查：

一、确认实际环境

1. 确认 CODEX_HOME。优先使用当前进程的 CODEX_HOME；没有设置时才使用 ~/.codex。
2. 确认当前工作目录。
3. 确认 Codex 启动时是否用了 --profile。不能靠猜；如果无法从当前上下文或启动参数确认，就把 Profile 标记为“待确认”，分别说明有无 Profile 会影响什么。
4. 运行 codex --version，只保留版本号。
5. 如果当前版本支持，先运行 codex doctor，使用它检查通用安装、认证、运行环境和任务清单问题；不要用它代替后面的 Provider 专项检查。

二、还原最终生效的配置

按实际优先级检查系统配置、$CODEX_HOME/config.toml、选中的 $CODEX_HOME/<profile>.config.toml、可信项目从项目根到当前目录的 .codex/config.toml，以及本次命令行 -c/--config 覆盖。

逐层记录：文件路径、是否存在、TOML 是否有效、是否真正加载、哪些关键字段由这一层覆盖。

项目不可信时，不要擅自把它设为可信。项目级 .codex/config.toml 里的 model_provider 和 model_providers 等机器级字段可能被 Codex 忽略，要明确指出，不能把它们误算为生效配置。

三、定位真正的模型目录 JSON

1. 从最终生效配置里读取 model_catalog_json。
2. 不要假设文件叫 models.custom.json、models.json、catalog.json 或任何固定名称。
3. 不要先全盘搜索同名文件再随便选一个。
4. 如果值是绝对路径，使用该绝对路径。
5. 如果值是相对路径，按“最终声明 model_catalog_json 的那个配置文件所在目录”解析；只有命令行覆盖里的相对路径，才按本次工作目录解析。
6. 输出：原始值、声明它的配置层、解析后的绝对路径、文件是否存在。不要输出无关目录列表。

四、核对活动模型

1. 解析模型目录 JSON，确认顶层是对象，models 是数组。
2. 先报告 models 条目总数，但不要完整输出所有模型条目。
3. 用最终生效的 model 精确匹配 models[].slug，大小写、连字符和版本后缀都必须一致。
4. 必须恰好匹配一条；零条或重复都要报错。
5. 只输出活动条目的这些字段：slug、display_name、context_window、effective_context_window_percent、auto_compact_token_limit、tool_mode、supports_search_tool、use_responses_lite。
6. display_name 缺失或为空时，说明这会导致模型列表只显示 slug 或名称不清楚，但不要替我编造名称。
7. 如果 slug 和非空 display_name 已经正确，不要继续建议修改字段，也不要反复清缓存。先确认界面使用的是这份生效目录，再按下面的 Windows Desktop 条件式提醒判断。
8. 分开显示顶层 web_search 和模型条目的 supports_search_tool，不要把它们当成同一个参数。
9. 如果用户使用 Windows Desktop，并且已经提供或确认以下证据：App Server 的 `model/list` 返回活动 slug，但桌面下拉框仍遗漏它，或只显示 `Custom`、`Custom High/Max`、错误名称或错误元数据，则把 Desktop 选择器二次过滤作为首要已知兼容性疑点。必须同时写清：
   - 诊断器无法从静态配置自动观察桌面 UI 或远程 `available_models` 响应，因此不能自动确认为根因；
   - 截至 2026-08-05 的同类公开记录是 `openai/codex#19694` 和 `#36582`，对外表述“仍未解决”前要重新核对当前状态；
   - 安全绕过优先使用配置切换器直接切换 `model` 与 `model_provider`；只有当前 Provider 已正确时才单独使用 `codex -m <slug>`，跨 Provider 切换用不同 Profile；
   - 必须用新任务真实请求或 CLI 调用确认实际模型路由，界面名称不能作为判据；
   - 只有 App Server 列表或真实请求也失败时，才继续排查 Profile、配置层或 Provider 请求链；
   - 不自动修改 `app.asar`。实验性补丁必须先备份、取得明确确认并提供恢复路径。

如果我明确报告“第三方模型下 Chrome 插件不可用”，先把活动模型目录条目的实际 `supports_search_tool` 放到兼容性排查前部，并按当前工具暴露语义解释：

- 仅当当前是第三方 Responses Provider 时适用；不要限定为 DeepSeek。
- `supports_search_tool = false` 时，按 2026-08-05 官方源码会让 namespace 工具规划条件回落到 Direct；这不能证明 Chrome 自身声明为 Direct 或已经进入真实任务工具列表，这个值本身也不是故障证据。
- `supports_search_tool = true` 时，只有 namespace tools 同时启用才允许 Deferred，否则仍可能走 Direct；不能仅凭这个字段判定 Chrome 暴露路径或根因。
- 把模型目录静态证据、插件清单证据和真实调用烟雾测试分开写；真实调用仍是更强证据。
- 不要自动推断或修改顶层 `web_search`，也不要因为 CLI 插件清单探针失败就建议重装插件。

如果我正在排查 2026-08-03 已观察到的 DeepSeek/第三方接口兼容案例，请只做差异对比：

{
  "tool_mode": "direct",
  "supports_search_tool": false,
  "use_responses_lite": false
}

必须同时写清：这只是在 Codex 0.146.0-alpha.9.2 和一个第三方 DeepSeek Responses 接口组合中观察到的配置，不是所有第三方模型的默认值；官方模型即使位于同一模型目录也不适用。`supports_search_tool = false` 和 `use_responses_lite = false` 是该案例建议值；`tool_mode = direct` 只在直接工具出现症状时核对，当前 `code_mode_only` 已正常时不写成必改项。当前 Codex 版本不同时必须重新验证。不要自动修改 JSON。

五、核对 Provider 认证

1. 读取最终 model_provider，并定位对应的 [model_providers.<id>]。
2. 检查 name、base_url 主机名、wire_api、requires_openai_auth、env_key、auth 和 experimental_bearer_token 是否存在。
3. requires_openai_auth 必须位于活动 `[model_providers.<id>]` 块内。顶层同名字段不能算作活动 Provider 配置。
4. 对已经确认的双认证设计，`requires_openai_auth = true` 保留官方 ChatGPT/Codex 账户状态，`experimental_bearer_token` 优先用于第三方 Provider 请求。
5. 这套双认证只适用于自定义第三方 Provider，不要套到内置 `openai` Provider。
6. 用户明确要求保留官方登录态时，把这个组合标记为 acknowledged / intentional；不能再建议删除 `requires_openai_auth` 或改成 `false`。
7. 如果当前 Provider 已经使用 `env_key` 或 `[model_providers.<id>.auth]` 命令认证，不要直接叠加双认证字段；先给出备份方案和完整字段迁移 diff，在一次受控修改中切换请求认证方式。
8. `env_key`、`experimental_bearer_token` 和 `[model_providers.<id>.auth]` 的其他组合仍按当前版本实际优先级单独判断，不要把双认证设计混入普通冲突。
9. 插件是否真实可用仍需新任务、设置页面和实际调用验证，不能只从认证字段推断。
10. Token 明文存储必须作为独立 warning 保留，不能因为认证意图已确认而隐藏。
11. 对 env_key 只检查当前启动环境中是否存在非空值，不读取或输出值。

六、分别确认官方登录、插件和 Chrome

1. 运行 codex login status，只保留 ChatGPT、API key、access token、signed out 或 unknown 这类结果。
2. 本地 Skill 只统计数量，不输出名称。用户级 Skill 可以只读计数；项目级 Skill 只有在项目已受信任时才扫描，项目不可信或状态未知时跳过并标记覆盖不完整，不能为了完成检查而修改信任状态。
3. 运行 codex plugin list --json。兼容顶层 installed/available 结构，也兼容旧数组结构；报告只保留插件总数，以及精确匹配到的 Chrome installed 和 enabled 聚合状态，不输出其他插件名称或标识符。
4. 检查 features.apps 和 features.remote_plugin 是否被关闭。
5. 确认 Chrome 插件已安装并开启。
6. 按证据强弱判断插件与 Chrome 状态：实际调用成功 > 当前任务已提供目标工具或设置页面可见 > codex plugin list --json 成功 > 静态配置推断。CLI 探针失败或输出无法解析，只表示清单未核验，必须标成 info / unverified，单独出现时不改变退出码 0；界面或实际调用正常时，不建议重装插件或清理缓存。
7. 人工检查必须列出：
   - 使用的是 Google Chrome，不是其他 Chromium 浏览器；
   - 当前 Chrome Profile 正是安装并启用 ChatGPT 扩展的 Profile；
   - ChatGPT/Codex 的 Computer Use 没有阻止目标网站；
   - 插件依赖的连接器或 MCP 已完成授权；
   - 配置或插件变化后，完全重启 Codex，并新建任务；
   - 分别测试 Skill、Chrome、Web Search 和其他插件，不能用一项成功代替全部验收；
   - 插件在 ChatGPT 桌面端或 Codex CLI 使用，IDE 扩展不支持插件。

七、只读检查历史任务 Provider 绑定

1. 不要假设数据库固定叫 state_5.sqlite。
2. 只在 CODEX_HOME 和 CODEX_HOME/sqlite 下发现 .db、.sqlite、.sqlite3 候选文件，再用表结构确认是否存在 threads.model_provider。
3. SQLite 必须用只读模式，并开启 query_only。
4. 只统计：任务总数、绑定当前 Provider 的数量、绑定其他 Provider 的数量、其中未归档数量；并按每个 model_provider 给出全部、未归档和已归档数量。
5. 不读取任务标题、消息、预览或正文。
6. 如果存在未归档的其他 Provider 任务，默认只说明：任务文件可能仍在，但在会按 Provider 过滤任务的版本里可能不显示。这是本地观察，不是所有 Codex 版本的官方保证。
7. 如果没有找到兼容数据库或只读探针失败，只能写“尚未核验”，不能写成“未发现 Provider 绑定差异”。
8. 如果未归档任务分属多个旧 Provider，逐个输出聚合数量，不能把总数全部归到其中一个 Provider。
9. 只有用户明确确认“本次历史任务不可见就是由这些 Provider 绑定不一致造成”后，才把结论升级为“用户确认的根因”；同时写清自动探针证明的是绑定差异，因果确认来自用户对本次现象的确认。
10. 本轮禁止 UPDATE、迁移、删除、VACUUM、覆盖数据库或复制 auth.json。任何未来修复都必须先退出相关进程，完整备份数据库及其 WAL/SHM 旁路文件，展示精确行数和字段 diff，并再次取得明确确认。

八、输出报告

请按下面结构输出：

1. 先按用户选中的问题给出：当前判断、立即恢复方法、需要修改的位置、仍需人工验证的边界。
2. 默认不要先展开配置层。只有用户要求技术证据时，才使用 `--details` 展示生效配置层、字段来源、模型目录、认证、插件和历史聚合。
3. 有用户确认根因时直接写“已确认根因”，否则只给证据支持的判断。
4. 建议修改只给逐字段 diff，不执行。
5. 明确声明：没有读取 auth.json 内容，没有输出密钥，没有修改任何文件或数据库。

如果本机已经安装 codex-provider-doctor，优先运行：

codex-provider-doctor --json

根据用户问题添加一个或多个入口：

--problem keep-official-login
--problem plugins-or-skills-unavailable
--problem model-name-incorrect
--problem history-missing
--problem chrome-unavailable

只有需要配置层和完整证据时才加：

--details

如果我明确说正在核对 2026-08-03 的兼容案例，再加：

--compat-rule deepseek-direct-tools-2026-08-03

如果我已经明确确认 requires_openai_auth = true 与 experimental_bearer_token 的组合就是有意设计，再加：

--acknowledge provider.auth.openai_with_direct_token

如果我明确报告第三方模型下 Chrome 插件不可用，再加：

--symptom chrome-plugin-unavailable

如果只读结果已发现历史 Provider 绑定不一致，并且我明确确认这就是本次历史任务不可见的根因，再加：

--confirm-cause history.provider_mismatch

如果 Codex 是用 Profile 启动的，必须同时传同一个 --profile。
```
