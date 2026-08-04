# 交给 Agent 的 Codex 第三方 Provider 诊断指令

把下面整段复制给 Codex。默认只检查，不修改。

```text
请对我当前电脑上的 Codex 第三方 Provider 做一次完整的只读诊断，目标是解释并定位下面四类问题：

1. Skill 不可用或没有出现在新任务里。
2. 模型名称显示成不清楚的 slug。
3. Chrome 插件不可用。
4. 切换 Provider 后，历史任务像是不见了。

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
2. 用最终生效的 model 精确匹配 models[].slug，大小写、连字符和版本后缀都必须一致。
3. 必须恰好匹配一条；零条或重复都要报错。
4. 只输出活动条目的这些字段：slug、display_name、context_window、effective_context_window_percent、auto_compact_token_limit、tool_mode、supports_search_tool、use_responses_lite。
5. display_name 缺失或为空时，说明这会导致模型列表只显示 slug 或名称不清楚，但不要替我编造名称。
6. 分开显示顶层 web_search 和模型条目的 supports_search_tool，不要把它们当成同一个参数。

如果我正在排查 2026-08-03 已观察到的 DeepSeek/第三方接口兼容案例，请只做差异对比：

{
  "tool_mode": "direct",
  "supports_search_tool": false,
  "use_responses_lite": false
}

必须同时写清：这只是在 Codex 0.146.0-alpha.9.2 和一个第三方接口组合中观察到的配置，不是所有第三方模型的默认值；当前 Codex 版本不同时必须重新验证。不要自动修改 JSON。

五、核对 Provider 认证

1. 读取最终 model_provider，并定位对应的 [model_providers.<id>]。
2. 检查 name、base_url 主机名、wire_api、requires_openai_auth、env_key、auth 和 experimental_bearer_token 是否存在。
3. requires_openai_auth 必须位于活动 Provider 块内。顶层同名字段不能算作活动 Provider 配置。
4. requires_openai_auth = true 的准确含义是“这个 Provider 使用 OpenAI 认证”；此时 Codex 会忽略 env_key。
5. 它不是“保留官方 ChatGPT 登录态”的通用开关。第三方接口使用自己的 API Key 时，通常应使用 env_key，并把官方登录态作为另一项独立检查。
6. 明确冲突要报错：requires_openai_auth = true 时 env_key 会被忽略；env_key 和 experimental_bearer_token 会竞争 Provider Token；[model_providers.<id>.auth] 不能再和其他认证字段组合。
7. requires_openai_auth = true 与 experimental_bearer_token 同时存在时，不要直接判成必然错误。说明它可能被用来保留官方登录入口，同时给 Provider 请求提供显式 Token，但这依赖具体 Codex 版本，而且 Token 明文存储。只给风险警告和版本化验证建议，不自动删除字段。
8. 对 env_key 只检查当前启动环境中是否存在非空值，不读取或输出值。

六、分别确认官方登录、插件和 Chrome

1. 运行 codex login status，只保留 ChatGPT、API key、access token、signed out 或 unknown 这类结果。
2. 运行 codex plugin list --json。兼容顶层 installed/available 结构，也兼容旧数组结构；报告只保留插件总数，以及精确匹配到的 Chrome installed 和 enabled 聚合状态，不输出其他插件名称或标识符。
3. 检查 features.apps 和 features.remote_plugin 是否被关闭。
4. 确认 Chrome 插件已安装并开启。
5. 人工检查必须列出：
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
4. 只统计：任务总数、绑定当前 Provider 的数量、绑定其他 Provider 的数量、其中未归档数量。
5. 不读取任务标题、消息、预览或正文。
6. 如果存在未归档的其他 Provider 任务，说明：任务文件可能仍在，但在会按 Provider 过滤任务的版本里可能不显示。这是本地观察，不是所有 Codex 版本的官方保证。
7. 本轮禁止 UPDATE、迁移、删除、VACUUM、覆盖数据库或复制 auth.json。

八、输出报告

请按下面结构输出：

1. 总结：错误数、警告数、最可能原因。
2. 生效配置层：每层是否存在、是否加载、关键来源。
3. 模型目录：实际路径和活动模型字段。
4. Provider 认证：官方登录和第三方认证分开写。
5. Skill / 插件 / Chrome：自动检查结果和人工验收项。
6. 历史任务：只读聚合结果和风险解释。
7. 建议修改：只给逐字段 diff，不执行。
8. 明确声明：没有读取 auth.json 内容，没有输出密钥，没有修改任何文件或数据库。

如果本机已经安装 codex-provider-doctor，优先运行：

codex-provider-doctor --json

如果我明确说正在核对 2026-08-03 的兼容案例，再加：

--compat-rule deepseek-direct-tools-2026-08-03

如果 Codex 是用 Profile 启动的，必须同时传同一个 --profile。
```
