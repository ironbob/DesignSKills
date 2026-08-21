# 范围与边界

## 范围门

确认五项后才能深挖和定级：路径、JVM/C++、范围文件、是否喂入项目规约、一句话模块职责。首条请求已给齐并明确确认时不重复询问。

## 枚举

- 枚举 `.java/.kt/.h/.hpp/.hh/.cc/.cpp/.cxx`，默认剔除测试和生成/构建产物；用户明确要求时包含。
- 多个根路径合并为 `coverage.scope_files`，不得把范围外文件当 finding 证据。
- `indexed_files`、`inspected_files`、`semantic_resolved_files` 分别记录工具索引、实际精读和语义确认覆盖，不能用 scope 冒充检查完成。
- 混合语言模块按用户确认的主体语言执行，其他语言写入 coverage gap。

## 结构粗识别

- JVM：package、目录和类型角色。
- C++：namespace、目录、include 和 compile database 可用性。

这里只形成范围摘要，不从目录现状推断“项目应有架构”。C++ 也只记录实际 backend，不做语言细节诊断。

## 项目规约

只接受用户手工输入的分层、模块边界、允许/禁止依赖和架构暴露规则，转为 `{id, rule}`。不自动把 `ARCHITECTURE.md`、现有代码或架构测试当作用户规约。

## 超范围请求

- 全仓巡检：要求收窄到 feature/子系统。
- 单文件：可以评价局部边界，但通常不足以给模块级 go；覆盖不足时 verdict 为 inconclusive。
- 完整目标架构、迁移计划、代码风格和语法诊断：明确不在本 Skill 范围。
