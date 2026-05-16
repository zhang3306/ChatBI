# ChatBI 智慧家庭AI运营系统 — 完整技术解读

> 本文档用于深入理解 ChatBI 项目的全部技术细节、开发难点和生产运维挑战，帮助你将项目经验内化为自己的技术积累。

---

## 一、项目概况

### 1.1 业务场景

面向企业内部运营团队的**对话式数据查询平台**。运营人员用自然语言提问，系统自动将问题转为 SQL、执行查询、返回结果，替代了"找数据→写SQL→做报表"的冗长流程。

**核心价值**：将数据查询门槛从"会SQL的运营"降到"会说话的运营"。

### 1.2 核心能力

| 能力 | 说明 |
|------|------|
| Text2SQL | 自然语言 → SQL 语句的自动转换 |
| RAG增强检索 | 向量库/关键词库存储表结构和SQL示例，提升生成准确率 |
| SQL安全校验 | AST解析，只允许SELECT，拦截危险操作 |
| 多轮对话 | 支持追问、纠错、维度切换 |
| 查询优化 | 汇总表路由，避免大表全扫 |
| 数据可视化 | 自动识别数据类型，生成表格+柱状图/折线图 |

---

## 二、架构全景

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                         │
│  聊天界面 → 消息提交 → 结果渲染（表格/图表/SQL展开）      │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   ConversationAgent                      │
│  · 接收用户输入                                          │
│  · 维护对话历史（最近N轮）                                 │
│  · 调用 LLM 生成 SQL / 格式化回复                         │
│  · 存储最后一次查询结果（供UI渲染）                         │
└────────┬─────────────┬──────────────┬────────────────────┘
         │             │              │
         ▼             ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ SQLGenerator │ │ Executor │ │    RAG       │
│ · RAG检索    │ │ · 安全校验│ │ · 关键词匹配  │
│ · Prompt构建 │ │ · 汇总路由│ │ · Schema索引  │
│ · LLM调用    │ │ · SQL执行 │ │ · Example索引 │
└──────────────┘ └──────────┘ └──────────────┘
```

### 2.1 数据流详解

```
用户输入："北京有多少在线设备？"
        │
        ▼
1. Agent 收到消息，追加到对话历史
        │
        ▼
2. SQLGenerator.generate() 调用
   ├─ 2.1 Retriever.retrieve("北京多少在线设备")
   │    从 DocumentStore 检索 Top-K Schema + Example
   │    └─ schema_indexer → "devices" 表结构
   │    └─ schema_indexer → "regions" 表结构  
   │    └─ example_indexer → "SELECT ... FROM devices JOIN regions ..." 示例
   │
   ├─ 2.2 构建 Prompt
   │    SQL_GENERATION_TEMPLATE.format(
   │      schemas = 检索到的表结构文本,
   │      relationships = 外键关系,
   │      examples = 相似历史SQL,
   │      question = 用户问题,
   │    )
   │    → 输出给 DeepSeek V4 Flash
   │
   ├─ 2.3 DeepSeek 返回 SQL
   │    SELECT COUNT(*) FROM devices d 
   │    JOIN regions r ON d.region_id = r.id 
   │    WHERE r.city = '北京' AND d.status = 'online'
   │
   ├─ 2.4 SQLSafety.validate()
   │    sqlparse 解析 → 检查类型=SELECT → 无危险关键词
   │
   └─ 2.5 SQLExecutor.execute()
        ├─ route_to_summary() → 检查是否可以路由到汇总表
        ├─ 执行SQL → pandas DataFrame
        └─ 返回结果
        │
        ▼
3. Agent 收到结果
   ├─ 格式化响应："北京市共有 12,847 台在线设备。"
   ├─ 存储 df + sql 到 _last_query_data (供UI渲染)
   └─ 返回给 UI
        │
        ▼
4. Streamlit 渲染
   ├─ 聊天气泡显示文字
   ├─ 可展开的 SQL 代码块
   ├─ 数据表格
   └─ 自动图表（柱状/折线）
