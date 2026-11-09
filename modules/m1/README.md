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

混合消息保留已识别的事项和完整原文。「请大家准时参加」这类单独的到场提醒留在原文里。其他暂无法解析的片段在 `questions` 中提示核对，`field` 为 `source_excerpt`，问题中包含待核对的原文片段。

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

消息解析器支持以 ISO 日期、完整中文日期、今天、明天、后天、本周星期开头的「在 A201 开班会」和「时刻前交材料」类句式，分句使用逗号、句号、分号或换行。

本批更正句式为「事项名称地点改到新地点」或「事项名称地点改为新地点」，支持一次更正一个地点。重放判定覆盖相同来源的原消息，同义改写待后续处理。WorkBuddy 持久保存、更正历史和账号隔离由 A 接入。

WorkBuddy 集成时可采用[消息处理提示词](prompt.md)。

## 课表 CSV

```sh
python -X utf8 -m modules.m1.timetable --csv modules/m1/examples/timetable.csv --config modules/m1/examples/term-config.json
```

输入为 UTF-8 八列 CSV 和 [学期配置](examples/term-config.json)，[实际输出](examples/timetable-output.json)为普通 bundle。CSV 的星期用「周一」至「周日」或 1 至 7，起止周如「12–13周」，单双周填「每周」「单周」或「双周」。学期起点是第一教学周周一，节次表填写各节开始和结束时间。示例课程和备注为合成数据，节次、校历和适用范围来自 C 核对的资料。真实课表由 A 传入经核对的对应学期配置及 `mode="real"`，单次停调课另走更新。

A 调用 `modules.m1.timetable.parse_timetable(csv_text, config, file_name=...)`，将结果经 `plan_import(bundle, current_bundle)` 筛选后交给 M0 `prepare_import`。事项编号由模式、学期起点、课程名、原定周次、星期和节次生成。课次共用 CSV 来源和原始行，按课次编号去重。每周示例生成 11 月 17 日和 24 日两次 14:00–15:35 的课，双周只生成 17 日，单周只生成 24 日。

可运行 `python -X utf8 -m unittest discover -s tests -p test_m1_timetable.py -v` 复核单双周、M0 回读、完整重放和仅保存一次后的补齐。

## 作业与状态更新

```sh
python -X utf8 -m modules.m1.demo workflow
```

[输入](examples/d2-d3-workflow.json)和[实际输出](examples/d2-d3-workflow-output.json)包含作业、延期、完成、单次调课、同名候选、取消和旧输入重放。作业用 `parse_message` 生成 `submission`，截止时间放 `start_time`，`end_time` 为 `null`。句末 PDF 保存在来源的 `submission_requirements[event_id]` 中。A 及 D 从快照的 `sources` 按 `event.source_id` 查找来源，再按事项编号读取要求。M0 的 `source` JSON 列已能保存和回读这一映射。

A 使用 `modules.m1.updates.propose_event_update(message, current_bundle)`。消息保留 `text`、原发送日及模式，A 把确认过的操作放入 `kind`，用 `target_event_id` 或精确的 `target_title` 定位目标，可加 `target_date` 指定当前课次日期。日期、时刻使用 `YYYY-MM-DD` 和 `HH:MM`。结果与地点更正共用补丁和候选结构。

| `kind` | 传入的 `changes` |
| --- | --- |
| `postpone` | 提交事项的新 `date`、`start_time`，可只传变化字段 |
| `reschedule` | 单次课程的新 `date`、`start_time`、`end_time`、`location`，可只传变化字段 |
| `cancel` / `complete` | 由模块生成 `status=cancelled` / `status=completed` |

A 从当前个人表读取快照，再对原编号应用补丁。可复用 `runtime.py` 的 `_patch` 生成写入计划，保留原始来源并将补丁前后值和完整新来源追加到 `event_history`。生产编排、个人表回读和独立账号由 A/D 验收。根目录的 `test_m1_workflow.py` 用该适配和本地 CSV 验证实际往返。

## D2 + D3 联调复核

- **C 通知更正。** 已有事项走 `notice_runtime.py correction`，使用已保存目标与当前前值。原版不适用且没有该事项的用户走显式 `newly_applicable: true`，确认适用并要求保存后新增。合成例原先仅覆盖 A 学院 2023 级，更正纳入 2022 级，并将 11 月 25 日 17:00、A101、申请表，改为 11 月 27 日 18:00、B202、申请表和证明材料。本地验证 2023 级原位更新 1 条，2022 级确认后新增 1 条，原文和更正重放均零写入。两条路径回读完整更正来源。见 [M2 接入](../../docs/M2接入.md)及 `test_combined_correction_updates_old_audience_or_adds_new_audience`。
- **D 冲突和空档。** 共同 [D.input_bundle](../../docs/协作/联调样例.json) 的合成课为 11 月 17 日 14:00–15:40，会议为 15:00–16:00，重叠 15:00–15:40。在同日 14:00–18:00 的可安排窗口内，首个空档为 16:00–18:00。该合成课与 CSV 的正式节次换算分别验收。
- **D 截止与状态。** 11 月 20 日 20:00 是截止点。若同日 16:00–19:00 可用，可建议该 3 小时准备时段。今天设为 11 月 30 日时，三天窗口为 11 月 30 日至 12 月 2 日。完成作业和取消课次仍可从快照读到，但应从临期提醒和占用中排除。D 的实际展示及独立账号待联调。
- **U6 导出评估。** 后续可从当前账号的 bundle 生成 `work/calendar.ics`，经 WorkBuddy 的会话文件交付供下载。余量优先用于平台回读与独立账号验收，确认文件交付可用后再估算导出及客户端导入验证。
