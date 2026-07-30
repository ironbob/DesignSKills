---
name: java-sp-handle
description: "Trigger only when the user explicitly asks to use this skill by name: `$java-sp-handle`, `java-sp-handle`, `java_sp_handle`, or a namespaced form ending in `:java-sp-handle`. Do not trigger from generic JNI, Java, C++, shared_ptr, native handle, or lifecycle questions. Designs, implements, migrates, or reviews a Java/JNI/C++ native-object handle mechanism in which Java owns an opaque long handle and C++ stores a type-tagged std::shared_ptr; includes an optional debug-only non-owning live-object observer, uses bundled verbatim production sources as the baseline, and always shows textual and semantic differences between the original and newly written code."
---

# Java shared_ptr Handle

实现一套 Java/JNI/C++ 跨语言对象句柄机制：

```text
Java NativeObjectRef.mWrapPtr
        -> C++ NativeWrap { typeId, shared_ptr<void> }
        -> native object T
```

目标是让 Java 不直接拥有 `T*`，而是持有 native 包装器；由 `std::shared_ptr`
管理真实对象生命周期，并明确区分复制引用、转移句柄和释放句柄。始终以 Skill 内置的原始
生产代码为可见基线，交付新代码时同时交付原始代码到新代码的差异。

## 先确定任务类型

将请求归入一类：

1. **新建**：在项目中生成完整基础设施和一个可运行示例。
2. **接入**：为一个已有 C++ 类型增加 Java Wrapper、JNI create/access/free。
3. **迁移**：把裸指针或另一套 Handle 迁移到 shared_ptr Handle。
4. **审查/修复**：检查已有实现的所有权、类型安全、并发和清理路径。

用户没有明确要求写代码时，只分析或审查，不修改文件。

## 加载参考

- 开始任何分析、设计、实现或审查前，完整读取以下三份原样源码快照：
  - [原始 NativeObjectRef.h](references/original-code/NativeObjectRef.h)
  - [原始 NativeObjectRef.java](references/original-code/NativeObjectRef.java)
  - [原始 NativeObjectRef.cpp](references/original-code/NativeObjectRef.cpp)
- 开始设计或实现前，完整读取 [references/mechanism-contract.md](references/mechanism-contract.md)。
- 准备编译和交付前，完整读取
  [references/verification-checklist.md](references/verification-checklist.md)。
- 需要从零生成兼容型实现时，再读取并改造 `assets/compat-template/`；模板不是事实源，不要
  不经适配直接复制。

三份 `references/original-code/` 文件是只读历史基线。不得为了让新设计看起来更接近而修改
它们；发现原实现缺陷时，在新代码和差异说明中处理。

快照来源分别是：

- `onestream/src/main/cpp/insbase/nativeref/NativeObjectRef.h`
- `bmgmedia/src/main/cpp/bmg/android/project/insbase/src/main/java/com/arashivision/insbase/nativeref/NativeObjectRef.java`
- `bmgmedia/src/main/cpp/bmg/android/insbase/nativeref/NativeObjectRef.cpp`

## 执行流程

### 1. 取证项目约束

只检查任务范围内的文件，确认：

- Java package、基类命名、so 加载方式、最低 Android/JDK 版本。
- JNI 使用静态导出符号还是 `RegisterNatives`。
- C++ namespace、日志/断言、JNI helper、智能指针别名和构建系统。
- 是否已有集中定义的 typeId 常量、Java native 基类或重复实现。
- 对象是否跨线程使用、是否要求显式释放、是否需要 native 反向创建 Java 对象。
- Debug 构建开关、so 加载入口，以及只读诊断 API 应放在哪个 Java package。

优先复用项目现有约定。只有会改变 ABI、线程模型或资源释放语义的缺失信息才询问用户。

### 2. 建立“原始实现 → 新实现”基线

编码前，先引用原始源码中的真实符号建立决策表：

| 原始机制 | 原始符号 | 新实现决策 | 理由 |
|---|---|---|---|
| Handle 存储 | `mWrapPtr` | 保留/改名/替换 | 项目约束 |
| 包装器 | `NativeWrap` | 保留/改造 | ABI、并发 |
| 复制 | `CopyRefGet` | 保留/改造 | 生命周期 |
| 转移 | `MoveRefGet` | 保留/改造 | 失效语义 |
| 释放 | `free/nativeFree` | 保留/改造 | 清理策略 |
| 类型保护 | `typeId` | 保留/改造 | 类型注册 |
| Java 反向构造 | `NewJavaNativeObjectRef` | 保留/改造/删除 | 实际需求 |
| 生命周期观测 | 原实现无 | 新增/关闭 | Debug 需求 |

