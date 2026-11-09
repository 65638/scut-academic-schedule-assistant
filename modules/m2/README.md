# M2 资料与判断

本模块读取通知来源和可选用户画像，输出结构化抽取结果与共同 `bundle`。同时提供通知更正对比和公开栏目来源列表差异识别。

## 运行环境

- Python 3.9 或更高版本
- 只使用 Python 标准库

## 通知抽取

```powershell
python -m modules.m2.cli extract --input modules/m2/fixtures/handoff_c.json
```

输入顶层字段为 `source` 或 `input`、`profile`、明确的 `today`、可选的 `timezone` 和 `campus`。模型已生成候选结果时，可以传入 `candidate_extraction`；CLI 会校验字段、类型、日期、时刻、相关性、URL 和原文证据后再生成 `bundle`。

候选中的普通文本和每项材料必须是 `source.text` 的连续逐字片段。材料存在“或”“任选”“之一”“确无…提供”等替代条件时，候选保留包含关系的完整短语。URL 必须等于原文中的完整 URL。`action`、规范化后的 `date`、`time` 和 `location` 必须由同一个 `source_excerpt` 支持。原文可明确解析适用对象时，CLI 按原文限制和画像重新计算 `relevance` 与 `missing_profile_question`；“补贴对象”“适用对象”等标题后的连续条件段落也必须完整保留。画像无法证实全部条件时只接受“可能相关”及确认问题。

输出中的 `bundle` 是供 A 组接入的候选结构，不表示已经获得保存授权。A 应先处理 `extraction.relevance` 和 `missing_profile_question`：`不适用` 不写入个人表，`可能相关` 先询问用户；用户确认适用并明确保存后，才把候选 `bundle` 交给 M0。

真实来源必须提供发布单位、绝对 HTTP(S) URL 和带时区的收录时间。发布日期未知时使用 `published_on: null`。

模型提示词见 `modules/m2/PROMPT.md`。

## 更正对比

```powershell
python -m modules.m2.cli compare --input modules/m2/fixtures/handoff_c_correction.json
```

输出包含目标事项编号、字段变化、依据片段和完整更正来源。示例将 `handoff-c-event-001` 的日期从 `2026-11-25` 更新为 `2026-11-27`。CLI 当前处理代码已覆盖的明确日期、时刻、适用对象、材料和地点表达；`PROMPT.md` 的 U4 提示词供平台模型理解更复杂的更正，平台编排层仍需校验模型结果。

## U7 栏目刷新

```powershell
python -m modules.m2.cli refresh --input modules/m2/fixtures/refresh_sources.json
```

输出分别列出新增来源和更正来源。带 `corrects` 且指向旧来源的新编号只归入 `corrected`。

## 测试

```powershell
python -m unittest discover -s modules/m2/tests -v
```

测试覆盖共同 C 组样例、真实通知候选抽取、连续原文证据、完整 URL、同一事项片段、材料备选关系、画像缺失与冲突、来源校验、缺日期事项、多字段更正、栏目新增与更正识别，以及 B 组相对日期的独立预期。

## 已知范围

当前规则处理正文中明确写出的绝对日期、截止时刻、提交行动、材料、入口和适用条件。它不承担通用语义判断；复杂否定、叙事条件和无法确定的适用关系由平台模型与用户共同核对。来源原文没有提供的字段保持 `null`，不会补充推断值。
