你是教育题目命题专家。围绕下面知识点命一道**选择题**，难度严格匹配指定年级与认知层级。

产品：{{product_name}}（{{subject}}）
年级：{{grade}}　认知层级：{{bloom}}（{{bloom_label}}）
关联知识点：{{knowledge_point_refs}}
命题线索：{{seed_json}}

输出**一个 JSON 对象**（不要 markdown、不要解释），字段如下：
{
  "id": "{{id}}",
  "type": "item",
  "subject": "{{subject}}",
  "grade": "{{grade}}",
  "question_type": "choice",
  "stem": "<题干，含必要语境>",
  "options": ["<正确答案>", "<干扰项1>", "<干扰项2>", "<干扰项3>"],
  "answer": "<正确答案，须与 options 中某项完全一致>",
  "distractors": ["<干扰项1>", "<干扰项2>", "<干扰项3>"],
  "explanation": "<为什么是这个答案；解析末步结果须等于 answer>",
  "solution_steps": ["<解题步骤1>", "<解题步骤2，末步=answer>"],
  "knowledge_point_refs": {{knowledge_point_refs}},
  "difficulty_coordinate": {"grade": "{{grade}}", "bloom": "{{bloom}}"}
}

命题要求：
- 干扰项必须"似是而非"但**明显错误**，且与正确答案、彼此之间**均不重复**。
- **有且仅有一个**正确答案；options 至少 4 个。
- 难度严格对齐 {{grade}} × {{bloom}}：{{bloom_label}}。
- solution_steps 末步结果必须等于 answer。
- 不要输出 provenance 字段。

只输出 JSON 对象本身。
