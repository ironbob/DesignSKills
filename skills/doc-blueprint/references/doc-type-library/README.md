# 文档类型库（注册表）

> 用途：登记本 skill 内置的文档类型、各类型的必备章节（slot），以及**如何新增一个类型**。
> 与 `clarify-doc/references/writing-situation-analysis.md` 的"选用决策树"共用同一套类型本体：那里管"该选哪类"，这里管"这类怎么搭结构"。
> 校验 R-S1 按本库的"必备章节（slot）"判定。

---

## 一、已内置类型

| doc_type | 文件 | 必备 slot（缺即 🔴） | 一句话 |
|----------|------|---------------------|--------|
| `postmortem` | `postmortem.md` | summary / impact / timeline / root_cause / actions / lessons | 事故复盘 |
| `rfc` | `rfc.md` | context / current_state / proposal / **alternatives** / decision / impact | 技术方案/设计文档 |
| `prd` | `prd.md` | problem / goals / **success_metrics** / scope / out_of_scope | 产品需求文档 |
| `adr` | `adr.md` | context / **decision** / **rationale** / consequences | 架构决策记录 |
| `runbook` | `runbook.md` | trigger / precheck / steps / expected / **rollback** / escalation | 操作指引/SOP |
| `business_case` | （按通用结构） | opportunity / solution / **cost** / **benefit** / risk / resources | 立项书/商业论证 |
| `weekly` | （按通用结构） | done / **risks** / next / need_help | 周报/进展 |
| `changelog` | （按通用结构） | change / **impact** / window / mitigation / contact | 变更公告 |
| `announcement` | （按通用结构） | what / **impact** / **status** / mitigation / followup | 通知/事故公告 |
| `meeting` | （按通用结构） | topics / **decisions** / **actions** / open_issues | 会议决议 |
| `article` | （按通用结构） | problem / solution / repro / pitfalls / conclusion | 技术文章/Wiki |
| `custom` | （与用户确认） | 背景/核心/支撑/结论（通用） | 其他 |

> 标"按通用结构"的类型暂无独立模板文件，按通用专业结构（背景→核心→支撑→结论）派生并与用户确认必备章节。**新增独立模板 = 加一个 `<type>.md` + 在本表登记 slot**，无需改逻辑。

---

## 二、每个类型文件的统一结构

```
# <类型名>
## 匹配信号      ← 什么场景选它（与 clarify-doc 决策树呼应）
## 必备章节（slot）与每节必含   ← R-S1 锚点；列 slot id + 每节必须写什么
## 常见缺陷       ← 盲区/反模式
## 专业示例片段   ← 一段达标正文（带标注），供派生参照
```

---

## 三、新增一个类型（零逻辑改动）

1. 新建 `references/doc-type-library/<type>.md`，按上方统一结构写。
2. 在本表（§一）登记一行，列出必备 slot。
3. 在 `doc-schema.md` 第四节枚举表加一行（如已有枚举值则跳过）。
4. （若该类型有专属表现力偏好）在 `expressiveness.md` §四受众调表现力补一句。

完成 1–3，新类型即可被 `validate_doc.py` 的 R-S1 校验、被派生写作。
