# 华工日程 · 0.5.1 集成源包（M0 + M1 + M2 + M3）

0.5.1 接入 C D4/D5 修复：无截止日期通知的材料完整保留，后续材料／地点更正可回读，空摘录在 CSV 往返后重放不冲突。随包增加来源复核、知识库使用说明和 10 条通知来源的本地核对结果。资料入口为 `skills/scut-schedule/references/knowledge/D4-D5-发布说明.md`；本版平台验收、实际发布状态与分享链接以仓库 README 和 `docs/平台验收-0.5.1.md` 为准。

面向华南理工大学大学城校区各专业。安装后可问：

- 载入示例并查看本周安排。
- 查看我本周已保存的真实事项。
- 帮我把这条消息保存成事项。
- 示例模式，保存发送于 2026-11-16 的消息：明天19:00在A201开班会，本周五18:00前交信息表。
- 示例模式：班会地点改到A202。若有多条班会，先选定需要更正的一条。
- 解读这条校园通知，核对适用条件、所需材料、办理入口和原文依据。
- 示例模式，保存随包报名通知，再将它的截止日期延长到 11 月 27 日，并查看更正依据。
- 示例模式，今天为2026-11-16，查看今晚简报和时间冲突。
- 查看11月17日14:00–18:00内的空档，为预计3小时的作业推荐截止前准备时间。

日程存入当前账号“我的文档”中的“华工个人日程 v0”在线表格。新任务重新读取这张表；示例重复载入会保留已有修改。
示例今天固定为 2026-11-16，班会在 11 月 17 日 19:00、A201；真实日程使用北京时间。

需要 WorkBuddy 原生 library 能力及 Python 3.9+。脚本仅使用标准库，不需要 API Key，不包含作者的个人表格 ID。
消息入口为 `skills/scut-schedule/scripts/runtime.py`，M0 入口为同目录 `schedule.py`，示例为 `skills/scut-schedule/examples/m0-demo.json`。
同目录 `m1/message.py`、`m1/updates.py`、`m1/timetable.py` 与仓库模块一致，以 B 已审核提交 `16413c5` 为基础，0.5.0 仅补明确跨日课程的调动。无需开发仓库即可运行。`runtime.py timetable` 接课表 CSV，`runtime.py update` 接延期、完成、取消和单次调课。
通知入口为同目录 `notice_runtime.py notice/correction/snapshot`，随包 `m2/` 与仓库 C 模块保持一致。提示词及公开资料位于 Skill 的 `references/`，两个通知演示输入位于 `examples/m2-notice-save.json` 和 `examples/m2-notice-correction.json`。

D2 + D3 新增 `knowledge_runtime.py`，可按关键词检索随包公开通知、校历和作息，并按来源编号读取。结果保留原链接、发布日期和收录时间，分别返回整理资料与可用的原文节选；这是本地资料检索，不是在线刷新。0.3.1 修复“部分学院”未知名单的判断，并补齐四字段通知更正案例；版本更新用于区分客户端旧 0.3.0 缓存。本批平台结果见仓库的 `docs/C-D2-D3交付.md`，没有生成新版分享链接。

```sh
python platform/scut-schedule/skills/scut-schedule/scripts/knowledge_runtime.py search --query "求职 补贴"
python platform/scut-schedule/skills/scut-schedule/scripts/knowledge_runtime.py read --source-id scut-student-2026-1027-job-subsidy
```

通知计划默认不写入：先核对适用性，可能相关先确认，明确请求保存后才生成新增载荷；不适用不保存。通知更正沿用原事项编号，材料、对象、完整来源和前后值保存在既有来源 JSON；重传不会回退用户修改。每次计划读取当前账号的新快照，平台增量写入并回读后才确认保存。

从仓库根目录验证源包入口：

```sh
python platform/scut-schedule/skills/scut-schedule/scripts/notice_runtime.py notice --input platform/scut-schedule/skills/scut-schedule/examples/m2-notice-save.json --out work/m2-plan.json
python -m unittest discover -s tests -v
python -m unittest discover -s modules/m2/tests -v
```

第一条只输出 `saved_to_cloud=false` 的计划。更正命令把 `notice` 换成 `correction`，使用更正示例，并通过 `--existing` 传入从本人个人表读取的最新 CSV；不使用首次新增前的空快照进行更正。
通过 WorkBuddy 内置 expert-manager 安装、校验和注册该目录，再从“我的专家”召唤。仓库总 README 记录本次实测结果和未通过项。

支持双事项消息保存、地点原位更正、重复输入不回退、缺发送日补充和混合消息待核对提示。更正历史和完整来源保存于个人表；新任务可恢复。
0.4.0 的课表、调课取消、作业延期完成、通知原位更正及独立任务恢复已于 2026-11-10 通过同账号平台实测。0.5.0 基线新增 M3 呈现，修复完成会议误报、更正依据缺失及跨日保存，并已完成安装、原生平台验收、同账号独立任务回读和专家分享。0.5.1 保留这些能力并修复上述通知材料问题。第二账号按用户决定本次跳过，仍记未测。当前提醒为查询时的对话内提示。

呈现直接读取本轮本人在线表快照：

```sh
python platform/scut-schedule/skills/scut-schedule/scripts/presentation_runtime.py tonight --existing latest.csv --mode example --today 2026-11-16 --out tonight.md
python platform/scut-schedule/skills/scut-schedule/scripts/presentation_runtime.py free --existing latest.csv --mode example --today 2026-11-16 --start 2026-11-17 --end 2026-11-17 --day-start 14:00 --day-end 18:00
```

同一入口支持 week、week-brief、conflicts、prepare，默认 Markdown，`--format json` 输出结构化结果。真实模式省略 today 使用北京时间当天。准备建议需要 `--event-id`、`--minutes` 和上述窗口；只读计算，不改原截止。完整参数见 Skill。模块与包内 presentation.py 字节一致。

无需个人表的本地演示：`python platform/scut-schedule/skills/scut-schedule/scripts/presentation.py tonight --input platform/scut-schedule/skills/scut-schedule/examples/m3-demo.json`。样例保留共同 D 的六项内容，使用独立稳定编号，避免和早期已修改的样例混用；并非当前用户真实日程。

课表示例：

```sh
python platform/scut-schedule/skills/scut-schedule/scripts/runtime.py timetable --csv platform/scut-schedule/skills/scut-schedule/examples/timetable.csv --config platform/scut-schedule/skills/scut-schedule/examples/term-config.json --out work/timetable-plan.json
```

`examples/d2-d3-workflow.json` 中的 assignment 对象可作为 message 输入，其余对象作为 update 输入；更新时加 `--existing` 指向本轮个人表 CSV。输出仍只是待写入计划。
头像由 WorkBuddy 图片生成工具生成，可替换为 512×512 的 PNG/JPG（不超过 500 KB）。
