# 范围与现有代码库对齐（模块 A）

> 配合 `arch-first-code-gen` 的 Checklist 第 1 步。确认**技术栈** + 读懂**现有仓库**的分层/命名/日志习惯，让新代码沿用而非另起炉灶。这一步定错栈或无视现有风格，后面全偏。

## 一、模块 A 三件事（PRD §4-A）

1. **需求与栈确认**（P0）：接受新需求，确认技术栈；需求不清提示走 `clarify-requirements`，**不替用户澄清**。
2. **现有代码库对齐**（P0）：读懂仓库现有分层/命名/日志习惯，新代码沿用。
3. 一句话重述「需求范围 + 栈 + 现有风格如何沿用」，请用户确认。

## 二、确认技术栈

- 从需求/代码识别栈：`.java`/`.kt` → **JVM**；`.h/.hpp/.cc/.cpp` → **C++**；FastAPI(`.py` + `APIRouter`) + Vue(`.vue`) → **FastAPI+Vue**。
- 写进契约源 `stack`，第 2 步据此加载 `standard-practices/<stack>.md`。
- 多栈仓库：确认本次 feature 落在哪一栈；跨栈 feature（前后端联动）按 `FastAPI+Vue` 全栈库处理。

## 三、读懂现有仓库（粗读，不深挖）

在动手前用 `rg`/`find` 粗读相关目录，识别并陈述：

- **分层风格**：是三层？六边形？按 feature 切？看目录与包结构（`controller/service/dao`？`handlers/services/`？`routers/services/repositories/`？）。
- **命名约定**：类/文件/包怎么命名（`OrderService` vs `OrderManager` vs `order_service.py`）。
- **日志库与习惯**：SLF4J？loguru？spdlog？日志放哪、打多细。
- **依赖/注入方式**：构造注入？Spring `@Autowired`？手动 new？

> 结果写进契约源 `existing_alignment.recognized_style`（一句话陈述现状）+ `new_code_follows`（新代码怎么沿用）。这是「对齐现有、不另起炉灶」的显式声明（PRD 模块 A P0 验收）。

## 四、不替用户澄清需求

- 输入假设**需求已明确**（或仅做必要范围确认：圈定本次 feature 边界、明确不做什么）。
- 需求明显不清（缺目标用户/核心场景/验收）→ 明确提示「需求还没澄清，建议先走 `clarify-requirements`」，**不在本 skill 里展开需求澄清**（越界）。
- 仅做范围确认：用一句话重述本次 feature 范围，请用户确认/修正。

## 五、一句话确认（第 1 步末）

把下面三样呈现给用户确认：

1. **需求范围**（本次 feature 做什么、不做什么）。
2. **技术栈**（JVM / C++ / FastAPI+Vue）。
3. **现有风格如何沿用**（包/命名/日志库与现有一致）。

> 用户确认后进入第 2 步（加载原则库 + 按栈做法库）。

## 六、边界越界识别

- **用户要「评估/重构已有模块」** → 超出本 skill（那是 `arch-quality-eval`）；本 skill 是新需求生成侧。
- **用户要「全自动别问我直接出代码」** → 本 skill 强制架构确认环节，需人参与；可说明确认很轻量（几轮）。
- **用户给的范围过大**（整个大系统一次落地）→ 提示「单 feature 粒度，建议拆成多个 feature 逐个走；大 feature 用聚焦策略（按角色分批，未决）」。
- **需求还没想清楚** → 提示走 `clarify-requirements`，不在本 skill 澄清。