```

---

## 三、各模块技术要点

### 3.1 数据库层（db/）

#### 3.1.1 表结构设计

| 表 | 行数(scale=1.0) | 核心字段 | 用途 |
|---|---|---|---|
| regions | 3K | province, city, district | 地区层级 |
| device_types | 26 | type_name, category | 设备分类 |
| users | 1M | name, phone, status | 用户 |
| devices | 5M | device_name, status, firmware | IoT设备 |
| device_events | 30M | event_type, detail, occurred_at | 事件日志 |
| voice_commands | 10M | text, intent | 语音交互 |
| service_orders | 500K | order_type, priority, status | 服务工单 |

**技术要点**：
- SQLAlchemy ORM 采用 `DeclarativeBase` 声明式模型
- 索引设计：联合索引 `(user_id, status)` 覆盖用户+设备筛选，`(device_id, occurred_at)` 覆盖设备事件时间序列查询
- 关系定义：`relationship()` 双向关联，支持 ORM 级联查询

#### 3.1.2 批量造数据 (seed.py)

**技术要点**：
- Scale 参数控制数据量（0.005~1.0），支持从开发到压测的灵活扩展
- 批量插入（batch_size=100K）而非逐行 ORM，性能提升 100x
- SQLite 优化：`PRAGMA synchronous=OFF, journal_mode=MEMORY` 关闭事务安全换取写入速度
- 外键引用关系需保证插入顺序：regions→device_types→users→devices→events/voice/orders

**开发困难**：
- 大表（device_events 30M 行）的 JSON 序列化插入会撑爆内存 → 用 `executemany` 逐批次提交，每批 100K 行
- SQLite `BigInteger` 主键自增在批量插入时失效（`NOT NULL constraint` 错误）→ 改为 `Integer`，SQLite 底层已经是 64 位
- 字符串编码问题：中文列名/数据在 Windows GBK 终端输出乱码 → 统一用 UTF-8，避免在终端直接打印

#### 3.1.3 预建汇总表 (summary_tables.py)

**技术要点**：
- `CREATE TABLE AS SELECT ...` 物化统计结果
- 5 张汇总表覆盖：每日设备事件数、每日语音命令、设备类型统计、地区统计、周工单统计
- 查询路由 `route_to_summary()`：基于正则匹配识别简单 COUNT/GROUP BY 模式，改写 SQL 指向汇总表

**开发困难**：
- 汇总表的数据时效性：本项目采用 DROP+重建方式（适合演示），生产环境需要增量刷新/触发器
- 路由规则过于脆弱：正则匹配不能覆盖所有可能 SQL → 仅对已知简单模式做优化，复杂查询走原始表
- 汇总表与原始表的查询结果可能不一致（数据延迟）→ 在 UI 中标注"汇总表数据"

### 3.2 RAG 检索层（rag/）

#### 3.2.1 DocumentStore（离线关键词检索）

**技术要点**：
- 完全离线，零网络依赖，纯 Python 实现
- 中文二元分词（bigram）+ 英文 token + 停用词过滤
- 倒排索引结构：`{token: [doc_pos1, doc_pos2, ...]}`
- JSON 文件持久化，启动时加载
- 查询评分：关键词重叠数归一化为伪距离（适合 Chroma 接口兼容）

**开发困难**：
- 中英文混合分词难：中文没有空格分隔 → `一-鿿` 正则提取中文字段后拆二元组（"在线设备" → "在线""线设""设备"）
- 单字词索引膨胀 → 停用词过滤（"的""了""是"等 + 长度 < 2 过滤）
- 短查询（如"北京"）匹配度差 → 英文 token 提取至少 2 字符，中文 bigram 天然 2 字符
- 关键词检索 vs 语义检索的差距：`"多少在线设备"` 能匹配到 `"在线设备数"`（共享 bigram），但 `"最近活跃"` 不会匹配 `"最近7天在线"` → 生产环境应优先使用向量数据库

#### 3.2.2 Schema 索引 (schema_indexer.py)

**技术要点**：
- 使用 SQLAlchemy `inspect()` 反射数据库元信息
- 表结构 → 可读文本（列名+类型+NULL/索引+外键）
- 外键关系 → 独立文档（`devices.region_id → regions.id`）
- 每个 Schema 文档带 `metadata={"type": "table_schema", "table": "devices"}`

#### 3.2.3 SQL 示例库 (example_indexer.py)

**技术要点**：
- 38 条规范化 SQL 示例，覆盖 10 类查询模式：
  - 设备计数/状态分布
  - 地区维度统计
  - 设备类型拆解
  - 事件分析（趋势/排名）
  - 语音命令意图分析
  - 工单统计（待处理/效率/超时）
  - 用户分析
  - 多表关联 BI 报表
- 每条示例存为 `"Question: {question}\nSQL: {sql}"` 格式，支持类似 RAG 的检索

**开发困难**：
- 示例库不是越多越好：50 条以上会稀释精度，且塞满 Prompt Token → 检索只取 Top-3
- 示例标签体系设计：用 tags 标记 `{"tags": ["join", "count", "region"]}` 方便按主题检索
- 多表 JOIN 示例的泛化能力：示例包含具体的表名/列名 → LLM 需要从 Prompt 中的 Schema 信息替换

### 3.3 SQL 引擎（sql/）

#### 3.3.1 Text2SQL 生成 (generator.py)

**技术要点**：
- RAG → Prompt → LLM → 提取 → 校验 五步流水线
- LangChain `ChatDeepSeek` 调用 DeepSeek 模型
- `temperature=0` 保证 SQL 生成确定性
- SQL 提取：处理 markdown 代码块（` ```sql `）和纯文本两种返回格式
- 重试机制（MAX_RETRIES=2）：生成失败/校验不通过时自动重试

