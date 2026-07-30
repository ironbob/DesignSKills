# Verification checklist

## 目录

1. 静态检查
2. 生命周期测试
3. 类型和身份测试
4. 并发测试
5. Debug 观测测试
6. 集成检查
7. 交付判定

## 1. 静态检查

- Java Handle 字段默认值为 0。
- close/free 和 move 都会使 Handle 变为 0。
- 二次 close 是 no-op；二次 move 有明确失败结果。
- wrapper 只通过唯一 release 路径删除。
- wrapper 内保存 `shared_ptr<void>`，不是仅保存 raw pointer。
- copy-get 在访问对象前完成空值和 typeId 校验。
- `shared_ptr<T>` 覆盖真实 native 使用区间。
- 所有 typeId 在项目范围内唯一。
- 新 Java 子类拥有需要的 `(J)V` 构造器。
- R8/ProGuard 不会移除动态查找的类、构造器或 native 方法。
- C++ 异常不会穿过 JNI。
- direct-wrap 的线程限制已写进 API，并由串行 executor、线程断言或外层锁落实。

## 2. 生命周期测试

使用一个析构时递增计数器的测试类，至少验证：

1. create 后对象存在，close 后最后引用析构一次。
2. copy-get 获得局部 `shared_ptr` 后再串行 close Java Handle，对象在局部引用释放前仍存在。
3. native 组件保存 copy 后，Java close 不析构；组件释放后析构。
4. close 两次只减少一次引用。
5. move 后 Java Handle 为 0，C++ 获得有效对象。
6. move 后 close 不改变引用计数。
7. move 两次失败，且不产生 double delete。
8. C++ 反向创建 Java Wrapper 后，双方释放顺序任意，最终析构一次。
9. Java 构造抛异常时，未交付 wrapper 被释放。

## 3. 类型和身份测试

- 正确 typeId 返回预期类型。
- 错误 typeId 走约定错误路径，不执行 cast。
- null Java object、0 Handle、closed Handle、moved Handle 行为符合契约。
- 两个 wrapper 包装同一 `shared_ptr`，identity 为 true。
- 两个不同对象，identity 为 false。
- 任意一方无效时 identity 为 false。
- 如果项目使用 aliasing `shared_ptr`，增加 identity 定义对应测试。

## 4. 并发测试

本 Skill 的 direct-wrap 不承诺无约束跨线程访问。验证项目采用的保护方式：

- 错误线程调用会被线程断言拒绝；或
- 所有 native access、identity、close、move 进入同一串行 executor；或
- 同一外层锁覆盖从读取 Handle 到复制 `shared_ptr` 的完整 native 操作以及 close/move。

至少增加一个测试证明保护方式真实生效。禁止仅用 `volatile`、`AtomicLong` 或同步 getter
宣称解决 `NativeWrap*` 的并发删除窗口。

## 5. Debug 观测测试

- 创建一个 named wrapper 后，wrapper/object count 都增加 1。
- 同一 `shared_ptr` 创建两个 wrapper，只增加一个 object，wrapperCount 为 2。
- 删除一个 wrapper 后 object 仍为 `wrapped`，wrapperCount 为 1。
- 删除最后一个 wrapper但保留外部 `shared_ptr`，状态变成 `native-only`。
- 释放最后一个强引用后，下一次 dump 会清除 expired object。
- typeId 和 minimumAgeMs 过滤正确。
- dump 与 wrapper 析构并发执行不崩溃、不死锁。
- Tracker 内只存在 `weak_ptr`；查询之外不会临时增加真实对象引用计数。
- Debug hook 抛出或分配失败时，Handle 主流程仍能创建和释放。
- Release 构建返回 `trackingEnabled=false`、count 为 0。
- 输出地址不可被任何 API 重新解析成 Handle。

## 6. 集成检查

- 编译所有目标 ABI，而不是只编译 host C++。
- 验证 32/64 位指针到 `jlong` 的转换。
- 验证 so 在首次 native 调用前加载。
- 动态注册只存在一个有效 `JNI_OnLoad` 集成点。
- native-to-Java 创建在 Java 发起线程和 native 附加线程上都能找到目标类。
- GlobalRef 生命周期明确。
- ASan/HWASan 没有 UAF/double free。
- 项目泄漏工具没有遗留 wrapper。
- Debug target 定义观测宏，Release target 未定义或值为 0。
- Java Debug 查询类随同一个 so 加载，不额外持有业务对象。

建议按项目能力执行：

```text
./gradlew <module>:assembleDebug
./gradlew <module>:testDebugUnitTest
./gradlew <module>:connectedDebugAndroidTest
ctest --test-dir <native-build-dir>
```

不要照抄任务中不存在的命令。先检查 Gradle、CMake、ndk-build 和测试布局，再选择真实命令。

## 7. 交付判定

满足以下条件才可声明完成：

- Java、JNI、C++ 编译通过。
- 至少一个真实类型完成 create -> access -> copy/move -> close。
- 核心生命周期和 type mismatch 测试通过。
- 没有已知 double delete 或 wrapper 泄漏。
- 线程约束声明与实际保护方式相符。
- Debug 查询能区分 `wrapped`、`native-only` 和已清理的 `expired`。

无法运行设备测试时，明确写“未验证”，列出可复现命令，不把静态检查描述成运行通过。
