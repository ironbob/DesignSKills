# Confluence 组件映射：block kind → 存储格式宏

> 用途：把 `doc.md` 的每个 block kind 映射到 Confluence Storage Format 原生构造。与 `render-template.md`、`projection.manifest.yaml`、上游 `doc-schema.md` 的 block kind 枚举同进同退。
> 颜色/宏名以 Confluence Data Center / Cloud 通用宏为准。

---

## 一、block kind → Confluence 宏

### `callout`（admonition → structured-macro）

```xhtml
<!-- doc:proj id=warning-1 kind=callout -->
<ac:structured-macro ac:name="warning">
  <ac:rich-text-body>
    <p><strong>风险：重试风暴</strong></p>
    <p>恢复后若不限流，积压重试会再次打满连接池。</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

| doc.md variant | Confluence macro `ac:name` | 视觉 |
|----------------|---------------------------|------|
| `note` | `info` | 蓝色信息面板 |
| `tip` | `tip` | 绿色提示 |
| `warning` | `warning` | 红色警示 |
| `important` | `note` | 黄色注意 |
| `decision` | `info`（内含 **决策** 标识） | 见下 |

#### `decision`（决策）
```xhtml
<!-- doc:proj id=decision-1 kind=callout -->
<ac:structured-macro ac:name="info">
  <ac:rich-text-body>
    <p><strong>决策：限流算法选令牌桶</strong></p>
    <p>理由：需支持突发流量且可平滑限速。备选：漏桶（否）、计数器（否）。</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

### `status`（徽章 → status macro）
```xhtml
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="title">已恢复</ac:parameter>
  <ac:parameter ac:name="colour">Green</ac:parameter>
</ac:structured-macro>
```
| level | colour |
|-------|--------|
| healthy | Green |
| degraded | Yellow |
| down | Red |
| blocked | Orange |
| done | Green（title 带 ✅） |
| todo | Grey |
> 全文颜色含义一致；首次出现处建议放一个图例（用 `info` 宏列出颜色含义）。

### `chart:bar`/`chart:line`/`chart:pie`（图表）
两种合法映射，按数据形态选一：
- **A. Chart 宏 + 内嵌数据表**（Confluence 内置 Chart 宏，数据来自一个表格）：
```xhtml
<!-- doc:proj id=impact_by_minute kind=chart:bar -->
<ac:structured-macro ac:name="chart">
  <ac:parameter ac:name="type">bar</ac:parameter>
  <ac:parameter ac:name="title">超时量/分钟</ac:parameter>
  <ac:rich-text-body>
    <table><tbody>
      <tr><th>时间</th><th>超时量</th></tr>
      <tr><td>00:00</td><td>12</td></tr>
      <tr><td>00:15</td><td>120</td></tr>
    </tbody></table>
  </ac:rich-text-body>
</ac:structured-macro>
```
  > `type` ∈ `bar|line|pie`；数据从 datasets/figures inline 投影成表。
- **B. Mermaid 宏**（环境装了 Mermaid for Confluence 时）：见 diagram，`xychart-beta`/`pie`。

### `diagram`（mermaid）
```xhtml
<!-- doc:proj id=arch kind=diagram -->
<ac:structured-macro ac:name="mermaid">
  <ac:plain-text-body><![CDATA[flowchart LR; A-->B-->C]]></ac:plain-text-body>
</ac:structured-macro>
```
> 无 Mermaid 宏时退化为 `<ac:structured-macro ac:name="info">` 内贴 mermaid 源码 + 说明。

### `kpi`（关键指标）
```xhtml
<!-- doc:proj id=kpi_impact kind=kpi -->
<ac:structured-macro ac:name="info">
  <ac:rich-text-body>
    <p><strong>受影响订单</strong></p>
    <p style="font-size:2em"><strong>1,284 单</strong> · 环比 +12%</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

### `timeline`（→ 表格）
```xhtml
<!-- doc:proj id=tl kind=timeline -->
<table><tbody>
  <tr><th>时间</th><th>事件</th><th>影响</th></tr>
  <tr><td>00:00</td><td>告警突增</td><td>超时率↑</td></tr>
</tbody></table>
```

### `table`（原生表格 → 存储格式表）
```xhtml
<!-- doc:proj id=matrix kind=table -->
<table><tbody>
  <tr><th>方案</th><th>成本</th><th>结论</th></tr>
  <tr><td>组合方案</td><td>中</td><td>采用</td></tr>
</tbody></table>
```

### `code`（代码 → code 宏）
```xhtml
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">bash</ac:parameter>
  <ac:plain-text-body><![CDATA[kubectl get pods]]></ac:plain-text-body>
</ac:structured-macro>
```

### `prose`/`list`/`quote`
- 段落 → `<p>…</p>`；列表 → `<ul>`/`<ol>`；引述 → `<blockquote>`。

---

## 二、数字插值与引用

- `{{d:affected_orders}}` → 文本 `1,284 单`。
- `[ref:r1]` → `<a href="confluence://OBS/pay-pool">连接池监控定义</a>`（内部链接可用 `<ac:link>`）。

> 所有数字来自 `datasets`，与 Markdown 后端同源，禁止硬编码另一套。
