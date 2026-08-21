# 《代码大全2》构造与验证准则

在方案确认后、编码前读取。按已确认边界构造代码，并把检查结果写入 `construction_review.items`；不要为了打勾增加无价值抽象。

## 构造原则

| ID | 编码与复核要求 |
|---|---|
| `cc_routine_quality` | 例程只完成一个目的，名称描述动作；参数、返回值和副作用保持最少。 |
| `cc_defensive_programming` | 在边界校验外部输入；内部断言只表达不应发生的程序错误；建立一致的错误处理边界。 |
| `cc_pseudocode_programming_process` | 对复杂例程先写接近自然语言的结构化步骤，再逐步替换成代码；简单例程标记不适用。 |
| `cc_minimize_variable_scope` | 在首次使用附近声明，限制生命周期和可见范围，避免跨分支共享临时状态。 |
| `cc_one_variable_one_purpose` | 一个变量只表达一个含义；不要复用为不同阶段或不同单位的数据。 |
| `cc_simple_control_flow` | 正常路径清楚，条件正向且分支少；用早返回、命名条件或拆例程降低嵌套。 |
| `cc_design_for_test` | 将时间、随机、网络、存储等不稳定依赖放在可替换边界；验证可观察结果。 |
| `cc_refactor_safely` | 小步修改；每个语义批次后编译并运行最相关测试，避免重构与行为变更混成一次不可诊断改动。 |

同时复核方案阶段的 `cc_class_contract`：构造后对象处于有效状态，公开操作保护不变量，接口不泄漏内部表示。

## Profile 验证矩阵

每类写入 `verification.matrix`，状态为 `covered` 或 `not_applicable`；后者必须给出具体理由。`covered` 必须回链至少一个实际执行的 `VCMD-*`。

- `light`：`compile_or_typecheck`、`affected_tests`、`happy_path`、`invalid_input`。
- `standard`：`light` 全部 + `boundary`、`failure_path`、`integration`。
- `high_risk`：`standard` 全部 + `concurrency`、`idempotency`、`recovery`、`fault_injection`、`spike`。

不要用一句“测试通过”代替证据。命令声明最小受影响 `inputs`，由 `run_verification.py` 无 shell 执行并记录退出码、耗时、输出摘要、时间、命令与输入哈希；代码/测试漂移、失败或未执行的 required 命令禁止 `go`。

## 构造复核

对每个适用项记录 `passed/failed/not_applicable` 与代码或测试证据，至少覆盖：

1. 类型始终维持合法状态且接口最小。
2. 复杂例程使用 PPP，例程保持单一目的。
3. 外部输入、断言和错误边界各司其职。
4. 变量作用域最小且一个变量只有一个用途。
5. 正常路径清楚，控制流不过度嵌套。
6. 不稳定依赖可替换，关键结果可观察。
7. 重构后已编译并运行相关测试。
