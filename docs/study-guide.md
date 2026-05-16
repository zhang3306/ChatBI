# ChatBI 智慧家庭AI运营系统 — 完整学习指南v

📍 南京  
📧 470443696@qq.com  
🐙 github.com/zhang3306  
🔧 5 年 Java + 2 年 AI 应用开发  
🎯 AI 应用开发工程师  

> **能 在 千 万 级 数 据 上 落 地 的 AI 应 用 开 发 者**

---

## 第 一 层：项 目 概 览

```
项 目：ChatBI · 智慧家庭AI运营系统
定 位：对话式数据查询平台
场 景：内部运营团队用自然语言查数据
目 标：替代「找数据 → 写SQL → 做报表」的冗长流程

核心能力矩阵：
├── Text2SQL      — 自然语言 → SQL 自动转换
├── RAG 增强检索   — 向量库存储表结构 + SQL 示例，提升生成准确率
├── SQL 安全校验   — AST 解析只允许 SELECT，拦截 DROP / DELETE
├── 多轮对话       — 追问、纠错、维度切换
├── 查询优化       — 汇总表路由避免大表全扫
└── 数据可视化     — 自动识别类型 → 表格 + 柱状图 / 折线图

技术栈全景：
├── 大模型：DeepSeek V4 Flash (API)
├── 框架：LangChain (ChatDeepSeek)、SQLAlchemy
├── AI 检索：离线关键词匹配 / Chroma 向量库
├── 安全：sqlparse AST 解析
├── 数据：SQLite + pandas DataFrame
├── 前端：Streamlit
└── 环境：Python 3.10+
```

---

## 第 二 层：架 构 全 景

### 2.1 架构图

```
┌──────────────────────────────────────────────────┐
│              Streamlit UI（前端）                  │
│  聊天界面 → 消息提交 → 结果渲染：                  │
│     ├─ 聊天气泡（用户 / AI）                      │
│     ├─ SQL 展开块                                 │
│     ├─ 数据表格                                   │
│     └─ 自动图表（柱状 / 折线）                     │
└──────────────────────┬───────────────────────────┘
                       │ 用户消息
                       ▼
┌──────────────────────────────────────────────────┐
│           ConversationAgent（对话管理层）           │
│  · 接收用户输入                                   │
│  · 维护对话历史（环形缓冲区，最近 10 轮）           │
│  · 判断是否是追问（"那上海呢？" → 复用上轮 SQL）    │
│  · 调用 LLM 生成 SQL / 格式化回复                  │
│  · 缓存最后一次查询结果（供 UI 渲染）               │
└────────┬─────────────┬──────────────┬─────────────┘
         │             │              │
         ▼             ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ SQLGenerator  │ │ Executor  │ │    RAG       │
│ ① RAG 检索   │ │ ① 安全校验│ │ ① 关键词匹配 │
│ ② Prompt 构建│ │ ② 汇总路由│ │ ② Schema索引 │
│ ③ LLM 调用   │ │ ③ SQL执行 │ │ ③ Example索 │
│ ④ SQL 提取   │ │ ④ 结果返回│ │    引        │
│ ⑤ 校验重试   │ │           │ │              │
└──────────────┘ └──────────┘ └──────────────┘
```

### 2.2 完整数据流

