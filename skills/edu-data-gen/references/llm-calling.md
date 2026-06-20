# LLM 调用约定（claude_code_direct）

> 配合 edu-data-gen skill。说明工具包生成脚本如何调大模型。
> 用户指定入口：`ai_bridge/providers/claude_code_direct.py`（`ClaudeCodeDirectProvider`）。它复用 Claude Code 本地鉴权（读 `~/.claude/settings.json` 的 token/base_url/model 别名），零子进程直连 Anthropic 协议后端。

---

## 一、关键事实（易踩坑）

- **provider 注册名是 `claude_code`**（不是 `claude_code_direct`）。`ai_bridge` 的 provider 注册表把 `"claude_code"` 映射到 `ClaudeCodeDirectProvider`。用 `provider="claude_code_direct"` 会报 `Unknown provider`。
- **模型用别名** `sonnet|opus|haiku`（provider 会按 settings.json 解析成真实 model id，并去掉 `[1m]` 这类后缀）。
- `chat()` 返回 `ChatResponse`：文本在 **`.content`**（str），实际模型在 **`.model`**（写入 provenance 做可追溯）。
- `chat()` 的 kwargs：`system`、`temperature`、`max_tokens`（默认 4096）等透传给后端。

---

## 二、标准调用模式

```python
from ai_bridge import AIBridge

client = AIBridge(provider="claude_code", model="sonnet")
resp = client.chat(
    messages=prompt_text,          # str；或多轮用 [Message(role=Role.USER, content=...)]
    system=system_prompt,          # 可选 system
    temperature=0.7,
    max_tokens=2048,
)
text = resp.content                # 模型输出文本
model_used = resp.model            # 实际 model id → provenance.model_version
```

- 一个工具包内 **复用同一个 client**（避免重复建连/重复读 settings）。
- 生成脚本把 `model_used` 写进每条的 `provenance.model_version`（G8 可追溯门查这个字段非空）。

---

## 三、JSON 输出与健壮解析

生成教育数据要求**结构化 JSON**，但模型常包代码块/多余文本。处理：

1. prompt 明确："只返回 JSON，不要 markdown 代码块、不要解释"；并给出目标 JSON 结构（与 schema + file_split 字段分组对齐）。
2. 解析时**先剥离** ```` ```json ... ``` ```` 围栏与首尾非 JSON 文本，再 `json.loads`。
3. 解析失败 → 计入该内容点重试（`max_retries` 内）；重试用更严格的 prompt（强调"仅 JSON"+再附 schema）。
4. 解析成功但**字段不全** → 不直接用，走重试或标失败。

参考实现见 `assets/toolkit-template/generate.py` 的 `extract_json()` 与 `generate_one()`。

---

## 四、模型选型（默认，可改）

用户未定具体选型时（未决项），用以下默认：

| 任务 | 默认模型 | 理由 |
|---|---|---|
| 生成内容（material/explanation/item） | `sonnet` | 质量/成本/速度平衡；难题库可升 `opus` |
| 生成大纲/知识点（从零模式） | `sonnet` | 结构化归纳 |
| 主观准确性 LLM-as-judge（可选，非门） | `sonnet` | 仅建议性复核，不阻断 |

> 质量门（validate.py）**尽量不依赖 LLM**——schema/覆盖/干扰项/分布/去重/可追溯/音标格式都机判。把"LLM 自评准确性"当阻断门是反模式。

---

## 五、错误处理与重试（LLM 层）

`claude_code_direct` 经 `AnthropicProvider` 已对 HTTP 异常分类（`RateLimitError`/`NetworkError`/`ProviderError`/`AuthenticationError`）。生成脚本在内容点级别再套一层重试：

- 捕获 `RateLimitError` → 退避后重试（尊重 429）。
- 捕获 `NetworkError`/`ProviderError` → 重试（计入 `max_retries`）。
- `AuthenticationError` → 不重试，直接报错（需用户检查 Claude Code 登录/鉴权）。
- 单内容点超过 `max_retries` → 写入 `state.failed`，标"待修复/人审"，不中断整体（中断/恢复的体现：其余项继续）。

---

## 六、调用约束

- **全量生产由用户跑**；skill 只在样本上调用验证。样本规模小（默认 20），注意成本可控。
- 不要在门禁里为每条数据额外发起 LLM 调用（成本爆炸）；G5 准确性门只做**机判**子集。
- prompt 模板版本（`prompt_version`）写进 provenance，便于复现/回溯。