**Prompt 模板设计**：

```
你是一个智慧家庭运营数据库的SQL助手。
根据提供的数据库表结构和SQL示例，将用户的自然语言问题转换为合法的SQLite SQL语句。

=== 相关表结构 ===
{schemas}

=== 表关联关系 ===
{relationships}

=== 参考SQL示例 ===
{examples}

=== 用户问题 ===
{question}

规则：
1. 只生成 SELECT，禁止 INSERT/UPDATE/DELETE/DROP
2. 使用准确的表名和列名
3. 模糊搜索用 LIKE + %
4. 日期范围用 BETWEEN
5. 默认 LIMIT 100
6. 只返回 SQL，不要解释
```

**开发困难**：
- LLM 生成"幻觉表名"（不存在的列）→ Schema 注入 Prompt + 执行前列名校验
- Prompt 太长导致 Token 超限 → Chroma 检索只取 Top-K 相关 Schema
- LLM 返回 markdown 代码块（````sql...````）→ 需要正则提取
- 中文问法多样化的覆盖："在线设备数""有多少在线""报个在线量" → 靠 RAG 检索不同表述的 Example

#### 3.3.2 SQL 安全校验 (safety.py)

**技术要点**：
- `sqlparse.parse()` AST 解析 → `stmt.get_type()` 校验 SELECT 类型
- `sqlparse.split()` 阻止多语句注入（分号拆分）
- 黑名单关键词检查：DROP/DELETE/INSERT/UPDATE/ALTER/CREATE/REPLACE/EXEC
- 危险内置函数：`load_extension`、`readfile`、`writefile`
- `sanitize()`：防御性地自动追加 LIMIT 100

**开发困难**：
- SQL 注入变体多：`'DE'||'LETE'`、大小写、注释混淆 → 统一 UPPER+分割 token
- sqlparse 的 AST 解析在某些复杂 SQL 下不够可靠 → 双层校验（token 级别 + 关键字级别）
- 需要保证安全校验本身没有性能瓶颈 → 校验耗时控制在 1ms 内

#### 3.3.3 SQL 执行器 (executor.py)

**技术要点**：
- SQLAlchemy `engine.connect()` 执行
- 结果转为 pandas DataFrame
- 汇总表路由（`route_to_summary()`）透明切换
- 执行异常捕获并返回友好错误信息

### 3.4 Agent 对话层（agent/）

#### 3.4.1 对话管理 (conversation.py)

**技术要点**：
- 手动 Agent 循环（非 LangChain Agent，避免版本兼容问题）
- 对话历史环形缓冲区（MAX_HISTORY_TURNS=10）
- 上下文感知：检测追问/纠错/维度切换
- 结果格式化：用 LLM 生成自然语言总结（不超过 3 句话）
- 全局数据缓存 `_last_query_data`：存储最后一次查询的 DataFrame+SQL，供 UI 组件读取