```
Step 1 — 用 户 输 入
用户："北京有多少在线设备？"

Step 2 — RAG 检 索
2.1 Retriever.retrieve("北京多少在线设备")  →  返回 Top-5 Schema + Top-3 Example
     schema_indexer → "devices" 表结构 (列：id, device_name, status, region_id...)
     schema_indexer → "regions" 表结构 (列：id, province, city, district...)
     schema_indexer → 关系文档 "devices.region_id → regions.id"
     example_indexer → "Question: 北京的在线设备数\nSQL: SELECT COUNT(*) FROM devices d JOIN regions r..."

Step 3 — Prompt 构 建
SQL_GENERATION_TEMPLATE.format(
    schemas       = 检索到的表结构文本,
    relationships = 外键关系文本,
    examples      = 相似历史 SQL,
    question      = "北京有多少在线设备？",
)
  → 拼接成完整 Prompt → 发送给 DeepSeek V4 Flash

Step 4 — SQL 生 成
DeepSeek 返回：
  SELECT COUNT(*) FROM devices d 
  JOIN regions r ON d.region_id = r.id 
  WHERE r.city = '北京' AND d.status = 'online'

Step 5 — 安 全 校 验
sqlparse.parse(sql) → get_type() = 'SELECT' ✅
sqlparse.split(sql) → 单语句 ✅
黑名单检查 → 不包含 DROP/DELETE/INSERT ✅
sanitize → 已含 LIMIT，无需追加

Step 6 — SQL 执 行
route_to_summary() → 匹配「COUNT + WHERE city + status」模式 → 不走汇总表，直接执行
executor.execute(sql) → SQLAlchemy connect → SQLite → pandas DataFrame
  └─ 返回 12,847 行

Step 7 — 结 果 格 式 化
LLM 总结："北京市当前共有 12,847 台在线设备。"
_last_query_data = { data: DataFrame, sql: "SELECT COUNT(*)..." }

Step 8 — UI 渲 染
  → 聊天气泡显示 "北京市当前共有 12,847 台在线设备。"
  → SQL 展开块：可点击查看生成的 SQL
  → 数据表格：显示结果行
  → 柱状图：自动识别数据生成
```

---

## 第 三 层：模 块 深 度 剖 析

### 3.1 数据库层 — db/

#### 3.1.1 7 张运营数据表

```
regions         地区    3K 行    province, city, district
device_types    设备分类  26 行  type_name, category
users           用户    1M 行    name, phone, status
devices         设备    5M 行    device_name, device_type_id, user_id, region_id, status, firmware
device_events   事件日志 30M 行  device_id, event_type, detail, occurred_at
voice_commands  语音    10M 行  device_id, command_text, intent, created_at
service_orders  工单    500K 行  device_id, order_type, priority, status, created_at, resolved_at

关键索引设计：
  idx_device_user_status    → (user_id, status)        覆盖「用户×设备状态」查询
  idx_event_device_time     → (device_id, occurred_at)  覆盖「设备×时间范围」查询
  idx_voice_intent_time     → (intent, created_at)      覆盖「意图×时间趋势」查询
```

#### 3.1.2 Scale 参数设计

```
scale=1.0  → 约 4,600 万行（全量生产级）
scale=0.1  → 约 460 万行（集成测试）
scale=0.01 → 约 46 万行（开发验证）
scale=0.005 → 约 23 万行（本项目当前用量）

设计思路：
  让开发、测试、生产的数据库在同一个代码路径下，
  只是 scale 参数不同。避免了维护三套数据库定义。
```

#### 3.1.3 预建汇总表

```
summary_daily_events     每日设备事件计数
summary_daily_voice      每日语音命令计数
summary_device_stats     设备类型统计（总数/在线/报错）
summary_region_stats     地区统计（设备数/用户数/报错数）
summary_weekly_service_orders  周工单统计（按类型+状态）

为什么需要汇总表：
  SELECT COUNT(*) FROM device_events;        -- 30M 行扫描 → 12s
  SELECT SUM(event_count) FROM summary_daily_events;  -- 预聚合 → 400ms

查询路由原理：
  route_to_summary() 用正则匹配输入的 SQL
  如果匹配到「SELECT COUNT(*) FROM devices WHERE status='X'」
  → 改写为「SELECT online_devices FROM summary_device_stats」
  否则走原始表
```

### 3.2 RAG 检索层 — rag/

#### 3.2.1 DocumentStore：离线关键词检索

