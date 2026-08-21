# 已有 app 风格迁移 · 审计清单

> 场景 B 的执行手册。产出 = 功能冻结清单 + 风格差距报告 + 目标态演示；确认后才迁移。

## 1. 功能冻结（先于视觉审计）

按真实页面记录，迁移后逐项复测：

| 类别 | 必须记录 |
| --- | --- |
| 信息架构 | 页面、导航层级、区域关系、打开/关闭方式 |
| 操作 | 主次/危险操作、搜索、筛选、排序、多选、批量、拖拽 |
| 数据 | 主数据、元数据、层级关系、真实密度、最长内容 |
| 状态 | 默认、hover、选中、编辑、加载、空、错误、禁用、离线、权限 |
| 输入 | 鼠标、键盘、快捷键、焦点顺序、Esc 链、焦点归还 |
| 环境 | 平台、最小窗口、宽窄屏、现有主题、缩放与长文本 |
| 无障碍 | 名称、角色、状态表达、对比度、非颜色线索 |

没有证据的项写“未验证”，不要默认通过。结构可以重构，能力不允许无授权改变。

## 2. 风格边界

1. 读取 `style-transfer-model.md`、目标风格 `evidence.md` 和 `identity.md`。
2. 记录 source-version、platforms、evidence-grade、representation；目标要求超出采样版本时先补采样或明确降级。
3. 把命中的规则分别登记为 `invariant`、`adaptive`、`archetype-bound`、`source-specific`，并给结论标 `observed`、`derived` 或 `adapted`。
4. 默认保留目标 app 区域关系。布局母题通过兼容判断且获 G1 确认后才采用。
5. 对目标风格未覆盖的组件使用推导规则，不跨风格借组件。

## 3. 视觉与工程审计

1. 读取 `ui-surface-inventory.md`，运行
   `<skill>/scripts/audit-ui-style.py --project <project> --style <style> --format json --workers 0 > /tmp/ui-style-audit.json`。
2. 运行 `<skill>/scripts/validate-ui-coverage.py --report /tmp/ui-style-audit.json --init /tmp/ui-style-coverage.json`，以候选源文件和识别出的 route/component/element/overlay/theme/breakpoint 建立覆盖分母。
3. 并行检查全局/Token、组件状态、交互响应式、无障碍四组表面；每组只回填自己负责的 inventory ID 与证据。
4. 从全局 CSS、主题变量和组件覆盖层开始，排查 `!important`、简写遮蔽与全局污染。
5. 将颜色、排版、几何、间距、材质和动效对照目标规范，写死值归入 token 收敛清单。
6. 逐条检查目标风格反模式；扫描命中只是线索，必须人工判断上下文。
7. 对每个受影响组件核对完整状态，不用全项目 hover 数量代替组件级判断；不适用状态写 N/A 和理由。
8. 核对键盘、Esc LIFO、焦点环与归还、浮层钳制、窗口/页面失活和窄窗行为。
9. 未知扩展名、大文件、符号链接与读取错误必须补扫或显式 waiver；不能静默移出分母。
10. 生成保留布局版 mock；布局兼容时才额外生成布局增强版。

## 4. 差距报告模板

```markdown
# <app> → <style> 风格迁移报告

## 功能冻结
- 页面/区域：…
- 核心操作：…
- 关键状态：…
- 键盘/焦点：…
- 响应式/主题：…
- 未验证：…

## 迁移边界
来源版本/平台/等级：…

| 规则 | 身份分类 | 证据分类 | 决策 | 理由/来源 ID |
| --- | --- | --- | --- | --- |
| 单强调色 | invariant | observed/derived | 迁移 | O-… / D-… |
| 三栏布局 | archetype-bound | observed | N/A | 保留目标两栏任务流 |

## 分区域差距
| 区域 | 功能基线 | 当前视觉 | 目标表达 | 风险 | 工作量 |
| --- | --- | --- | --- | --- | --- |

## 反模式与状态缺口
1. `<文件:行>` …

## 实施顺序
功能冒烟 → Token → 表面层级 → 组件状态 → 空间节奏 → 条件性布局增强
```

## 5. 区域迁移与验收

- 一次迁一个区域；修改前后运行相同功能路径。
- 一个区域只有通过功能保持门，才能进入下一区域。
- 写死视觉值替换为语义 token；确需局部例外时说明 `adapted` 原因。
- 不适用的布局评分项标记 N/A，不为了拿分改变功能结构。
- 迁移完成后填写 `score-style-transfer.py` 输入：先过功能硬门，再计算风格身份分。
- 回填 coverage manifest，并运行 `validate-ui-coverage.py`。只有门禁返回 complete 才能称为所定义范围内“全量完成”；否则按 blocker 明示未验证项。
- 规范未覆盖的场景记录为 derived；稳定后回写风格包，不能在当前工程偷偷混入另一风格。
