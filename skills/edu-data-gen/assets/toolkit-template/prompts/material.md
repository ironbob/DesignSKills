你是教育内容生成专家。为下面这个学习项生成完整的结构化内容。

产品：{{product_name}}（{{subject}}）
年级：{{grade}}　目标认知层级：{{bloom}}（{{bloom_label}}）
学习项种子：{{seed_json}}
关联知识点：{{knowledge_point_refs}}

严格按下面 schema 输出**一个扁平 JSON 对象**（不要分组嵌套、不要 markdown 代码块、不要解释）：
{{schema_json}}

字段要求：
- id = "{{id}}"；type = "material"；subject="{{subject}}"；grade="{{grade}}"。
- term/释义/音标/词性 等事实必须正确，不得编造；缺失字段留空字符串而非臆造。
- context_sentence 与 examples 难度匹配 {{grade}} × {{bloom}}。
- difficulty_coordinate = {"grade": "{{grade}}", "bloom": "{{bloom}}"}。
- 不要输出 provenance 字段（系统自动注入）。

只输出 JSON 对象本身。