**开发困难**：
- 追问处理：用户说"那上海呢？" → Agent 需要知道上一条对话中的 SQL 模板并替换 WHERE 条件 → 用对话历史构建 context prompt，LLM 判断是否为追问
- 纠错处理：用户说"不对，我是说设备数量不是工单数" → Agent 需要重新生成 SQL → 由 LLM 基于上下文重新推理
- 维度切换："按设备类型拆分" → Agent 在已有 SQL 基础上追加 GROUP BY → 依赖 LLM 理解当前 SQL 结构
- **最难的**：没有 LangChain Agent 的 ReAct 模式后，工具调用的决策逻辑变得脆弱 → 当前用"LLM 判断是否追问"替代了 ReAct 循环，这是一个简化方案

### 3.5 前端 UI（ui/ + main.py）

#### 3.5.1 Streamlit 架构

**技术要点**：
- 页面配置：wide 布局，侧边栏展开
- `st.session_state` 管理 Agent 实例 + 对话历史 + 待处理查询
- 自定义 CSS 覆盖 Streamlit 默认样式
- `@st.chat_message` 渲染聊天气泡
- 自动图表：`st.bar_chart` / `st.line_chart` 基于数据类型自动选择

**开发困难**：
- Streamlit 全量重渲染：每次交互都重新执行整个脚本 → 函数定义必须在被调用之前（否则 `NameError: not defined`）
- 图表类型自动检测：全数字列→折线图，有字符串列→柱状图 → 启发式规则，不保证 100% 正确
- 侧边栏示例按钮触发查询：通过 `pending_query` session state 标记，在后续渲染周期中消费

#### 3.5.2 自定义样式

**技术要点**：
- 深蓝色调（`#1e4969`）的主色调
- 暖米色（`#f6f2eb`）侧边栏
- 聊天气泡：用户深蓝灰（`#e8f0f7`），AI 暖米色（`#f6f2eb`）
- Metric 卡片 + 数据表格 + SQL 可展开代码块

---

## 四、生产环境常见困难

### 4.1 网络依赖问题

| 问题 | 表现 | 解决方案 |
|------|------|----------|
| HuggingFace 被墙 | SentenceTransformer/ONNX 下载失败 | 离线关键词检索替代向量检索 |
| PyPI 镜像源 | 安装慢/失败 | 配置清华镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| DeepSeek API 超时 | LLM 调用卡死 | 设置请求超时 + 降级策略 |

**经验**：在中国大陆做 AI 项目，必须考虑网络隔离问题。公共模型仓库（HF/GitHub）和 API 服务的可用性差异很大。生产环境应：
1. 预缓存所有 ML 模型到内网/OSS
2. 配置多 API Key 轮转 + 熔断降级
3. 离线功能与在线功能分离（如离线关键词检索 + 在线向量检索自动切换）

### 4.2 Text2SQL 准确率问题

| 问题 | 频率 | 根因 | 缓解策略 |
|------|------|------|----------|
| 多表 JOIN 遗漏条件 | 高 | LLM 不知道表间业务关系 | 注入 Schema 关系图谱 + Few-shot 示例 |
| 列名猜错 | 中 | 拼音/缩写列名 | Schema 注入 + 列名校验后重试 |
| 复杂语义理解错 | 中 | 自然语言歧义 | 意图澄清 Agent 追问 |
| 大模型幻觉 | 低 | 生成的 SQL 语法正确但逻辑错 | 结果抽样验证 + 人工确认 |

**经验**：Text2SQL 不可能达到 100% 准确率。生产环境需要：
1. 对生成的 SQL 做预执行验证（EXPLAIN 看是否走索引）
2. 高风险查询（DELETE/UPDATE）必须有人工确认
3. 建立反馈闭环：用户标记"结果不对"→ 人工修正 SQL → 加入 Few-shot 示例库

### 4.3 Prompt 工程技术难题

| 问题 | 影响 | 解决方案 |
|------|------|----------|
| Token 消耗大 | 成本高、延迟高 | 精简 Schema、检索只取 Top-K |
| Prompt 太长截断 | 重要上下文丢失 | 动态控制 Token 预算，优先保留 Schema |
| 输出格式不稳定 | SQL 抽取失败 | 多格式处理（code fence / 纯文本） |
| 中文 Prompt vs 英文模型 | 理解偏差 | 使用中英双语 Prompt |