不得只说“参考了原实现”。每一项必须明确保留、修改、替换或删除。

### 3. 声明所有权表

编码前先在工作记录中明确：

| 操作 | Java Handle | NativeWrap | 真实对象引用计数 |
|---|---|---|---|
| create | 获得有效句柄 | 新建 | +1 |
| copy-get | 保持有效 | 保持 | 临时 +1 |
| move-get | 立即失效 | 删除 | 净值通常不变 |
| close/free | 立即失效 | 删除 | -1 |
| native-to-Java wrap | 新 Java Wrapper | 新建 | +1 |
| debug observe | 不变 | 不拥有，仅记录元数据 | 0 |

如果实际需求不同，先更新此表，再写代码。

### 4. 固定 direct-wrap 后端

只实现原始代码同类的 direct-wrap：

```text
jlong -> NativeWrap* -> shared_ptr<void> -> T
```

不要增加全局 Handle 容器、Handle ID 分配器或按 ID 查找对象的机制。所有访问必须限定在同一
线程、串行 executor，或由覆盖完整 native 调用与 close/move 的外层锁保护。无法满足串行约束
时，明确说明该需求超出本 Skill 的设计边界，不得通过 `volatile` 或只同步 getter 宣称安全。

Debug Tracker 不是 Handle 后端：它不能按 debugId 返回对象、不能释放对象、不能参与
`CopyRefGet/MoveRefGet`，只保存 `weak_ptr<void>` 和不可解引用的诊断元数据。

### 5. 实现最小闭环

至少实现：

1. C++ `NativeWrap { typeId, shared_ptr<void> }`。
2. `NewRefWrap/NewRefWrapJlong`。
3. `CopyRefGet<T>`：校验空值和 typeId，复制 `shared_ptr`，Java Handle 保持有效。
4. `MoveRefGet<T>`：在既定串行约束下取走 Handle，让 Java 立即失效。
5. Java `close/free`：幂等地释放一个 wrapper 引用。
6. 一个真实 Java 子类和对应 native create/access 示例。
7. 错误映射：不得让普通参数错误无说明地演变成野指针。
8. Debug 构建启用非持有型 Tracker，并提供 Java 只读 JSON/count 查询入口。

按需求实现：

- `hasSameNativeObject`。
- `IsSuchType`。
- `PtrGetFromNativeWrap`；仅限同步、不延长生命周期的明确场景。
- C++ 反向构造 Java Wrapper。
- 手动释放泄漏诊断。

### 6. 遵守硬性实现规则

- `jlong` 只保存 `NativeWrap*` 地址，禁止保存真实 `T*` 或把 `std::shared_ptr` 对象位模式塞进
  `jlong`。
- 指针与 `jlong` 之间经 `intptr_t/uintptr_t` 转换。
- `typeId` 必须来自集中定义的常量或枚举；新增值前搜索冲突。
- typeId 通过后才能做 `static_pointer_cast`；不能把 Java 类名当成唯一类型保护。
- move 必须先让 Java Handle 失效，再释放 wrapper，且二次 move 必须失败。
- close/free 必须幂等；释放 wrapper 不得直接假设真实对象已经析构。
- 从 JNI 取出的 `shared_ptr<T>` 必须覆盖完整 native 使用区间。
- native-to-Java 构造失败时必须回收刚创建的 wrapper。
- Java 绿色项目优先 `AutoCloseable`；不要新增 `finalize()`。需要兜底时使用项目可用的
  `Cleaner`，且 cleaning action 不得强引用被清理对象。
- direct-wrap 不得声称天然线程安全。使用统一线程、串行 executor 或覆盖完整操作的外层锁；
  不能仅给 Java 字段加 `volatile`。
- Tracker 不得保存 `shared_ptr<void>`、`jobject` 或 JNI GlobalRef；只允许 `weak_ptr`、整数、
  时间、线程 ID 和名称副本。
