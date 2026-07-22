# LLM 调用约定（ai_bridge）

> 配合写 `generate.py` / `generate_audio.py` 时加载。ai_bridge API 与 edu-data-gen 完全一致——本文件从其 `references/llm-calling.md` 原样移植。

## 一、用 `claude_code` provider（复用 Claude Code 本地鉴权）

```python
from ai_bridge import AIBridge
from ai_bridge.exceptions import RateLimitError, NetworkError, ProviderError, AuthenticationError

client = AIBridge(provider="claude_code", model="sonnet")   # 鉴权自动从 ~/.claude/settings.json 读
resp = client.chat(
    messages=prompt,                  # 纯字符串（也接受 list[Message]）
    system="你是…专家。严格输出 JSON…",
    temperature=0.7,
    max_tokens=4096,
)
text = resp.content                   # 模型原始文本（需自行剥 ```json 代码块再 json.loads）
model_version = resp.model            # 实际模型名 → 写进 _meta.json 的 model_version（G8 可追溯）
```

## 二、关键约定（load-bearing，踩过坑）

1. **provider 注册名是 `claude_code`**（不是 `claude_code_direct`）。ai_bridge 把 `"claude_code"` → `ClaudeCodeDirectProvider`。写错 → `Unknown provider`。
2. **模型用别名** `sonnet` / `opus` / `haiku`（经 `~/.claude/settings.json` 解析为实际模型 id）。本课按 CEFR 调 `max_tokens_by_level`（A1 紧凑、B2 宽松）。
3. **`chat()` 返回 `ChatResponse`**：文本在 `.content`，实际模型在 `.model`。
4. **无内置 JSON mode**：`.content` 是原始文本，`generate.py` 的 `extract_json` 负责剥代码块 + 平衡括号解析（本课已扩展支持顶层数组 `[...]`）。
5. **重试是工具包的职责**（provider 单次请求不自动重试）：`generate_one` 内 `for attempt in range(1, max_retries+1)`，遇 `RateLimitError/NetworkError/ProviderError` 退避 `time.sleep(min(2**attempt,16))`，遇 `AuthenticationError` 直接抛（不可重试，主循环存 state 退码 2）。

## 三、JSON 输出契约

- prompt 末尾固定指令：「只输出 JSON 对象本身（无 markdown、无解释）」。
- system prompt 固定强调「事实正确、适龄、贴合 CEFR 与认知层级；不得编造」。
- `extract_json` 先试 ```` ```json…``` ```` 代码块，否则找首个 `{` 或 `[` 平衡匹配；非 dict/list → 重试。

## 四、定位 ai_bridge（向上走）

工具包脚本的 `_ensure_ai_bridge()` 从自身目录向上找含 `ai_bridge/__init__.py` 的目录，插 `sys.path`。DesignSkills 仓根有 `ai_bridge/`，所以工具包在 `data_gen/` 下能找到。外移时设 `EDU_DATA_GEN_ROOT`。

## 五、反模式

- ❌ 用 LLM 自评的「准确性」当阻断门（主观准确性走人审抽样）。
- ❌ 把全量生产塞进 skill（交付边界止于工具包 + 样本验证）。
- ❌ 每内容点多次 LLM 调用（本课**一节课一次调用**，保曲线连贯 + resume 粒度=一节课）。
