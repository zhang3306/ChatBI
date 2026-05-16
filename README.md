<p align="center">
  <img src="docs/banner.png" alt="ChatBI" width="600"/>
</p>

<h1 align="center">ChatBI - 智慧家庭AI运营系统</h1>

<p align="center">
  <strong>自然语言 → SQL → 数据 → 洞察</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/LLM-DeepSeek V4 Flash-green" alt="DeepSeek"/>
  <img src="https://img.shields.io/badge/RAG-Keyword%20Retrieval-orange" alt="RAG"/>
  <img src="https://img.shields.io/badge/UI-Streamlit-red?logo=streamlit" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License"/>
</p>

---

## 简介

**ChatBI** 是一款基于 Text2SQL + RAG + Agent 技术的对话式数据分析平台。运营人员用自然语言提问，系统自动将问题转为 SQL、执行查询、返回可视化结果——替代了「找数据 → 写 SQL → 做报表」的冗长流程。

### 核心能力

| 能力 | 说明 |
|------|------|
| **Text2SQL** | NL → SQL 自动转换，支持多表 JOIN、聚合、时间序列 |
| **RAG 增强检索** | 检索表结构 + SQL 示例注入 Prompt，提升生成准确率 |
| **SQL 安全校验** | AST 解析三层拦截，只允许 SELECT，杜绝注入风险 |
| **多轮对话** | 追问、纠错、维度切换，对话式交互体验 |
| **查询优化** | 预建汇总表 + 查询路由，大表 COUNT 从 12s→400ms |
| **数据可视化** | 自动识别数据类型，生成表格 + 柱状图 / 折线图 |

### 技术栈

```
LLM:      DeepSeek V4 Flash
框架:     LangChain, SQLAlchemy
检索:     ChromaDB 向量检索（首选） / 离线关键词 fallback
安全:     sqlparse AST 解析
数据:     SQLite + pandas DataFrame（可扩展至 PostgreSQL）
前端:     Streamlit
语言:     Python 3.10+
```

---

## 快速开始

### 前置条件

