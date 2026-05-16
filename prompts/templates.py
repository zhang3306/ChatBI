"""Prompt templates for Text2SQL, intent clarification, and response formatting."""

SQL_GENERATION = """你是一个智慧家庭运营数据库的SQL助手。根据提供的数据库表结构和SQL示例，将用户的自然语言问题转换为合法的SQLite SQL语句。

=== 相关表结构 ===
{schemas}

=== 表关联关系 ===
{relationships}

=== 参考SQL示例 ===
{examples}

=== 用户问题 ===
{question}

规则：
1. 只生成 SELECT 语句，禁止 INSERT/UPDATE/DELETE/DROP
2. 使用上面表结构中出现的准确表名和列名
3. 模糊搜索使用 LIKE 配合 % 通配符
4. 日期范围使用 BETWEEN
5. 默认添加 LIMIT 100 限制返回行数
6. 只返回SQL语句，不要任何解释

SQL:"""


INTENT_CLARIFICATION = """用户的问题是："{question}"

这个问题的表述存在歧义，以下是一些可能的理解：
{interpretations}

请生成一个友好的追问，帮助澄清用户的真实意图。你的追问应该：
1. 列出2-3种可能的理解
2. 引导用户选择一个
3. 保持在SQL查询可覆盖的范围内

追问:"""


RESPONSE_FORMATTING = """用户问题：{question}
执行的SQL：{sql}
查询结果（前10行）：{preview}
总行数：{row_count}

请用自然语言简要总结查询结果，语气友好干练，不要超过3句话。

总结:"""