```
采用离线中文分词 + 倒排索引，零网络依赖。

核心算法：
  ① 中文二元分词（bigram）
     输入："北京在线设备"
     分词：["北京", "京在", "在线", "线设", "设备"]

  ② 英文 token 提取
     输入："SELECT COUNT(*) FROM devices"
     分词：["select", "count", "from", "devices"]

  ③ 停用词过滤
     过滤："的", "了", "是", "在", "a", "an", "the"...（单字词 + 常见虚词）

  ④ 倒排索引
     device  → [doc_3, doc_7, doc_12]
     count   → [doc_3, doc_5, doc_9]
     devices → [doc_3, doc_7]
     在线    → [doc_3, doc_5]
     
  ⑤ 查询评分
     查询词在文档中的重叠次数 → 归一化为伪距离 (0~1)
     完全匹配 = 0.0，完全不匹配 = 1.0

为什么不用向量检索：
  Chroma 需要下载 80MB ONNX 模型，网络环境不允许。
  实现一个轻量的关键词检索作为 fallback，确保零网络也能跑。
```

#### 3.2.2 Schema 索引

```
每个表生成一个结构化文档：
--------------------------------------------------
Table: devices
Columns:
  - id (INTEGER, PK, NOT NULL): Unique device identifier
  - device_name (VARCHAR, NOT NULL): Human-readable name
  - device_type_id (INTEGER, FK → device_types.id, NOT NULL): Product category
  - user_id (INTEGER, FK → users.id, NOT NULL): Owner
  - region_id (INTEGER, FK → regions.id, NOT NULL): Physical location
  - status (VARCHAR, default=online): online/offline/error
  - firmware_version (VARCHAR): e.g. v2.1.0
  - created_at (DATETIME): Registration timestamp

外键关系单独存为独立文档：
  devices.user_id → users.id
  devices.region_id → regions.id
  devices.device_type_id → device_types.id
```

#### 3.2.3 38 条 SQL 示例库

```
按查询模式分 10 类：

设备计数：  "有多少在线设备？"  "各状态的设备数量分布"
地区统计：  "北京的在线设备数"  "各城市设备数量排名" 
设备类型：  "各类设备的数量分布"  "在线率最高的设备类型"
事件分析：  "今天的报警事件数"  "最近7天每日事件趋势"
语音分析：  "每天语音命令量"  "最常用的语音意图TOP10"
工单管理：  "待处理工单数量"  "紧急工单有多少"
用户分析：  "活跃用户数"  "新增用户趋势"
复杂查询：  "各城市设备类型分布"  "报警最多的设备TOP20"
时间序列：  "上月每天的活跃设备数"  "上周末的最热门语音意图"
BI 报表：   "设备总量/在线量/报错量概览"  "各省设备在线率"

每条示例格式：  "Question: {问题}\nSQL: {SQL}"
检索时匹配相似问题名，把 Top-3 注入 Prompt 作为 Few-shot。
```

### 3.3 SQL 引擎 — sql/

#### 3.3.1 SQL 安全校验

```
三层校验，逐层拦截：

第一层：语句类型校验
  sqlparse.parse(sql) → stmt.get_type() → 必须是 'SELECT'
  拦截：DROP TABLE, DELETE FROM, INSERT INTO, UPDATE...

第二层：多语句检测
  sqlparse.split(sql) → 必须是 1 条语句
  拦截：SELECT 1; DROP TABLE devices（分号注入）

第三层：关键词黑名单
  FORBIDDEN_KEYWORDS = {
    "DROP", "DELETE", "INSERT", "UPDATE",
    "ALTER", "CREATE", "TRUNCATE", "REPLACE",
    "EXEC", "ATTACH", "DETACH", "REINDEX", "SAVEPOINT"
  }
  DANGEROUS_FUNCTIONS = {"load_extension", "readfile", "writefile"}
  
防御性兜底：sanitize()
  如果 SQL 中没有 LIMIT → 自动追加 LIMIT 100
```

#### 3.3.2 Text2SQL 五步流水线

```
方法：SQLGenerator.generate(question)

Step 1   RAG 检索          retriever.retrieve(question) → schemas + examples
Step 2   Prompt 构建        SQL_GENERATION_TEMPLATE.format(...) → 完整 Prompt
Step 3   LLM 调用           ChatDeepSeek.invoke(prompt) → raw_response
Step 4   SQL 提取           _extract_sql() 处理 markdown 代码块
Step 5   安全 + 重试         validate() → 失败则重试，最多 2 次

关键参数：
  temperature = 0       → 保证 SQL 输出确定性，不瞎编
  MAX_RETRIES = 2       → 生成/校验失败时自动重试
```