- Python 3.10+
- [DeepSeek API Key](https://platform.deepseek.com/)

### 安装

```bash
# 1. 克隆
git clone https://github.com/zhang3306/chatbi.git
cd chatbi

# 2. 安装依赖
pip install -r requirements.txt

# 3. (可选) 安装 ChromaDB 以启用语义检索
pip install chromadb  # ~80MB ONNX 模型首次使用自动下载

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 5. 生成模拟数据
python run.py --seed

# 6. 构建 RAG 索引
python run.py --index

# 7. 启动
python -m streamlit run main.py
```

启动后浏览器访问 **http://localhost:8501**，点击「初始化系统」即可开始对话。

---

## 项目结构

```
chatbi/
│
├── main.py                  # Streamlit 入口
├── config.py                # 统一配置
├── run.py                   # 一键运行（seed / index / ui）
│
├── db/                      # 数据库层
│   ├── models.py            # ORM 模型（7 张运营数据表）
│   ├── engine.py            # SQLAlchemy 引擎
│   ├── seed.py              # 千万级模拟数据生成器
│   └── summary_tables.py    # 预建统计汇总表 + 查询路由
│
├── rag/                     # RAG 检索层
│   ├── vector_store.py      # 检索器切换（离线 / 向量）
│   ├── store_offline.py     # 离线关键词检索（中文 bigram + 倒排索引）
│   ├── schema_indexer.py    # 表结构索引
│   ├── example_indexer.py   # 38 条 SQL 示例库索引
│   └── retriever.py         # 统一检索器
│
├── sql/                     # SQL 引擎
│   ├── safety.py            # SQL 安全校验（AST 解析三层拦截）
│   ├── generator.py         # Text2SQL 生成（RAG→Prompt→LLM→校验→重试）
│   └── executor.py          # SQL 执行 + 汇总表路由
│
├── agent/                   # Agent 对话层
│   ├── tools.py             # 工具函数 + 查询结果缓存
│   └── conversation.py      # 多轮对话管理（追问 / 纠错 / 维度切换）
│
├── prompts/                 # Prompt 模板
│   └── templates.py         # SQL 生成 / 意图澄清 / 结果格式化
│
├── ui/                      # 前端组件
│   ├── components.py        # 聊天气泡、数据表格、图表、SQL 展开
│   └── styles.py            # 自定义 CSS 样式
│
├── scripts/
│   └── index.py             # RAG 索引构建脚本
│
└── docs/                    # 文档
    ├── banner.png           # 项目横幅
    ├── study-guide.md       # 完整技术学习指南
    └── technical-deep-dive.md  # 技术深度解读
```

---

## 数据流

```
用户输入 → Agent → RAG 检索(Schema + Example) → Prompt 构建 → DeepSeek
  → SQL 生成 → AST 安全校验 → 汇总表路由? → SQLite 执行
  → DataFrame → LLM 格式化 → 聊天气泡 + 表格 + 图表
```

### 示例对话

| 轮次 | 用户 | ChatBI |
|------|------|--------|
| 1 | 北京有多少在线设备？ | 12,847 台 → 柱状图 |
| 2 | 那上海呢？ | 追问识别 → 9,632 台 |
| 3 | 按设备类型拆分 | 维度切换 → GROUP BY → 分类图 |

---

## 数据库设计

| 表 | 行数 (scale=1.0) | 说明 |
|----|-----------------|------|
| `regions` | 3K | 地区层级（省 / 市 / 区） |
| `device_types` | 26 | 设备分类（照明 / 安防 / 娱乐 / 家电） |
| `users` | 1M | 用户信息 |
| `devices` | 5M | IoT 设备（状态 / 固件 / 归属） |
| `device_events` | 30M | 事件日志（开关 / 告警 / 升级） |
| `voice_commands` | 10M | 语音交互（意图 / 响应） |
| `service_orders` | 500K | 服务工单（维修 / 安装 / 投诉） |

数据量通过 `--scale` 参数控制：

```bash
python -m db.seed --scale 0.01    # 46 万行（开发调试）
python -m db.seed --scale 0.1     # 460 万行（集成测试）
python -m db.seed --scale 1.0     # 4600 万行（全量）
```

---

## 技术难点

| 难点 | 解决方案 |
|------|----------|
| 多表 JOIN 生成不准 | 外键关系单独注入 Prompt + 联表 Few-shot 示例库 |
| 中文问法多样化 | RAG 检索不同表述的 Example（"在线数"/"报个数"/"查状态"） |
| SQL 注入风险 | sqlparse AST 三层校验（类型 / 多语句 / 黑名单） |
| 大表 COUNT 延迟 | 预建 5 张汇总表 + 正则路由，30 倍性能提升 |
| Prompt 超长 | RAG 只取 Top-K 相关 Schema 和 Example，Token 降 60% |
| 追问 / 纠错 | 对话历史环形缓冲区 + LLM 上下文判断 |
| 网络隔离 | 离线关键词检索 fallback，零网络依赖 |

---

## 生产优化方向

| 优化 | 预期收益 | 实现方式 |
|------|---------|----------|
| 向量检索升级 | 检索精度提升 50%+ | Chroma / Milvus 替代关键词检索 |
| 数据库迁移 | 支持高并发、ACID | PostgreSQL 替代 SQLite |
| 语义缓存 | 50% 查询免 LLM 调用 | Redis + embedding 相似度匹配 |
| Prompt Caching | 首 token 延迟 2s→400ms | DeepSeek 原生 Prompt 缓存 |
| 流式输出 (SSE) | 首 token 延迟 200ms | FastAPI + EventSource |
| EXPLAIN 预检 | 防止慢查询打挂 DB | SQLite EXPLAIN 执行计划分析 |
| Docker 部署 | 一键部署、环境隔离 | Dockerfile + docker-compose |

---

## 许可

MIT License — 详见 [LICENSE](LICENSE)

## 作者

**张玉生** · AI 应用开发工程师

- GitHub: [@zhang3306](https://github.com/zhang3306)
- Email: 470443696@qq.com