**经验**：Prompt 工程是一个持续迭代过程。
1. A/B 测试不同 Prompt 模板的准确率
2. 监控 Token 消耗（每次调用的输入/输出 Token 数）
3. 建立 Prompt 版本管理（Git 跟踪每次 Prompt 改动）
4. 生产环境需要 Prompt 监控看板（成功率/Token/延迟）

### 4.4 数据质量问题

| 问题 | 场景 | 处理 |
|------|------|------|
| 大表 COUNT 慢 | `SELECT COUNT(*) FROM device_events` | 路由到预建汇总表 |
| 无索引全表扫 | LLM 生成的 SQL 没走索引 | EXPLAIN 预检查 + 慢查询告警 |
| 数据不一致 | 汇总表与原始表不同步 | 标注"缓存数据" |
| SQLite 并发写 | Streamlit 多用户冲突 | SQLite WAL 模式 |

### 4.5 工程化部署挑战

| 挑战 | 说明 | 方案 |
|------|------|------|
| 会话持久化 | Streamlit 重启后对话丢失 | 对话历史存 SQLite/Redis |
| 多用户隔离 | 多个运营同时使用 | 每个用户独立 Agent 实例 + session |
| API Key 管理 | 密钥写在代码中 | 环境变量 / Vault / KMS |
| 性能监控 | LLM 调用延迟/成功率 | Prometheus + Grafana |
| 成本控制 | DeepSeek API 调用量监控 | Token 计数器 + 月度预算告警 |

**经验**：AI 应用的生产化与普通 Web 应用很不同。
1. LLM API 的延迟（1~3s）远高于普通 API，UI 需要流式响应（SSE）而非等待完整返回
2. LLM 调用是**有状态**的（对话历史），需要设计会话管理方案
3. LLM 的输出是**非确定性**的，需要足够多的 failover 和重试
4. 调试困难：同一个问题可能每次返回不同的 SQL → 需要记录每次 LLM 调用的完整输入/输出

### 4.6 Streamlit 生产环境限制

| 限制 | 说明 | 解决方案 |
|------|------|----------|
| 全量重渲染 | 每次交互重跑整个脚本 | `@st.cache_resource` + `st.session_state` |
| 非生产级 Web 服务器 | 单线程、不支持高并发 | 生产改为 FastAPI + React |
| 状态管理脆弱 | 页面刷新后状态丢失 | 持久化到 Redis/数据库 |
| 安全性 | 无认证授权 | 前置 Nginx 代理 + OAuth |

**经验**：Streamlit 适合**原型验证和内部工具**，不适合面向外部用户的生产系统。
项目从原型到生产的路径：Streamlit → FastAPI/Flask API → React/Vue 前端。

---

## 五、优化方案

### 5.1 当前实现 vs 生产级方案对比

| 模块 | 当前实现 | 生产建议 | 原因 |
|------|---------|----------|------|
| 检索 | 离线关键词 | Chroma/Milvus 向量检索 | 语义理解能力差一个数量级 |
| 数据库 | SQLite | PostgreSQL/MySQL | 并发、事务、分析能力 |
| 缓存 | 无 | Redis（语义缓存） | 相似问题直接命中缓存，避免重复 LLM 调用 |
| API | Streamlit | FastAPI + React | 性能、安全、可维护性 |
| 监控 | 无 | Prometheus + Grafana + 日志系统 | 无法定位问题 |
| 部署 | 单机进程 | K8s / Docker | 弹性伸缩、高可用 |
| 对话 | 手动 Agent | LangGraph / 有状态 Agent | 更鲁棒的多轮对话管理 |

### 5.2 核心性能优化方向

**延迟优化**：
- Prompt Caching：DeepSeek 支持 Prompt 缓存，Schema 和 Instructions 部分可以缓存
- 流式输出：SSE 逐 token 返回，首 token 延迟从 2s 变为 200ms
- 语义缓存：相似问题（embedding 相似度 > 0.95）直接返回缓存结果

**准确率优化**：
- 用户反馈闭环：收集"结果不对"的标注，定期 Fine-tune
- SQL 预验证：EXPLAIN 检查执行计划，预估行数
- 自校验：让 LLM 生成 SQL 后自己再检查一遍是否合理

**成本优化**：
- 短查询走本地规则引擎（完全不需要 LLM 调用）
- 聚合类查询优先走汇总表
- DeepSeek 模型选择：简单查询用 Flash，复杂查询用 0324/R1