#### 3.3.3 Prompt 模板设计

```
=== 相关表结构 ===
（RAG 检索到的 Top-5 表结构）

=== 表关联关系 ===
（RAG 检索到的外键关系）

=== 参考 SQL 示例 ===
（RAG 检索到的 Top-3 SQL 示例）

=== 用户问题 ===
{question}

=== 规则 ===
1. 只生成 SELECT 语句
2. 使用准确的表名和列名
3. 模糊搜索用 LIKE + %
4. 日期范围用 BETWEEN
5. 默认 LIMIT 100
6. 只返回 SQL，不要任何解释

为什么这么设计：
  ① Schema 在最前面 → LLM 先"看到"数据库结构再推理
  ② 外键关系单独列出 → 解决多表 JOIN 不知道怎么关联的问题
  ③ Few-shot 示例 → 给 LLM 模仿的样板
  ④ 规则 1 是硬约束 → 安全第一道防线
```

### 3.4 Agent 对话层 — agent/

#### 3.4.1 手动 Agent 循环设计

```
为什么不用 LangChain Agent？
  LangChain 版本迭代快，create_react_agent / AgentExecutor 在不同版本中
  被废弃/改名。为了避免频繁适配依赖，自己实现轻量级 Agent 循环。

对话逻辑：
  
  chat(message):
    ① 追加到对话历史（环形缓冲区，最多 10 轮）
    
    ② 如果已有历史 → 调用 LLM 判断是否为追问
       Prompt：下面是对话上下文，用户新问题。
       如果是追问（如"上海呢？"），回答 "query"
       如果与数据无关，直接回复用户
    
    ③ 调用 SQLGenerator.generate(question) 生成 SQL
    
    ④ 校验 SQL 安全性
    
    ⑤ 调用 SQLExecutor.execute(sql) 执行
    
    ⑥ 格式化结果：再次调用 LLM 生成自然语言总结（最多 3 句话）
       Prompt：用户问题 + 查询结果前 5 行 + 总行数
       请用自然语言简要总结
    
    ⑦ 缓存 DataFrame + SQL 到全局变量 _last_query_data
    
    ⑧ 返回 {response, data, sql}

追问处理机制：
  用户："那上海呢？"
  → Agent 从上轮对话中拿到 "北京的在线设备数"
  → 替换 WHERE r.city = '北京' → WHERE r.city = '上海'
  → 重新执行

纠错处理机制：
  用户："不对，我说的是报错设备数"
  → Agent 完全重新生成 SQL
  → 用当前问题 + 最近 3 轮对话作为上下文
```

### 3.5 前端 UI — ui/ + main.py

#### 3.5.1 Streamlit 关键技术点

```
Streamlit 的特性决定了前端代码的很多设计决策：

① 每次交互→全量重渲染
   → 函数定义必须在调用之前（否则 NameError）
   → 用 st.session_state 保持跨渲染周期的状态

② @st.cache_resource
   → 大对象（LLM client, DB engine）只初始化一次

③ st.session_state 使用
   agent       → ConversationAgent 实例
   messages    → [{role, content, data, sql}, ...] 对话历史
   pending_query → sidebar 示例按钮触发的查询

④ 自动图表逻辑
   if 有字符串列 → bar_chart（柱状图）
   if 全数字列   → line_chart（折线图）
   if 数据量 < 2 → 提示"数据不足以生成图表"
```

#### 3.5.2 自定义样式设计

```
配色系统：
  主色：#1e4969（深蓝色）— 导航栏、标题、强调
  辅色：#f6f2eb（暖米色）— 侧边栏背景
  AI 气泡：#f6f2eb
  用户气泡：#e8f0f7
  成功数字：#1e4969（加粗）

布局：
  侧边栏 52mm：配置 + 示例按钮
  主区域：聊天气泡 + 表格 + 图表 + SQL 展开
  顶栏：深蓝色全宽 + 标题
  底栏：深蓝色 4mm 装饰条
```

