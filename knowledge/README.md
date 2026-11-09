# C 组公开资料包

本目录保存华南理工大学校园学业日程助手使用的公开资料。`real` 表示已从无需登录的公开页面核实，`example` 只用于联调。每条资料均保留原始链接、发布单位、发布日期或页面状态、收录时间和适用条件。

## 文件

- `source_ledger.json`：A 组可读取的机器可读来源台账。
- `source_ledger.md`：供人工检查的来源台账。
- `official/scut_2027_graduate_job_subsidy.md`：真实通知正文和人工核对抽取结果。
- `official/scut_2027_graduate_job_subsidy_output.json`：真实通知经过候选校验和 bundle 生成后的实际 CLI 输出。
- `official/scut_academic_calendar_2026_2027_1.md`：校历关键日期与来源说明。
- `official/scut_academic_calendar_2026_2027_1.xlsx`：本科生院公开下载的原始校历文件。
- `official/scut_university_town_schedule.md`：大学城、国际校区公开作息中的上课节次。
- `refresh/student_information_refresh_input.json`：学生工作部公开首页的两次真实栏目快照。
- `refresh/student_information_refresh_output.json`：M2 刷新命令的实际输出。

公开资料更新时，应更新 `ingested_at`，保留旧来源编号，并通过 `corrects` 或版本字段记录更正关系。不得把 `modules/m2/fixtures/` 中的合成示例写成学校真实资料。
