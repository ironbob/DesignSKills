# PPT QA 记录

- deck：2026 年上半年个人工作汇报｜8 页｜16:9
- 判定：**PASS**（ERROR 0 / WARN 0）
- 模板：无模板：使用默认 layout library
- 生成：storyboard + facts 共享数据层 → pptxgenjs 原生可编辑 PPTX → LibreOffice PDF → pdftoppm PNG

## storyboard 完整性（check-storyboard）
- ✅ 无 ERROR

## 结构 QA（check-slides：页数/标题/密度/字号/折行/重叠/越界/占位符/图表数字=facts）
- ✅ 无 ERROR

## 渲染 QA（PPTX→PDF→PNG 页数/标题落页）
- ✅ 无 ERROR

## 像素 QA（PNG 边缘溢出检测）
- ✅ 无 ERROR

## PDF 内容断言（pdftotext 逐页标题）
- ✅ 无 ERROR

## 视觉复核记录（人工/AI 逐页）
> 交付前由执行方逐页查看 png/ 并将结论写入 <out>/qa-visual-review.md（重建报告时自动拼回此处）。

- 8/8 页通过（zai-mcp 逐页读图 + pdftotext 数字交叉验证），详见 qa-visual-review.md；修复记录见 deviations.md #3–#5。