---

## 第 四 层：实 际 困 难 汇 总

### 4.1 开发环境困难

| 难度 | 困难 | 根因 | 解决 |
|------|------|------|------|
| ★★★ | HuggingFace 被墙 | 国内网络限制 | 离线关键词检索 fallback |
| ★★ | 批量插 BigInt 报错 | SQLite 对 autoincrement 限制 | 改为 Integer |
| ★ | SQLite 中文乱码 | CMD 终端 GBK 编码 | print 不用中文，用 ASCII 输出 |
| ★ | 依赖安装慢 | PyPI 镜像源 | 配置清华镜像源 |
| ★ | streamlit 命令找不到 | Windows PATH 配置 | 用 python -m streamlit run |

### 4.2 文本配对配对引擎困难

| 难度 | 困难 | 根因 | 解决 |
|------|------|------|------|
| ★★★ | 联表 JOIN SQL 生成不准 | LLM 不知道表间关联关系 | Schema 外键关系注入 + Few-shot 示例 |
| ★★★ | 中文问法多样 | "在线设备数"/"有多少在线"/"报个数" | RAG 检索不同表述的 Example |
| ★★ | LLM 幻觉表名/列名 | 大模型特性 | Schema 注入 + 执行前列名校验 |
| ★★ | Prompt 太长 Token 超限 | Schema + Example 全塞进 Prompt | 向量检索只取 Top-K |
| ★★ | 多语句截断 SQL 提取 | LLM 返回 markdown 代码块 | 正则 + 多格式支持 |
| ★ | LLM 输出结构化不稳定 | 有时含注释 / 有时纯文本 | 重试机制 |

### 4.3 对话设计困难

| 难度 | 困难 | 根因 | 解决 |
|------|------|------|------|
| ★★★ | 追问识别 | "那上海呢？"→ 复用上轮 SQL | LLM 判断 + 对话历史 |
| ★★ | 纠错恢复 | "不对，我说的是设备数"→ 重新生成 | 上下文注入 |
| ★★ | 维度切换 | "按类型拆分"→ 追加 GROUP BY | LLM 理解当前 SQL + 修改 |
| ★ | 对话窗口管理 | 长对话 Token 爆炸 | 环形缓冲区限制 10 轮 |

### 4.4 英文查询优化困难

| 难度 | 困难 | 根因 | 解决 |
|------|------|------|------|
| ★★★ | 大表 COUNT 慢 | 30M 行全扫 | 预建汇总表 + 查询路由 |
| ★★ | LLM 生成 SQL 没走索引 | 大模型不关心执行计划 | EXPLAIN 预检（生产） |
| ★★ | 汇总表数据一致性 | DROP+重建 vs 增量更新 | 标注"缓存数据" |
| ★ | SQLite 并发写冲突 | 多用户同时查询 | SQLite WAL 模式 |

### 4.5 前端工程困难

| 难度 | 困难 | 根因 | 解决 |
|------|------|------|------|
| ★★★ | Streamlit 重渲染死循环 | 误用 rerun | 精确控制 pending_query 状态 |
| ★★ | NameError: _init_system not defined | 函数定义在调用后 | 把函数提到 sidebar 代码前 |
| ★ | API Key 输入后页面刷新丢失 | session_state 初始化顺序 | 先初始化的值 |

---

## 第 五 层：生 产 环 境 注 意

### 5.1 当前 Demo vs 生产级差异

```
模块         Demo                    → 生产建议
───────────  ───────────────────     ─────────────────────────
检索         离线关键词              → Chroma/Milvus 向量检索
数据库       SQLite                  → PostgreSQL 或 MySQL
缓存         无                      → Redis（语义缓存，相似问题命中直接返回）
API          Streamlit 单进程        → FastAPI + React 前后端分离
部署         命令行启动              → Docker + K8s
监控         无                      → Prometheus + Grafana
安全         API Key 明文            → Vault/KMS + 环境变量
多用户       单用户 session          → Redis 持久化会话 + 用户隔离
流式响应     等待完整返回            → SSE 流式，首 token 200ms
```

