# 设计契约字段指南

仅在 `init_contract.py` 生成的骨架无法通过 `validate_contract.py` 时读取。不要手写完整 JSON 模板；运行：

```bash
python3 <skill-dir>/scripts/init_contract.py \
  --profile <light|standard|high_risk> \
  --stack <JVM|C++|FastAPI+Vue|Swift/iOS> \
  --feature <kebab-case> --title <title> \
  --profile-evidence <用户等级选择摘要> \
  --design-evidence <方案展示后用户确认摘要> \
  --output <design-contract.json>
```

骨架初始为 `no-go`，必须补完真实设计、代码和验证证据后才可交付。

## 顶层

| 字段 | 内容 |
|---|---|
| `feature/title/stack/analyzed_at` | feature 元数据；stack 为四个受支持枚举之一 |
| `existing_alignment` | `recognized_style`、`new_code_follows` |
| `interaction_confirmation` | profile 选择与当前 proposal 后续确认的真实凭据 |
| `design_decision` | profile、质量属性、候选、选型、spike、review、复杂度预算 |
| `ui_architecture` | 仅 UI；当前/目标模式、状态、MVVM、迁移影响与专项确认 |
| `roles/interfaces/business_process` | 角色、关键接口和流程契约 |
| `design_contract_checks` | 编码时软约束 |
| `logging_standard/verification` | 可观察性与真实执行证据 |
| `summary/gate/open_questions` | 计数、四门判断、缺口 |

## 确认凭据

```json
{
  "proposal_revision": 1,
  "profile_selection": {
    "status": "user_selected",
    "selected_profile": "standard",
    "source": "user_message",
    "evidence": "用户选择 standard"
  },
  "design_confirmation": {
    "status": "user_confirmed",
    "confirmed_candidate": "ALT-1",
    "confirmed_revision": 1,
    "source": "later_user_message",
    "evidence": "方案展示后的用户消息确认 ALT-1"
  }
}
```

候选、revision、profile 必须与当前设计一致。方案实质变化后递增 revision 并重新确认。

## Profile 差异

| Profile | 候选 | Review | 额外要求 |
|---|---:|---|---|
| `light` | ≥1 | `self/user/peer/independent` | 默认角色预算 3；超过须写 `exception_reason` |
| `standard` | ≥2 | `user/peer/independent` | 完整质量属性、接口、流程 |
| `high_risk` | ≥2 | `user/peer` | 至少一个 spike，结论需复核 |

`domain_role_decision.status` 为 `applicable` 或 `not_applicable`，并写具体理由；没有真实领域不变量时不要创建领域角色。

## 角色

每个 `roles[]` 项必须有：

- `id`：`ROLE-L<n>` 分层角色或 `ROLE-D<n>` 领域角色；前缀与 `role_kind` 一致。
- `name/role_kind/layer/domain_role`。
- `responsibility/hidden_secret/change_triggers/data_owned`。
- `depends_on`：声明真实角色依赖。
- `industry_basis/design_principles`。
- `code_units`：仓库根相对路径。

多个角色共享同一代码单元时，每个角色填写 `shared_code_unit_reason`。源码引用了未声明角色但属于允许的边界类型时，用：

```json
"source_reference_exceptions": [
  {"role": "ROLE-D01", "reason": "只作为不可变返回 DTO，不调用其行为"}
]
```

优先修正真实依赖，不要用 exception 掩盖反向依赖。

## 接口与流程

`interfaces[]` 每项：`id/name/provider/consumers/input/output/preconditions/postconditions/invariants/errors/data_ownership/transaction/concurrency`。只冻结关键跨角色边界；`light` 单角色才允许空接口。

`business_process[]` 每项：`step/name/roles/code_refs/doc_ref/exception`。代码引用可写 `path:符号`，必须在源码中存在；`doc_ref` 会由 renderer 写入文档。

## 验证

```json
{
  "target": "同一幂等键只创建一次",
  "method": "new_test",
  "status": "passed",
  "evidence": "测试命令输出",
  "test_ref": "src/test/.../OrderTest.java:testDuplicateKey"
}
```

`commands/checks` 的状态为 `passed/failed/skipped`。测试型 check 应提供 `test_ref`；未验证项写 `item/impact/follow_up`。存在失败时 `gate.verification` 不得为 `go`。

## Gate 与汇总

`summary` 六个计数必须与数组一致：`roles_count/interfaces_count/process_steps/verification_checks/layer_roles/domain_roles`。

`gate` 包含 `architecture/logging/coverage/verification/verdict/issues/notes`。四门全 `go` 时 verdict 才能 `go`；`no-go` 至少有一个 critical issue。脚本只能证明结构与文本关系，语义判断和近似限制写入 `notes`。

校验时优先运行：

```bash
python3 <skill-dir>/scripts/validate_all.py <contract.json> <arch.md> --root <repo-root> --summary
```

需要规则明细时才给单个校验器传 `--verbose`。
