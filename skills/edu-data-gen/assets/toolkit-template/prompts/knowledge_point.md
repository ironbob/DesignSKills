你是教育内容设计专家。把下面这个知识点补全为一条完整的教学知识点。

产品：{{product_name}}（{{subject}}）
年级：{{grade}}　基准认知层级：{{bloom}}（{{bloom_label}}）
知识点种子：{{seed_json}}

严格按下面 schema 输出**一个扁平 JSON 对象**（不要分组嵌套、不要 markdown 代码块、不要解释）：
{{schema_json}}

字段要求：
- id = "{{id}}"；type = "knowledge_point"；subject="{{subject}}"；grade="{{grade}}"。
- title 用种子给的标题；summary / objectives / key_exam_points 由你据该年级该知识点补全，事实正确、不超纲、可教学。
- prerequisites 用种子给的；若种子无则按该知识点的前置留空数组。
- difficulty_coordinate = {"grade": "{{grade}}", "bloom": "{{bloom}}"}。
- 不要输出 provenance 字段（系统自动注入）。
- **不要输出 `generation_plan`**：那是大纲规划字段，不进生成数据。

只输出 JSON 对象本身。
