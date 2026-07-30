---
name: java-sp-handle
description: "Trigger only when the user explicitly asks to use this skill by name: `$java-sp-handle`, `java-sp-handle`, `java_sp_handle`, or a namespaced form ending in `:java-sp-handle`. Do not trigger from generic JNI, Java, C++, shared_ptr, native handle, or lifecycle questions. Designs, implements, migrates, or reviews a Java/JNI/C++ native-object handle mechanism in which Java owns an opaque long handle, C++ stores a type-tagged std::shared_ptr, and JNI supports copy, move, release, identity, type checks, and native-to-Java wrapping."
---

# Java shared_ptr Handle

实现一套 Java/JNI/C++ 跨语言对象句柄机制：

```text
Java NativeObjectRef.mWrapPtr
        -> C++ NativeWrap { typeId, shared_ptr<void> }
        -> native object T
```

目标是让 Java 不直接拥有 `T*`，而是持有 native 包装器；由 `std::shared_ptr`
管理真实对象生命周期，并明确区分复制引用、转移句柄和释放句柄。

## 先确定任务类型

将请求归入一类：

1. **新建**：在项目中生成完整基础设施和一个可运行示例。
2. **接入**：为一个已有 C++ 类型增加 Java Wrapper、JNI create/access/free。
3. **迁移**：把裸指针或另一套 Handle 迁移到 shared_ptr Handle。
4. **审查/修复**：检查已有实现的所有权、类型安全、并发和清理路径。

用户没有明确要求写代码时，只分析或审查，不修改文件。

## 加载参考

- 开始设计或实现前，完整读取 [references/mechanism-contract.md](references/mechanism-contract.md)。
- 准备编译和交付前，完整读取
  [references/verification-checklist.md](references/verification-checklist.md)。
- 需要从零生成兼容型实现时，读取并改造 `assets/compat-template/`；不要不经适配直接复制。

## 执行流程

### 1. 取证项目约束

只检查任务范围内的文件，确认：

- Java package、基类命名、so 加载方式、最低 Android/JDK 版本。
- JNI 使用静态导出符号还是 `RegisterNatives`。
- C++ namespace、日志/断言、JNI helper、智能指针别名和构建系统。
- 是否已有全局 typeId 注册表、Java native 基类或重复实现。
- 对象是否跨线程使用、是否要求显式释放、是否需要 native 反向创建 Java 对象。

优先复用项目现有约定。只有会改变 ABI、线程模型或资源释放语义的缺失信息才询问用户。

### 2. 声明所有权表

编码前先在工作记录中明确：

| 操作 | Java Handle | NativeWrap | 真实对象引用计数 |
|---|---|---|---|
| create | 获得有效句柄 | 新建 | +1 |
| copy-get | 保持有效 | 保持 | 临时 +1 |
| move-get | 立即失效 | 删除或从注册表移除 | 净值通常不变 |
| close/free | 立即失效 | 删除或从注册表移除 | -1 |
| native-to-Java wrap | 新 Java Wrapper | 新建 | +1 |

如果实际需求不同，先更新此表，再写代码。

### 3. 选择 Handle 后端

根据 `mechanism-contract.md` 选择：

- **direct-wrap**：`jlong` 保存 `NativeWrap*`。适合兼容已有 ABI、对象线程受限的项目。
- **registry**：`jlong` 保存不可复用的 handle id，全局表持有 wrapper。适合新项目、跨线程
  close/copy、需要抵抗陈旧句柄的场景。

已有项目默认保持后端不变。新项目存在跨线程访问时默认 `registry`；线程受限且追求最小开销时
可用 `direct-wrap`，但必须把线程约束写进 API 和测试。

### 4. 实现最小闭环

至少实现：

1. C++ `NativeWrap { typeId, shared_ptr<void> }` 或等价注册表条目。
2. `NewRefWrap/NewRefWrapJlong`。
3. `CopyRefGet<T>`：校验空值和 typeId，复制 `shared_ptr`，Java Handle 保持有效。
4. `MoveRefGet<T>`：原子或受保护地取走 Handle，让 Java 立即失效。
5. Java `close/free`：幂等地释放一个 wrapper 引用。
6. 一个真实 Java 子类和对应 native create/access 示例。
7. 错误映射：不得让普通参数错误无说明地演变成野指针。

按需求实现：

- `hasSameNativeObject`。
- `IsSuchType`。
- `PtrGetFromNativeWrap`；仅限同步、不延长生命周期的明确场景。
- C++ 反向构造 Java Wrapper。
- 手动释放泄漏诊断。

### 5. 遵守硬性实现规则

- `jlong` 只保存包装器地址或注册表 id，禁止把 `std::shared_ptr` 对象位模式塞进 `jlong`。
- 指针与 `jlong` 之间经 `intptr_t/uintptr_t` 转换。
- `typeId` 必须来自集中注册表；新增值前搜索冲突。
- typeId 通过后才能做 `static_pointer_cast`；不能把 Java 类名当成唯一类型保护。
- move 必须先让 Java Handle 失效，再释放 wrapper，且二次 move 必须失败。
- close/free 必须幂等；释放 wrapper 不得直接假设真实对象已经析构。
- 从 JNI 取出的 `shared_ptr<T>` 必须覆盖完整 native 使用区间。
- native-to-Java 构造失败时必须回收刚创建的 wrapper。
- Java 绿色项目优先 `AutoCloseable`；不要新增 `finalize()`。需要兜底时使用项目可用的
  `Cleaner`，且 cleaning action 不得强引用被清理对象。
- direct-wrap 不得声称天然线程安全。并发 close/copy 无法被现有协议证明安全时，使用
  registry、统一线程或外层锁，而不是仅给 Java 字段加 `volatile`。
- JNI 边界不得让 C++ 异常穿过 JNI；按项目约定转换成 Java 异常、错误码或 fatal check。

### 6. 集成

- 将新源文件加入 CMake/ndk-build/Gradle 对应 source set。
- 保留混淆所需的 native 方法、构造器和类。
- 动态注册时接入已有 `JNI_OnLoad`，不要创建第二个冲突入口。
- 静态 JNI 符号必须正确编码 package/class/method 中的下划线。
- 缓存 `jclass` 时使用 GlobalRef，并明确进程期持有或在 `JNI_OnUnload` 释放。

### 7. 验证后交付

按 `verification-checklist.md` 执行：

- 编译目标 native ABI 和 Java/Kotlin 模块。
- 跑 create/copy/move/free/type mismatch/identity 测试。
- 有并发承诺时跑 close-vs-copy、double-close、double-move 压测。
- 检查 ASan/HWASan/LSan 或项目现有 native 内存工具结果。
- 报告实际执行的命令、结果、未验证 ABI 和剩余约束。

未通过编译和关键生命周期测试，不宣称完成。

## 输出要求

实现任务最终说明：

- 采用的 Handle 后端和理由。
- Java、JNI、C++ 三层新增或修改的文件。
- create/copy/move/close 的最终所有权语义。
- typeId、线程模型、错误策略。
- 验证命令与结果。
- 尚未覆盖的 ABI、并发或清理风险。

不要只交付三个孤立文件；必须完成一个真实类型的端到端接入，或者明确说明项目缺少什么依赖。