- Tracker 只在 `NativeWrap` 构造/析构和显式 dump 时工作，不得修改 copy-get 热路径。
- Debug 地址只能作为字符串展示，禁止重新转换成 Handle。
- Release 构建必须关闭 `ANBASE_NATIVE_REF_DEBUG_TRACKING`，使 `NativeWrap` 不增加调试字段。
- JNI 边界不得让 C++ 异常穿过 JNI；按项目约定转换成 Java 异常、错误码或 fatal check。

### 7. 集成

- 将新源文件加入 CMake/ndk-build/Gradle 对应 source set。
- 保留混淆所需的 native 方法、构造器和类。
- 动态注册时接入已有 `JNI_OnLoad`，不要创建第二个冲突入口。
- 静态 JNI 符号必须正确编码 package/class/method 中的下划线。
- 缓存 `jclass` 时使用 GlobalRef，并明确进程期持有或在 `JNI_OnUnload` 释放。
- 将 `NativeObjectDebug.{h,cpp}` 和 `NativeObjectDebug.java` 加入对应构建目标。
- 仅在 Debug variant 为 native target 定义 `ANBASE_NATIVE_REF_DEBUG_TRACKING=1`；Release
  variant 不定义或显式定义为 0。

### 8. 生成原始代码与新代码的差异

实现完成后，必须运行：

```bash
python3 <skill-dir>/scripts/compare_with_original.py \
  --header <new-header-path> \
  --java <new-java-path> \
  --cpp <new-cpp-path> \
  --extra <new-debug-header-path> \
  --extra <new-debug-cpp-path> \
  --extra <new-debug-java-path> \
  --output <comparison-report-path>
```

新实现拆成多个文件时：

- 将承担主要基类职责的三个文件传给脚本。
- 每个无原始对应文件的新源码都用一个 `--extra` 传给脚本，以 `/dev/null → new file`
  展示完整 diff。
- 在语义差异表中列出这些新增文件及其从原实现扩展出的职责。
- 不得通过先改写原始快照、格式化两边或删除大段 diff 来缩小差异。

比较报告必须包含完整 unified diff。另给一张语义差异表，至少覆盖：

| 维度 | 原始实现 | 新实现 | 影响 |
|---|---|---|---|
| 文件/命名 |  |  |  |
| Handle 后端 |  |  |  |
| create/copy/move/free |  |  |  |
| 类型校验 |  |  |  |
| Java 清理 |  |  |  |
| 并发模型 |  |  |  |
| 错误策略 |  |  |  |
| JNI 类/方法缓存 |  |  |  |
| Debug 生命周期观测 |  |  |  |
| 新增/删除能力 |  |  |  |

如果目标代码与原始代码完全相同，也必须生成报告并明确“无文本差异”，不能省略比较。

### 9. 验证后交付

按 `verification-checklist.md` 执行：

- 编译目标 native ABI 和 Java/Kotlin 模块。
- 跑 create/copy/move/free/type mismatch/identity 测试。
- 有并发承诺时跑 close-vs-copy、double-close、double-move 压测。
- 在 Debug 构建验证 wrapped/native-only/expired 三种观测结果以及 typeId/age 过滤。
- 在 Release 构建验证查询返回 `trackingEnabled=false` 且主路径没有 Tracker 状态。
- 检查 ASan/HWASan/LSan 或项目现有 native 内存工具结果。
- 检查比较报告包含三个文件映射且没有“文件缺失”。
- 报告实际执行的命令、结果、未验证 ABI 和剩余约束。

<HARD-GATE>
未完整读取三份原始源码、未生成三文件 unified diff、未给出语义差异表，禁止交付新实现。
未通过编译和关键生命周期测试，不宣称实现完成。
</HARD-GATE>

## 输出要求

实现任务最终说明：

- direct-wrap 的命名、地址转换和线程约束。
- Java、JNI、C++ 三层新增或修改的文件。
- create/copy/move/close 的最终所有权语义。
- typeId、线程模型、错误策略。
- Debug Tracker 开关、查询入口和“不拥有对象”的证明。
- 原始实现决策表。
- 三文件 unified diff 报告路径。
- 原始实现与新实现的语义差异表。
- 验证命令与结果。
- 尚未覆盖的 ABI、并发或清理风险。

不要只交付三个孤立文件；必须完成一个真实类型的端到端接入，或者明确说明项目缺少什么依赖。
