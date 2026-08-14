# 范围与现有代码库对齐（模块 A）

> 配合 `arch-first-code-gen` 的 Checklist 第 1 步。确认**技术栈** + 读懂**现有仓库**的分层/命名/日志习惯，让新代码沿用而非另起炉灶。这一步定错栈或无视现有风格，后面全偏。

## 一、模块 A 三件事（PRD §4-A）

1. **需求与栈确认**（P0）：接受新需求，确认技术栈；需求不清提示走 `clarify-requirements`，**不替用户澄清**。
2. **现有代码库对齐**（P0）：读懂仓库现有分层/命名/日志习惯，新代码沿用。
3. 识别现有测试命令和质量约束；按规模、寿命、可靠性、协作面、技术不确定性推荐 `light/standard/high_risk`。
4. 一句话重述「需求范围 + 栈 + 现有风格如何沿用」，解释三个等级的成本/最小产物并给出推荐，然后等待用户明确选择。模型不能替用户选择等级。

## 二、确认技术栈

- 从需求/代码识别栈：`.java`/`.kt` → **JVM**；`.h/.hpp/.cc/.cpp` → **C++**；FastAPI(`.py` + `APIRouter`) + Vue(`.vue`) → **FastAPI+Vue**；`.swift` + `.xcodeproj/.xcworkspace/Package.swift` 或 SwiftUI/UIKit import → **Swift/iOS**。
- 写进契约源 `stack`，第 2 步按 `standard-practices/README.md` 映射加载对应文件；Swift/iOS 对应 `swift-ios.md`。
- 多栈仓库：确认本次 feature 落在哪一栈；跨栈 feature（前后端联动）按 `FastAPI+Vue` 全栈库处理。

凡涉及 UI（Android、Vue、Qt/QML、SwiftUI/UIKit 等），还必须识别并记录：

- UI 框架及页面/feature 边界；
- 现有模式：MVVM / MVC / MVP / Coordinator / Clean-VIP / TCA / Redux-Store / Direct View / 其他；
- 状态工具与事实源：ViewModel / feature store / composable / QObject presentation object / 既有方案；
- 依赖注入、导航、并发与测试约定。

不要把某种语言或 UI 框架自动等同于“必须 MVVM”。先按 `ui-architecture-policy.md` 判断适用性与迁移影响；适合且影响可控时优先使用，纯展示/局部 UI 状态或已有清晰替代架构不机械增加 ViewModel。

## 三、读懂现有仓库（粗读，不深挖）

在动手前用 `rg`/`find` 粗读相关目录，识别并陈述：

- **分层风格**：是三层？六边形？按 feature 切？看目录与包结构（`controller/service/dao`？`handlers/services/`？`routers/services/repositories/`？）。
- **命名约定**：类/文件/包怎么命名（`OrderService` vs `OrderManager` vs `order_service.py`）。
- **日志库与习惯**：SLF4J？loguru？spdlog？日志放哪、打多细。
- **依赖/注入方式**：构造注入？Spring `@Autowired`？手动 new？
- **验证习惯**：现有单元/集成测试命令、fixture、静态检查和受影响模块测试范围。
- **UI 状态与导航**（所有 UI 栈）：ViewModel/Store/Controller 谁拥有状态？Coordinator/Router/Navigation 如何表达导航？
- **MVVM 迁移影响**：引入 MVVM 会改哪些模块、公共接口、共享状态、导航、组装与测试？是否达到 `high`？

> 结果写进契约源 `existing_alignment.recognized_style`（一句话陈述现状）+ `new_code_follows`（新代码怎么沿用）。这是「对齐现有、不另起炉灶」的显式声明（PRD 模块 A P0 验收）。

## 四、不替用户澄清需求

- 输入假设**需求已明确**（或仅做必要范围确认：圈定本次 feature 边界、明确不做什么）。
- 需求明显不清（缺目标用户/核心场景/验收）→ 明确提示「需求还没澄清，建议先走 `clarify-requirements`」，**不在本 skill 里展开需求澄清**（越界）。
- 仅做范围确认：用一句话重述本次 feature 范围，请用户确认/修正。

## 五、等级选择门（第 1 步末）

把下面内容呈现给用户：

1. **需求范围**（本次 feature 做什么、不做什么）。
2. **技术栈**（JVM / C++ / FastAPI+Vue / Swift-iOS）；涉及 UI 时同时注明框架、当前/目标模式、MVVM 适用性与迁移影响。
3. **现有风格如何沿用**（包/命名/日志库与现有一致）。
4. **设计等级选择**：`light / standard / high_risk` 的差异、推荐等级和推荐依据。

> 询问“请选择等级，或明确接受推荐等级”，然后结束当前回合。只有用户消息明确写出等级或接受某个推荐，才进入第 2 步。用户说“你决定”“直接做”“尽快”不算等级选择；初始请求已经明确写出等级时无需重复询问。

若 UI 目标是新引入 MVVM 且迁移影响为 `high`，必须额外说明迁移范围、收益、风险与较小改动的替代方案，并等待用户明确确认；通用方案确认不能替代这项专项确认。

## 六、边界越界识别

- **用户要「评估/重构已有模块」** → 超出本 skill（那是 `arch-quality-eval`）；本 skill 是新需求生成侧。
- **用户明确要「全自动、无需中间确认」** → 说明本 skill 为防止未审架构直接落码，不支持跳过双确认；仍停在等级选择门或方案确认门。
- **用户给的范围过大**（整个大系统一次落地）→ 提示「单 feature 粒度，建议拆成多个 feature 逐个走；大 feature 用聚焦策略（按角色分批，未决）」。
- **需求还没想清楚** → 提示走 `clarify-requirements`，不在本 skill 澄清。