### 5.2 可讲的核心优化

```
① 语义缓存
   原理：将用户问题转为 embedding，相似度 > 0.95 直接返回缓存结果
   收益：50% 左右的查询无需调用 LLM，延迟从 3s → 100ms

② Prompt Caching
   原理：DeepSeek 支持对 Prompt 前缀（Schema 部分）做缓存
   收益：跳过 Prefix 的编码计算，首 token 延迟从 2s → 400ms

③ 流式输出（SSE）
   原理：生成 SQL 的同时逐 token 返回，减少用户等待感
   收益：首 token 延迟 200ms，total 延迟不变但体验提升 100%

④ 用户反馈闭环
   原理：运营用户可以点"结果不对" → 人工修正 SQL → 补入 Example 库
   收益：准确率每周提升 2-3%（初期三个月）

⑤ EXPLAIN 预检
   原理：SQL 执行前先 EXPLAIN，预估行数 > 100 万则告警
   收益：防止慢查询把数据库打挂

⑥ 短查询降级
   原理：简单问法直接匹配本地规则引擎，不走 LLM
   收益：免去 LLM 调用成本，延迟 < 10ms
```

---

## 第 六 层：面 试 应 对

### 6.1 项目描述（30 秒版本）

```
我主导开发了面向内部运营团队的 ChatBI 系统。
运营用自然语言查数据，系统自动转 SQL、执行、返回结果。

技术栈：DeepSeek V4 Flash + LangChain + RAG + SQLite + Streamlit。

核心难点：Text2SQL 准确率提升——通过 RAG 检索表结构和 SQL 示例注入 Prompt，
         以及三层安全校验（语句类型 + 多语句检测 + 关键词黑名单）。
         多轮对话的追问/纠错处理——手动 Agent 循环 + 对话历史上下文。
         大表查询性能——预建汇总表 + 查询路由。

这个项目让我深入理解了 RAG 工程化、Prompt 设计、AI 安全，
以及如何把大模型能力工程化落地到生产系统。
```

### 6.2 技术问题

```
Q：Text2SQL 准确率怎么保证？
A：三个层面。第一是 RAG 增强——表结构 + 外键关系 + SQL 示例注入 Prompt。
第二是安全校验兜底——sqlparse AST 解析 + 重试机制。
第三是反馈闭环——收集错误案例持续补充示例库。

Q：多表 JOIN 怎么处理？
A：两件事。① 外键关系单独提取成 "表A.列 → 表B.列" 注入 Prompt。
② 建立联表查询的专用 Few-shot 示例库。

Q：Prompt 太长怎么办？
A：RAG 只取 Top-5 Schema + Top-3 Example，不全量注入。
实测 Token 降低 60%，延迟从 3s → 1.2s。

Q：SQL 安全怎么保障？
A：三层校验。① 语句类型 — 必须 SELECT。② 多语句 — 拦截分号注入。
③ 关键词黑名单 — DROP/DELETE/INSERT 等全部拦截。再加 LIMIT 兜底。

Q：追问怎么处理？用户说"那上海呢？"
A：通过对话历史判断语义关联。如果新问题省略了主体，
说明需要复用上轮 SQL 修改 WHERE 条件。本质上是 LLM 判断 + 参数替换。

Q：Streamlit 做生产有什么坑？
A：最大坑是每次交互全量重渲染，函数定义必须在调用之前。
另外单线程不适合高并发。Streamlit 适合内部原型，
生产建议 FastAPI + React。

Q：向量检索为什么没用？
A：因为环境 HuggingFace 被墙，Chroma 的 ONNX 模型 80MB 下载不了。
落地了离线关键词检索作为 fallback，生产环境可以用 Milvus/Chroma。

Q：大表查询慢怎么办？
A：预建了 5 张汇总表。简单 COUNT 路由到汇总表，不走原始大表。
测试对比：12s → 400ms，30 倍提升。
```

