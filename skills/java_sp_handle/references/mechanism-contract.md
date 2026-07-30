# Mechanism contract

## 目录

1. 不变量
2. 两种 Handle 后端
3. 操作语义
4. Java 层
5. JNI/C++ 层
6. 类型与错误
7. Native 反向创建 Java
8. 常见错误

## 1. 不变量

无论项目如何命名，都必须保持以下不变量：

1. Java 只持有 opaque handle，不解释 C++ 对象布局。
2. 一个有效 wrapper 至少拥有一个 `shared_ptr<void>`。
3. wrapper 的释放只减少一个 shared ownership，不等价于强制析构真实对象。
4. copy-get 返回的 `shared_ptr<T>` 独立覆盖本次 native 使用区间。
5. move-get 成功后，源 Java Handle 永久失效。
6. typeId 不匹配时，不得执行类型转换或访问对象。
7. close/free 可重复调用，不得 double delete。
8. Handle 值为 0 表示空或已释放；有效 id 不使用 0。

Java 引用复制不等于 native shared_ptr 复制：

```java
NativeObjectRef b = a;
```

`a` 和 `b` 是同一个 Java 对象，仍然只有一个 wrapper。只有新建第二个 wrapper 并把同一个
`shared_ptr` 放进去时，native 引用计数才增加。

## 2. 两种 Handle 后端

### direct-wrap

```text
jlong -> NativeWrap*
NativeWrap { uint32_t typeId; shared_ptr<void> object; }
```

优点：

- 实现小、查找 O(1)、无全局表。
- 与大量旧 JNI 代码兼容。

限制：

- `get pointer -> copy shared_ptr` 与另一线程 `delete wrapper` 之间存在 use-after-free 窗口。
- `volatile`、`AtomicLong` 或只同步 Java getter 不能关闭这个 native 窗口。
- 释放后的地址可能被 allocator 重用，陈旧 Handle 更危险。

仅在下列条件之一使用：

- API 明确限定同一线程或串行 executor。
- 外层锁覆盖完整 native 调用和 close。
- 为兼容已有 ABI，且在文档与测试中明确风险。

### registry

```text
jlong id -> mutex-protected map<id, shared_ptr<NativeWrap>>
NativeWrap { typeId; shared_ptr<void> object; }
```

copy-get：

1. 锁注册表。
2. 按 id 查找并复制 `shared_ptr<NativeWrap>`。
3. 解锁。
4. 校验 typeId，复制真实对象的 `shared_ptr`。

close/move：

1. Java 通过 atomic get-and-set 或同步状态把 id 置 0。
2. native 锁注册表并删除 id。
3. 已经完成查找的调用仍持有 `shared_ptr<NativeWrap>`，不会 UAF。

要求：

- id 单调递增或随机生成，避免短期复用。
- 防止溢出后误复用活跃 id。
- 注册表访问统一加锁。
- `JNI_OnUnload` 或进程退出策略明确。

## 3. 操作语义

### create

```cpp
auto object = std::make_shared<T>(...);
return NewRefWrapJlong(object, kType);
```

失败路径不得遗留 wrapper。Java 构造失败、数组写入失败或抛异常时，都要回滚未交付 Handle。

### copy-get

概念实现：

```cpp
auto wrapper = Lookup(handle);
CheckType(wrapper, expectedType);
std::shared_ptr<void> erased = wrapper->object;
return std::static_pointer_cast<T>(erased);
```

copy-get 不改变 Java Handle。返回空对象的策略必须统一：允许 nullable，就返回空；不允许，
就在 JNI 边界抛 `IllegalStateException` 或走项目 fatal 策略。

### move-get

概念实现：

```text
Java: handle = getAndSet(0), moved = true
JNI:  take wrapper, validate type, copy/move object, remove wrapper
C++:  return shared_ptr<T>
```

先校验 typeId 还是先让 Java 失效，需要定义失败语义：

- 兼容旧实现：Java 先失效，type mismatch 视为程序错误并 fatal。
- 可恢复实现：registry 先 lookup/check，再原子消费 id；冲突时重试或返回状态。

不得在 type mismatch 后悄悄恢复一个可能已经暴露给其他线程的 Handle。

### close/free

推荐 Java 语义：

```java
long handle = takeHandleForClose(); // 返回 0 表示已关闭
if (handle != 0) {
    nativeRelease(handle);
}
```

native `release(0)` 可作为 no-op，但不能依赖调用方一定只调用一次。

### identity

“同一个 native 对象”一般比较 `shared_ptr.get()`，不是 wrapper 地址。两个空 Handle 不应被视为
同一有效对象：

```text
if either side is invalid/null -> false
otherwise -> left.object.get() == right.object.get()
```

