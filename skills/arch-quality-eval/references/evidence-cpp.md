# C++ 架构证据

- 优先读取 compile database，用 Clang AST 提取范围内类型依赖；`--cpp-mode clang` 可强制不得降级。
- AST 不可用时用 namespace、目录、include 和显式类型引用定位候选，并降低 confidence 或 coverage。
- namespace/目录只是边界线索；必须确认双方职责后才能判断跨层或依赖方向。
- 记录成功解析的翻译单元及宏、条件编译等缺口。
- 不检查编译错误、模板技巧、指针/所有权风格、宏写法或其他 C++ 语言细节。
- Clang 只用于提取范围内依赖事实；不要把编译成功/失败本身写成架构结论。