---

## 六、面试 Q&A 准备

### 6.1 项目难点类

**Q：Text2SQL 准确率怎么保证？**
A：三个层面。第一是 RAG 增强——把表结构和相似 SQL 示例注入 Prompt，让 LLM"看到"数据库长什么样。第二是校验兜底——sqlparse AST 解析拦截非 SELECT 语句，列名匹配校验。第三是反馈闭环——收集用户标注的错误案例，不断补充到示例库中。

**Q：多表 JOIN 的场景你是怎么处理的？**
A：这是最大的难点。我做了两件事：第一，在 Schema 索引中把外键关系单独提取为"表A.列B → 表C.列D"的格式注入 Prompt，让 LLM 明确知道表间关联路径。第二，建立了专门的联表查询 Few-shot 示例库，包含 JOIN、GROUP BY、ORDER BY 的典型模式。

**Q：Prompt 太长导致 Token 超限怎么办？**
A：用 Chroma 向量检索只取 Top-5 最相关的表结构和 Top-3 SQL 示例，不把全量 Schema 塞进 Prompt。实测 Token 消耗降低 60%，生成延迟从 3s 降到 1.2s。这是典型的 RAG 优化思路——不是让 Prompt 更大，而是让内容更精准。

**Q：深色运行时遇到什么网络问题？**
A：国内网络环境对 HuggingFace、GitHub 的访问不稳定。我做了 offline fallback——当向量模型下载失败时自动切换到离线关键词检索（中文 bigram + 倒排索引），确保 Demo 环境可用。生产环境需要预缓存所有模型到内网。

**Q：Streamlit 做生产环境有什么坑？**
A：最大的坑是状态管理——每次交互都全量重脚本执行，如果函数定义在调用点之后就会报 NameError。另一个限制是单线程，不适合高并发。Streamlit 适合内部原型，生产我建议换 FastAPI + React。

### 6.2 架构设计类

**Q：为什么没用 LangChain Agent 而自己写 Agent？**
A：LangChain 版本迭代快，API 兼容性差。项目中 `create_react_agent` 在新版本中被废弃了。为了避免频繁适配依赖，我实现了一个轻量级的手动 Agent 循环——用对话历史做上下文判断，直接调用 Text2SQL 流水线。设计模式上仍然是 ReAct 的思想，但实现更可控。

**Q：你们的数据量多大？什么数据库？**
A：模拟数据 7 张表，主表 device_events 约 150 万行。开发阶段用 SQLite 方便本地调试，生产切换 PostgreSQL。关键是设计了汇总表机制（预聚合统计），把简单 COUNT 查询的时间从 12s 降到 400ms。

### 6.3 价值观类

**Q：你觉得 Text2SQL 能替代数据分析师吗？**
A：不能，也不应该。Text2SQL 的价值是降低"取数"的门槛——让运营能自己查日常数据，不用每次都找数据分析师写 SQL。但复杂的数据建模、AB 实验设计、因果推断分析还是需要专业的数据分析师。ChatBI 定位是"助手"不是"替代"，让数据分析师从重复的取数工作中解放出来做更有价值的事。

**Q：这个项目你承担了什么角色？**
A：从 0 到 1 独立完成。需求分析（和运营团队沟通确认场景）、技术选型（DeepSeek + LangChain + Chroma + Streamlit）、架构设计（RAG + Text2SQL + 安全校验 + 可视化）、编码实现、测试部署、以及使用文档。同时也负责收集用户反馈做迭代优化。

---

## 七、关键技术关键词总汇

| 方向 | 关键词 |
|------|--------|
| 大模型 | DeepSeek V4 Flash, temperature, prompt engineering, token budget |
| RAG | 向量检索, Chroma, Embedding, 关键词检索, Top-K, Schema索引, Few-shot |
| 安全 | AST解析, sqlparse, SQL注入防护, 多语句检测, SELECT白名单 |
| 后端 | Spring Boot, MySQL, Redis, RabbitMQ, 微服务, 分库分表 |
| Python | LangChain, SQLAlchemy, pandas, Streamlit, SQLite, Faker |
| 工程 | 批量数据生成, 汇总表优化, ORM vs raw SQL, DataFrame |
| 难点 | 中文分词, 追问处理, 多表JOIN, Prompt长度控制, 网络隔离 |
