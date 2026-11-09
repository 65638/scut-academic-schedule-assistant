# C 组 M2 首批交接

成员：C 组 Yaaaaang520

分支：`c/m2-v0`

本首批交付保留原模块验证记录。11 月 9 日第二批核心接入位于 `codex/c-m2-core`，将本模块随包放入 A 的 0.3.0 源包，提供通知保存计划、更正与恢复；实际命令和平台待验项见 [M2 接入记录](../../docs/M2接入.md)。

## 当前行为

1. 从校园通知中抽取适用对象、行动、日期、时刻、材料、入口、地点和原文依据。
2. 对复杂通知接收平台模型按 `PROMPT.md` 生成的候选 JSON，严格校验字段、类型、日期、时刻、完整 URL、连续原文证据和画像一致性，再生成共同 `bundle`。
3. 依据校区、学院、专业、年级和培养层次给出 `明确相关`、`可能相关` 或 `不适用`。
4. 比较通知更正中的日期、开始时刻、结束时刻、适用对象、材料和地点。
5. 比较公开栏目快照，区分新增来源和更正来源。
6. 保留完整来源、收录时间、依据片段和稳定事项编号。

## 运行命令

```powershell
python -m modules.m2.cli extract --input modules/m2/fixtures/handoff_c.json
python -m modules.m2.cli extract --input modules/m2/fixtures/real_job_subsidy.json
python -m modules.m2.cli compare --input modules/m2/fixtures/handoff_c_correction.json
python -m modules.m2.cli refresh --input modules/m2/fixtures/refresh_sources.json
python -m unittest discover -s modules/m2/tests -v
```

## 输入与实际结果

- 共同 C 组样例：输出 `2026-11-25 17:00` 的 `submission`，材料为报名表 PDF，来源摘录与共同样例一致。
- 共同更正样例：目标保持 `handoff-c-event-001`，日期从 `2026-11-25` 更新为 `2026-11-27`。
- B 组独立核对：发送日 `2026-11-16` 时，明天为 `2026-11-17`，本周五为 `2026-11-20`。
- 真实求职补贴通知：输出 `2026-11-10` 的 `submission`，个人截止时刻保持 `null`，院系报送的 10:00 没有写入学生事项。
- U7 合成样例：识别新增 1 条、更正 1 条。
- U7 真实栏目：两次读取 7 条学生工作部首页通知，没有新增或更正，实际输入输出保存在 `knowledge/refresh/`。

实际输出文件：

- `modules/m2/fixtures/handoff_c_output.json`
- `modules/m2/fixtures/handoff_c_correction_output.json`
- `modules/m2/fixtures/refresh_sources_output.json`
- `knowledge/official/scut_2027_graduate_job_subsidy_output.json`
- `knowledge/refresh/student_information_refresh_output.json`

## A 组接入入口

- 直接调用：`modules.m2.extract_notice`、`modules.m2.build_bundle`、`modules.m2.compare_notice_versions`、`modules.m2.refresh_sources`。
- 命令行入口：`python -m modules.m2.cli`。
- 模型输出格式：`modules/m2/PROMPT.md`。
- 公开资料台账：`knowledge/source_ledger.json`。

A 的调用顺序：先读取 `extraction.relevance` 和 `missing_profile_question`。`不适用` 不得直接写入个人表；`可能相关` 先请用户确认。用户确认适用并明确要求保存后，才把候选 `bundle` 交给 M0。共同 `bundle` 结构兼容不代表自动保存授权。

U4 的 CLI 只处理当前代码覆盖的明确日期、时刻、适用对象、材料和地点表达。`PROMPT.md` 的 U4 提示词供平台模型理解复杂更正，模型输出由平台编排层继续校验；本批没有改动 A 的平台实现。

## 验证状态

- 本地 Python 3.12.7：32 项测试通过。
- Python 3.9 兼容语法：已检查当前代码使用的语法和标准库接口。
- A 分支适配器只读验证：共同样例和真实通知均通过导入、重复输入跳过、本周查询及完整来源保留检查。
- GitHub 私有仓库：访问和推送权限已恢复。
- WorkBuddy 平台模型调用与 A 组存储接入：由 A 组在平台分支完成，当前 C 组交付没有声称平台验收通过。
