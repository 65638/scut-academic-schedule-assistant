# 周计划、简报、冲突与准备时段

`presentation.py` 由 D 在 #7 评论 6739188136 的候选修复而来，使用标准库，不写个人数据。A 于 2026-11-10 接入 0.5.0，随包 `scripts/presentation.py` 与本文件夹代码一致。

输入为共同 bundle，`today/mode/timezone/sources/events` 沿用既有约定。用最新个人表时直接运行随包 `presentation_runtime.py --existing`，它先调用 notice_snapshot；不要将原始 CSV 行交给呈现函数。

```sh
python -B -X utf8 -m modules.m3.demo --out-dir work/m3-demo
python -B -X utf8 -m modules.m3.presentation tonight --input work/m3-demo/input.json
python -B -X utf8 -m modules.m3.presentation free --input work/m3-demo/input.json --start 2026-11-17 --end 2026-11-17 --day-start 14:00 --day-end 18:00
```

`build_report(bundle, kind)` 的 kind 为 week、tonight、week-brief；`render_report` 输出 Markdown。`find_conflicts` 返回事项编号与重叠区间；`find_free_slots` 使用明确的日期范围和同日窗口。`suggest_preparation` 取 event_id、预计分钟及窗口，返回独立连续备选和可用总分钟、最长空档、缺口；`render_analysis` 将这些结果转成可读说明。所有 CLI 默认 Markdown，可加 `--format json`。

完成／取消退出提醒和占用；week 保留已完成事项供回顾。三天指今天、明天、后天；仅日期的截止不填时刻，逾期栏目按日期早于今天判断。未知活动区间列待核对，空档标为待核对结果。跨日须显式 end_date，不凭结束时刻较早猜跨日。

来源引用包含原始依据与历史中的更正来源；本周以前的更正仍可追溯。顶层 questions 若已由快照提供，使用其当前值，不恢复 source 中已经解决的问题。作业提交要求与 M2 材料、适用性随事项显示。

示例和实际结果见 demo 输出；相关测试为 `tests/test_presentation.py` 与 `tests/test_m3_integration.py`。这些验证本地行为，不等于 WorkBuddy 平台验收。第二账号按用户决定本次跳过，状态为未测。

D4–D5提交材料与证据见 [交付目录](../../docs/交付/0.5.0/README.md)。运行 `python -B -X utf8 -m modules.m3.verify_delivery --out-dir work/d4-d5-evidence` 可生成本批5组合成呈现核验及源包逐文件校验；不联网、不读取个人快照、不写云端，也不代替平台或第二账号验收。

该脚本限定专家版本 0.5.0，保留用于 D 原交付提交 `845b73e` 的历史复现；不用于验证 0.5.1 的版本或包清单。0.5.1 的实际验证见 [本版平台记录](../../docs/平台验收-0.5.1.md)。