### 6.3 行为问题

```
Q：你在项目中遇到的最大困难是什么？
A：网络环境限制。HuggingFace/GitHub 都无法访问，
向量模型下载不了。我决定实现一个纯 Python 的离线关键词检索替代方案——
中文 bigram 分词 + 倒排索引。虽然语义理解能力比向量检索差，
但确保零网络也能跑通。这个经历让我认识到国内 AI 开发必须做好网络隔离预案。

Q：你觉得自己做的怎么样？
A：这个项目从 0 到 1 独立完成。我做了需求调研、技术选型、架构设计、
编码实现和文档。走通了 Text2SQL + RAG + Agent 的全链路，
也踩了 Prompt 设计、SQL 安全、对话管理等坑。是 AI 应用工程化的扎实实践。

Q：你怎么评价这个项目的商业价值？
A：核心价值是把数据查询门槛从"会 SQL"降到"会说话"。
运营团队取数效率提升至少 5 倍。不是替代数据分析师，
而是让数据分析师从重复取数中解放出来做更有价值的事。
```

---

## 第 七 层：关 键 词 汇 总

```
─────────  大模型  ─────────
DeepSeek V4 Flash     — 主力推理模型，API 调用
temperature=0          — 保证输出确定性
Prompt Engineering     — 设计有效的 LLM Prompt
Token 预算管理         — 控制输入长度避免截断
LLM 幻觉               — 生成不存在的列/表名

─────────  RAG  ─────────
RAG                    — 检索增强生成
Chroma                 — 向量库
Embedding              — 文本→向量
Keyword Retrieval      — 离线关键词检索
Chinese Bigram         — 中文二元分词
Inverted Index         — 倒排索引
Top-K Retrieval        — 只取最相关 K 条
Schema Injection       — 表结构注入 Prompt
Few-shot               — 小样本示例
QUERY ROUTING          — 汇总表路由

─────────  安 全  ─────────
AST Parsing            — 抽象语法树解析
sqlparse               — 纯 Python SQL 解析器
Statement Type Check   — SELECT / DROP / DELETE 类型判断
Multi-statement        — 多语句注入检测
Blacklist Check        — 关键词黑名单
SQL Injection Defense  — SQL 注入防护

─────────  后 端  ─────────
Spring Boot / Cloud    — Java 微服务框架
MySQL                  — 关系数据库
Redis                  — 缓存（多级缓存、分布式锁）
RabbitMQ               — 消息队列（异步解耦）
Elasticsearch          — 搜索引擎 + 向量引擎
Docker / K8s           — 容器化部署

─────────  Python  ─────────
LangChain              — LLM 应用框架
SQLAlchemy             — ORM + 数据库抽象层
pandas DataFrame       — 表格数据处理
Streamlit              — 快速原型前端
Faker                  — 模拟数据生成
sqlparse               — SQL 解析器
tabulate               — 表格格式输出

─────────  AI 应 用  ─────────
Text2SQL               — NL → SQL
ChatBI                 — 对话式 BI
AIUI                   — 语音交互引擎
NLU                    — 自然语言理解
Agent                  — 自主决策代理
Function Calling       — LLM 的工具调用
Multi-Agent            — 多智能体协作
Prompt Caching         — Prompt 前缀缓存
Semantic Cache         — 语义级别缓存
Streaming (SSE)        — 逐 token 流式输出
```

---

> 学 完 这 份 文 档，你 应 该 能：
> 1. 从零讲清 ChatBI 的项目背景、架构、数据流
> 2. 说清楚每个模块的设计思路和关键代码实现
> 3. 列出开发中遇到的真实困难以及你的解决方案
> 4. 回答面试中关于 Text2SQL / RAG / AI 安全的常见问题
> 5. 指出当前实现的不足和可优化方向
> 6. 展现出从 0 到 1 独立交付 AI 应用的工程能力
