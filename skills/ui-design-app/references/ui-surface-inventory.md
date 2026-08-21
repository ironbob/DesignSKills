# UI Surface Inventory：全量迁移的覆盖契约

> 目的：让“已经检查全 app”成为可验证结论，而不是凭印象声明。静态扫描负责建立候选分母，运行时证据负责闭合条件 UI、状态、主题和视口。

## 1. 覆盖单位

完整迁移至少覆盖以下层级：

```text
候选源文件
├── route / screen
│   ├── component / region
│   │   ├── default
│   │   ├── hover / pressed / focus-visible / disabled
│   │   └── 组件特有状态（selected、checked、expanded、editing…）
│   └── overlay（dialog、menu、popover、tooltip、toast…）
├── journey state（loading、empty、error、offline、permission）
├── theme
└── viewport（wide、narrow；产品另有断点时追加）
```

`source_files` 是防漏底线：即使启发式没有识别出组件名，该候选文件仍在分母中。组件用 `文件::组件名` 区分同名实例；语义/ARIA 元素用 `文件:行:列:类型` 逐实例登记，不会把一页十个按钮压缩成一个检查项。每个条目只能是：

- `verified`：必须提供可定位证据，例如测试名、截图路径、录屏时间点、DOM/无障碍快照或人工检查记录。
- `n/a`：必须写明为什么该能力不适用；不能用来隐藏尚未检查的项目。
- `unverified`：明确未完成，并阻止“全量完成”声明。

## 2. 静态发现边界

运行：

```bash
python3 <skill>/scripts/audit-ui-style.py \
  --project <project> --style <style> --format json --workers 0 \
  > /tmp/ui-style-audit.json
```

扫描器递归枚举受支持的 Web、模板、SwiftUI、UIKit/AppKit、Compose、Android XML、Flutter、XAML 与 QML 源文件；识别路由、组件、HTML/ARIA 与常见原生控件、浮层、交互/旅程状态、主题与断点。`--workers 0` 自动使用有界线程池，输入和聚合均排序，因此多线程输出除执行元数据外必须与 `--workers 1` 一致。

静态扫描不知道运行时条件、服务端配置、权限分支、真实数据、portal 内容、焦点顺序和最终绘制结果。因此扫描报告始终保留 `runtime_inventory_unverified`，本身不能证明全量完成。

## 3. 未知项与跳过项

以下项目会阻止闭合：不支持但疑似 UI 的扩展名、过大文件、符号链接、读取/解码/stat 错误。处理优先级：

1. 用 `--include-extension` 或提高 `--max-file-bytes` 纳入扫描。
2. 用适合该技术栈的解析器或人工证据补查。
3. 确认无关时在 manifest 的 `waivers` 写 `kind`、`target` 和具体 `reason`。

当 blocker 的 `count` 大于报告保存的 examples 数量时，只能重新运行并提高 `--max-examples` 逐项处理，或使用 `target: "*"` 对整个类别作明确豁免。宽泛豁免降低可信度，交付报告必须披露。

构建产物、依赖缓存和已知非 UI 资源不进入候选分母；这是明确的扫描边界，不等于它们经过视觉验证。

## 4. 证据清单与门禁

先生成草稿：

```bash
python3 <skill>/scripts/validate-ui-coverage.py \
  --report /tmp/ui-style-audit.json \
  --init /tmp/ui-style-coverage.json
```

草稿把所有发现项、每个组件的基础状态、五类旅程状态、宽/窄视口全部设为 `unverified`。运行时检查后填写证据或 N/A，再执行：

```bash
python3 <skill>/scripts/validate-ui-coverage.py \
  --report /tmp/ui-style-audit.json \
  --manifest /tmp/ui-style-coverage.json
```

只有退出码为 0 且 `claim_full_coverage: true` 时，才可声明“所定义范围内全量检查完成”。这表示 manifest 的可审计分母已闭合，不表示静态启发式能发现未知技术或没有登记的新入口；交付时仍须声明扫描平台、扩展名、排除目录、主题与视口边界。

## 5. 高速执行

扫描器内部对文件读取和正则分析并行；运行时检查按互不依赖的证据 lane 并行：

- A：Token、主题、全局 CSS 与写死视觉值。
- B：route/component 清单、组件状态和数据状态。
- C：宽窄视口、键盘、焦点、Esc 链与浮层。
- D：语义、无障碍名称、角色、状态表达和对比度。

四个 lane 共享同一 inventory ID，只写各自证据，最后合并进单一 manifest。涉及同一源文件的实际修改仍按区域顺序执行，避免并行覆盖；并行化的是发现与验证，不是无序改码。

小项目上线程调度可能不比单线程快；大项目才通常受益。速度目标服从确定性和覆盖透明度，不能通过跳过未知项获得。