如果使用 aliasing `shared_ptr`，必须明确 identity 是 stored pointer 还是 ownership control block。

### raw pointer view

`PtrGetFromNativeWrap()` 不增加引用计数。只有当调用方已经持有覆盖完整区间的 wrapper 或
`shared_ptr` 时才能使用；不得把返回的 `T*` 保存到异步任务。

## 4. Java 层

基类应提供：

- opaque `long` 或 `AtomicLong`。
- `getWrapPtr`，仅供受控 JNI helper 使用。
- `moveGetWrapPtr` 或等价的 consume 操作。
- 幂等 `close/free`。
- `isMoved/isClosed`。
- 可选的名称与手动释放诊断。

新项目优先：

```java
public abstract class NativeObjectRef implements AutoCloseable
```

调用方用 try-with-resources 或显式 close。不要新增 `finalize()`。

使用 `Cleaner` 时：

- State 只保存 handle 状态，不保存外层 Java 对象。
- cleaning action 调用静态 native release。
- 显式 close 与 Cleaner 共享同一个原子 take，确保只释放一次。
- Cleaner 是泄漏兜底，不是及时释放保证。

业务子类至少提供接收 `long handle` 的构造器；若 C++ 要反向创建 Java 对象，构造器签名必须稳定，
并配置 R8/ProGuard keep。

## 5. JNI/C++ 层

推荐接口形状：

```cpp
struct NativeWrap;

NativeWrap* NewRefWrap(const std::shared_ptr<void>&, uint32_t typeId);
std::shared_ptr<void> CopyRefGetErased(JNIEnv*, jobject, uint32_t typeId);
std::shared_ptr<void> MoveRefGetErased(JNIEnv*, jobject, uint32_t typeId);

template<class T>
std::shared_ptr<T> CopyRefGet(JNIEnv* env, jobject object, uint32_t typeId);

template<class T>
std::shared_ptr<T> MoveRefGet(JNIEnv* env, jobject object, uint32_t typeId);
```

指针转换：

```cpp
auto value = static_cast<jlong>(reinterpret_cast<intptr_t>(pointer));
auto pointer = reinterpret_cast<NativeWrap*>(static_cast<intptr_t>(value));
```

JNI helper 缓存必须遵守：

- `jclass` 跨调用保存前转换成 GlobalRef。
- `jmethodID/jfieldID` 跟随其 declaring class。
- class-loader 不是默认 loader 时，不盲目依赖 native 线程上的 `FindClass`。
- 检查每次可能产生 Java exception 的 JNI 调用。
- 构造 Java 对象失败时回收未交付 wrapper。

## 6. 类型与错误

typeId 使用集中定义的 `uint32_t` 常量或稳定枚举。四字符多字符字面量在 C++ 中是
implementation-defined；兼容旧 ABI 时可保留，新项目优先显式整数、哈希生成表或枚举生成器。

必须测试：

- 相同 Java 类但错误 typeId。
- 不同 Java 子类共享同一 native 基类 typeId。
- 0 Handle。
- 已 close 和已 move Handle。

错误策略三选一并保持一致：

1. JNI 抛 `IllegalArgumentException/IllegalStateException`。
2. 返回 `Status/Result` 并由 Java 转异常。
3. 对纯内部编程错误记录并 abort。

C++ 异常必须在每个 JNI 导出入口内捕获，不能跨 JNI ABI 展开栈。

## 7. Native 反向创建 Java

流程：

1. 为已有 `shared_ptr<T>` 新建 wrapper。
2. 找到 Java 子类和 `(J)V` 构造器。
3. `NewObject` 交付 Handle。
4. 构造失败则 release wrapper。

如果缓存 class symbol，缓存 key 至少区分 JavaVM/class-loader/class name；单 class-loader 应用可按
项目约束简化。全局缓存需要锁，但不要在持有非递归缓存锁时执行可能重入相同创建逻辑的 Java
构造器。

## 8. 常见错误

- 把 `T*` 当 shared ownership，Java free 后 C++ 仍异步使用。
- `delete wrap->object.get()`，绕过 shared_ptr 控制块。
- copy-get 返回 raw pointer，局部 shared_ptr 立即析构。
- move 后只设置 `moved=true`，却没有清零 Handle。
- Java close 清零发生在 native delete 之后，异常路径造成二次释放。
- 两个无效 Handle 的 identity 返回 true。
- typeId 重复或调用端与创建端不一致。
- 复制一个 `NativeWrap*` 给两个 Java 实例，导致 double delete。
- C++ 创建 Java 对象失败后泄漏 wrapper。
- 用 `finalize()` 承担 GPU、codec、frame buffer 的及时释放。
- 宣称 direct-wrap 跨线程安全，却没有 registry 或覆盖完整调用区间的锁。
