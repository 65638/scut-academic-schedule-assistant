# M1 校园消息解析与地点更正

在仓库根目录使用 Python 3.9 或更高版本运行共享样例。

```sh
python -X utf8 -m modules.m1.demo
python -X utf8 -m modules.m1.demo update
```

[实际输入和 JSON 输出](examples/parse-output.json)涵盖 `B.input`、跨月发送日和缺发送日三组。日期按原发送日计算，本周为周一到周日。没有给出结束时刻时保留 `null`，提交截止时刻放在 `submission.start_time`。

[更正和重放的实际 JSON](examples/update-output.json)涵盖按编号更正、按标题关联、更正后重放原消息、同名候选和选定后重试。

## A 调用方式

```python
from modules.m1.message import parse_message

bundle = parse_message(message)
```

`message` 至少含 `text`。提供原发送日 `sent_on`，格式为 `YYYY-MM-DD`，缺失时用 `null`。合成示例传 `mode="example"`，其余默认真实模式。可传 `today` 表示调用当天，用于展示，省略时取发送日或 `null`。时区固定为 `Asia/Shanghai`。

来源编号优先沿用调用方提供的 `source_id`。未提供时根据模式、发送日和完整原文生成。事项编号由来源、片段和片段位置生成。若已有原始消息编号，A 在补发送日和重放时应沿用同一个 `source_id`。可传 `title` 作为来源标题。

输出的 `sources` 和 `events` 可交给 M0 的 `prepare_import`。有相对日期但缺发送日时，事项的 `pending_fields` 含 `date`，并通过可选的顶层 `questions` 请求发送日。对其他片段明确的输入，按各事项各自计算日期。

单条自定义输入也可通过 CLI 调用。输出为 JSON。

```sh
python -X utf8 -m modules.m1.message message.json
```

### 地点更正与重复导入

```python
from modules.m1.updates import plan_import, propose_location_update

import_plan = plan_import(bundle, current_bundle)
proposal = propose_location_update(update_message, current_bundle)
```

`current_bundle` 是当前账号、当前模式的事项快照，事项使用共享 JSON 字段。新消息调用 `parse_message` 后交给 `plan_import`。将 `import_plan["bundle"]` 交给 M0 的 `prepare_import`，其中 `events` 只含可新增事项。`skipped_event_ids` 列出输入中重复的事项编号。判定依据为稳定事项编号，或相同来源编号下的同一原文片段。缺日期的事项补充原发送日后，由 A 按原事项编号原位补写日期与来源。

更正消息采用 `B.update_input` 的格式。可带 `target_event_id` 指定已选事项，或省略它并按活动标题精确关联。A 可传 `title` 作为更正来源标题，示例使用 `B.update_source.title`。结果含 `source` 完整对象，以及共享的 `target_event_id`、`changes`、`source_id` 和 `source_excerpt`。

当 `target_event_id` 和 `changes` 都有值时，A 在当前记录上应用 `changes`，同时在更正历史中保存新来源及片段，并保留事项原编号和原始来源引用。候选不唯一时，展示 `candidates` 和 `question`，把用户选定的编号作为 `target_event_id` 传回同一条更正。没有匹配项时请用户核对名称。地点已一致时变更为空。

## 当前范围

解析器支持以 ISO 日期、今天、明天、后天、本周星期开头的「在 A201 开班会」和「时刻前交材料」类句式，分句使用逗号、句号、分号或换行。其他句式需扩展后再解析。课表教学周、调课、取消、完成和日历导出属于后续批次。

本批更正句式为「事项名称地点改到新地点」或「事项名称地点改为新地点」，支持一次更正一个地点。重放判定覆盖相同来源的原消息，同义改写待后续处理。WorkBuddy 持久保存、更正历史和账号隔离由 A 接入。

WorkBuddy 集成时可采用[消息处理提示词](prompt.md)。
