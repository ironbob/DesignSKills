# 并行轨候选契约

每个分析轨只返回紧凑 JSON，不写报告、不决定 severity/verdict：

```json
{
  "track": "structure-design",
  "principles_checked": ["complexity-management"],
  "coverage": {
    "inspected_files": ["src/OrderService.java"],
    "semantic_resolved_files": [],
    "gaps": []
  },
  "candidates": [{
    "category": "responsibility-mixed",
    "title": "OrderService 混合订单与促销职责",
    "evidence": [{"file": "src/OrderService.java", "line": 42, "note": "depends on PromotionService"}],
    "principles_violated": ["responsibility-cohesion"],
    "convention_rule_ids": [],
    "confidence": "confirmed",
    "impact": "两类变化进入同一职责单元"
  }],
  "inconclusive": ["change-isolation: Git history unavailable"]
}
```

规则：

- 只返回源码可复核事实；大小、扇出和目录名不得直接成为 candidate。
- `confidence` 只表示证据强度，不代替严重度。
- 没有 candidate 也必须返回 `principles_checked` 和覆盖缺口。
- 不重复回传扫描全文、源码全文或推理过程。
- 主分析者负责跨轨去重、分级、优先级、六轴状态和最终 schema。
