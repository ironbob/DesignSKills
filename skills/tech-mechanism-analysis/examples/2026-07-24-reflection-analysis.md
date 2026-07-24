---
mode: full
target: "reflection-dispatch"
title: "reflection-dispatch 技术机制深度分析"
mechanism_type: "call-chain"
languages: ["Python"]
analyzed_at: "2026-07-24"
covered_files:
  - "skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py"
chain_segments: 5
numerical_examples: 0
defects_arch: 1
defects_logic: 0
open_questions: 1
---

# reflection-dispatch 技术机制深度分析

## 机制概述

- **模式**：full。
- **一句话职责**：把请求中的方法名解析为插件对象上的可调用成员，按反射签名绑定参数并返回动态调用结果。
- **主机制类型**：`call-chain`。
- **次机制类型**：`other`。
- **类型依据**：handle 接收请求并委派 invoke，invoke 通过 getattr 动态解析方法、inspect.signature 绑定参数，再调用解析出的成员并返回结果。
- **链路模板**：`entry` → `resolve` → `bind` → `invoke` → `effect`。

### 范围确认

- **SCOPE-01 · initial · 2026-07-24**：验证样例明确以 handle 到反射调用结果为分析范围；候选文件：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py`。

### 工具与证据置信度

- **Python · high**：已读取动态成员解析、可调用检查、签名绑定和最终返回路径，并实际运行 fixture；工具：direct code reading、Python runtime。

## 全链路

### stage-entry · 从请求提取动态调用信息

- **阶段标识**：`entry`。
- **做了什么**：handle 创建 TextPlugins，并从 request 读取 method、payload 和可选 options 后委派 invoke。
- **怎么实现**：字典键提供方法名和参数，request.get 为关键字参数提供空字典默认值。
- **设计依据（inferred）**：统一请求结构把外部字符串路由与插件调用入口连接起来；这是从接口形态推断的效果。
- **关键结构**：`handle`、`request`、`TextPlugins`、`invoke`。
- **交接/最终效果**：向 invoke 交付插件实例、method_name、payload 和 options 四个值。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:32`（invoke call starts dynamic dispatch）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:30`（handle request entry）、`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:36`（request options default dictionary）。

### stage-resolve · 按名称反射解析成员

- **阶段标识**：`resolve`。
- **做了什么**：invoke 使用 getattr 在插件实例上查找 method_name 对应成员，并拒绝不存在或不可调用的值。
- **怎么实现**：getattr 的默认值是 None，随后 callable 检查把动态对象收窄为可调用成员。
- **设计依据（unknown）**：运行时解析允许请求字符串选择插件行为；代码无法证明选择公开方法反射而非显式注册表的历史原因。
- **关键结构**：`getattr`、`callable`、`LookupError`。
- **交接/最终效果**：成功时向签名绑定阶段交付 bound method；失败时抛出 LookupError 并终止链路。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:22`（getattr resolves method by method_name）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:23`（callable method guard）、`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:24`（LookupError rejects unknown method）。

### stage-bind · 读取签名并绑定参数

- **阶段标识**：`bind`。
- **做了什么**：inspect.signature 读取运行时方法签名，bind 把 payload 和 options 校验并映射到位置及关键字参数。
- **怎么实现**：signature.bind 在真实调用前复用 Python 调用约束，缺参和多余参数会在此抛出 TypeError。
- **设计依据（inferred）**：预绑定让动态请求仍遵守目标方法声明的参数契约；这是反射 API 的直接行为效果。
- **关键结构**：`inspect.signature`、`Signature.bind`、`BoundArguments`。
- **交接/最终效果**：向调用阶段交付 bound.args 和 bound.kwargs，确保参数形态已与目标方法一致。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:26`（signature bind payload and options）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:25`（inspect signature reads method contract）、`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:26`（signature bind validates arguments）。

### stage-invoke · 调用动态解析的方法

- **阶段标识**：`invoke`。
- **做了什么**：invoke 展开 BoundArguments，调用此前由 getattr 解析出的 bound method。
- **怎么实现**：method(*bound.args, **bound.kwargs) 保留目标方法的普通 Python 调用语义。
- **设计依据（inferred）**：把解析和绑定结果统一落到一次真实调用；该效果由调用表达式直接体现。
- **关键结构**：`method`、`bound.args`、`bound.kwargs`。
- **交接/最终效果**：目标插件方法的字符串返回值交回 handle。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:27`（method called with bound args kwargs）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:9`（upper plugin method）、`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:27`（dynamic method invocation）。

### stage-effect · 封装动态调用结果

- **阶段标识**：`effect`。
- **做了什么**：handle 把请求方法名和插件返回字符串封装为包含 plugin 与 result 的字典。
- **怎么实现**：返回对象保留被选择的方法名，使调用结果携带最小路由元数据。
- **设计依据（inferred）**：结果同时暴露路由选择和业务值，便于调用方观察实际分派；这是从返回结构推断的效果。
- **关键结构**：`response dictionary`、`plugin`、`result`。
- **交接/最终效果**：机制最终返回可序列化字典，例如 upper 请求得到 HELLO。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:38`（return plugin and result dictionary）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:38`（response contains method and result）、`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:42`（handle upper fixture request）。

### 链路图

```mermaid
flowchart LR
  request["request method"]
  resolver["getattr resolver"]
  binder["signature binder"]
  method["plugin method"]
  response["result response"]
  request -->|"method_name"| resolver
  resolver -->|"callable method"| binder
  binder -->|"bound arguments"| method
  method -->|"result"| response
```

## 数值示例

本机制未识别到需要工作示例的核心数值操作。

## 架构设计债

### DEBT-ARCH-01 · 插件实例化与反射入口硬绑定

- **所属阶段**：`stage-entry`；跨阶段。
- **需求来源**：`hypothetical`。
- **会变难的需求**：按配置加载多个插件类、隔离允许暴露的方法，并为不同插件使用独立生命周期或依赖。
- **为什么难**：handle 直接实例化 TextPlugins，invoke 又对对象全部公开可调用成员开放 getattr，没有插件注册表、允许列表或生命周期边界。
- **演进方向**：引入 plugin id 到实例工厂和显式 method descriptor 的注册表，反射只作为受控适配层而不是公开成员发现机制。
- **代价/影响**：需要改请求协议、实例创建、方法解析和错误模型，并补充未授权成员与插件加载失败测试。
- **量化范围**：阶段 2 个（`stage-entry`、`stage-resolve`）；文件 1 个（`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py`）；模块 3 个（`handle`、`invoke`、`TextPlugins`）；量级 `medium`；一个文件中的入口和解析两个阶段共同依赖硬编码实例及 getattr 约定。
- **结论置信度**：`high`；硬编码 TextPlugins 和开放 getattr 是直接事实；多插件受控发现是具体演进场景。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:22`（getattr opens method_name lookup）、`skills/tech-mechanism-analysis/examples/fixtures/reflection-dispatch/plugin_dispatch.py:31`（TextPlugins instantiated directly）。

## 逻辑设计债

本机制未识别到逻辑设计债。

## 跨阶段衔接

`DEBT-ARCH-01` 涉及跨阶段约定。

## 已知缺口

- ⚠ 未确认：当前验证环境未安装 mmdc；Mermaid 已通过安全子集结构检查，但未执行实际 SVG 渲染
