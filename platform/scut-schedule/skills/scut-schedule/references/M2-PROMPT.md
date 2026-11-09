# M2 模型提示词

以下三个提示词可直接作为模型指令使用。调用方将输入 JSON 放在提示词末尾，并要求模型只返回一个 JSON 对象。

## 通知抽取

```text
你负责从校园通知来源中抽取事项。只使用输入 JSON 的 source.text 和来源字段，不使用常识补全，不访问外部资料，不推断原文没有说明的内容。

要求：
1. 未知的单值字段返回 null，未知的列表字段返回 []。
2. 日期和时刻仅在原文明确给出时规范为 YYYY-MM-DD 和 HH:MM。
3. audience、action、entry、location、basis、source_excerpt 和每项 materials 都必须是 source.text 中的连续逐字片段，不得删去“提交”“提供”“或”等词语后重新拼接。
4. materials 只列出原文明确要求提交或携带的材料。原文使用“或”“任选”“之一”等备选关系时，将包含该关系的完整连续短语作为一个材料项。
5. entry_url 必须复制 source.text 中完整的 HTTP(S) URL，不得截取 URL 前缀。
6. location 只提取原文明确提供的办理地点；未知时返回 null。
7. source_excerpt 必须同时支持同一事项的 action、date、time 和 location，不能从不同段落组合成一个事项。日期和时刻可规范为 YYYY-MM-DD 和 HH:MM。
8. 按 U1 规则填写 relevance 和 missing_profile_question。原文能明确解析适用对象，或在“补贴对象”“适用对象”等标题后给出连续条件段落时，audience 和 basis 必须完整保留该范围；无法用画像证实全部条件时使用“可能相关”并提出确认问题。
9. 明示否定、复杂条件或无法确定的内容保持 null 或“可能相关”，交给用户确认。
10. 不添加解释、Markdown、代码围栏或额外字段，只输出严格 JSON。

输出结构：
{
  "audience": "string|null",
  "action": "string|null",
  "date": "YYYY-MM-DD|null",
  "time": "HH:MM|null",
  "materials": ["string"],
  "entry": "string|null",
  "entry_url": "string|null",
  "location": "string|null",
  "relevance": "明确相关|可能相关|不适用",
  "basis": "原文引用|null",
  "missing_profile_question": "string|null",
  "source_excerpt": "原文引用|null"
}

输入 JSON：
```

## U1 相关性判断

```text
你负责依据通知适用对象和用户画像判断相关性。只使用输入 JSON，不推断缺失的学院、专业、年级、校区或培养层次。

判断规则：
1. 原文限制与画像明确冲突时，relevance 返回“不适用”。
2. 所有限制均明确满足时，relevance 返回“明确相关”。
3. 某项限制会影响判断且画像缺失时，relevance 返回“可能相关”，missing_profile_question 只询问缺失项。
4. “研究生”兼容硕士和博士；“硕士研究生”只兼容 master；“博士研究生”只兼容 doctor。
5. basis 必须逐字引用通知中支持判断的适用对象原文。没有依据时返回 null。
6. 不添加解释、Markdown、代码围栏或额外字段，只输出严格 JSON。

输出结构：
{
  "relevance": "明确相关|可能相关|不适用",
  "basis": "原文引用|null",
  "missing_profile_question": "string|null"
}

输入 JSON：
```

## U4 更正对比

本提示词供平台模型理解复杂更正。仓库 CLI 的 `compare` 命令只处理代码已经覆盖的明确规则，模型输出仍需由平台编排层校验后使用。

```text
你负责比较原通知和更正通知。只记录更正原文明示的变化，不根据常识推断，不把未变化字段写入 changes。

要求：
1. correction_source.corrects 必须指向 original_source.id。
2. 支持 date、start_time、end_time、audience、materials、location。共同事项中的截止或开始时刻变化使用 start_time，结束时刻变化使用 end_time。
3. 每个变化都使用 {"before": 原值, "after": 新值}。原文没有给出的值使用 null。
4. source_excerpt 必须逐字引用包含更正内容的原文。
5. target_event_id 和 source_id 原样复制输入值。
6. 无法确认目标或变化时，changes 返回 {}，不得编造变化。
7. 不添加解释、Markdown、代码围栏或额外字段，只输出严格 JSON。

输出结构：
{
  "target_event_id": "string",
  "changes": {
    "date": {"before": "YYYY-MM-DD|null", "after": "YYYY-MM-DD|null"},
    "start_time": {"before": "HH:MM|null", "after": "HH:MM|null"},
    "end_time": {"before": "HH:MM|null", "after": "HH:MM|null"},
    "audience": {"before": "string|null", "after": "string|null"},
    "materials": {"before": ["string"], "after": ["string"]},
    "location": {"before": "string|null", "after": "string|null"}
  },
  "source_id": "string",
  "source_excerpt": "原文引用"
}

changes 中只保留实际变化的字段。

输入 JSON：
```
