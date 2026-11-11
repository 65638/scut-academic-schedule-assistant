# C D4/D5 交付

2026-11-11 定稿。成员：C 组 Yaaaaang520。任务 [#13](https://github.com/65638/scut-academic-schedule-assistant/issues/13)，分支 `codex/c-d4-d5`，基线 `a/platform-v0` 的 `eaaee46`（包含任务卡 `8f66576`）。

## 完成行为

- 从既有 fixture 登记 10 个不同通知来源：1 条真实节选、9 条合成来源，所有更正父来源均在清单内。逐条保留原文、编号、URL/逻辑文件名、日期、收录时间、适用条件、材料与更正指向；合成来源缺失字段明确留空。
- 修复既有材料样例：原文“提交身份证、申请表，办理地点为A101。”没有截止日期，原先遗漏身份证，导致后续更正的材料前值不匹配。本轮仅补材料识别的遗漏，保留原先动作和摘录的支持范围，不推断缺失日期；材料和地点可沿同一业务编号更正，完整原文及历史保留，重放零写。模块和随包实现同步。
- 同一回归发现未知摘录从 `None` 序列化为 CSV 空字符串后，原文重放会误报来源冲突。通知运行时将这两种空值等同处理；有内容的摘录仍严格比较，来源正文与模式的冲突检查保留。
- 复核校历、作息、真实通知与既有栏目标题的公开来源。首次收录时间、旧栏目快照和学校原文不被本轮检查时间覆盖。
- 提供可随包阅读的来源摘要、10 条核对结果、知识库使用方法与实际 Skill/提示词内容版本；没有新增依赖或后台服务。

## 运行与核对

仓库根目录执行（Python 3.9+，仅标准库）：

```sh
python -B -X utf8 tools/check_c_d4_d5.py --out work/c-d4-d5-notices.json
python -B -X utf8 -m unittest discover -s modules/m2/tests -v
python -B -X utf8 -m unittest discover -s tests -p test_notice_runtime.py -v
```

10 条来源的独立预期、实际值、原文、缺项和输入内容哈希见 [通知核对](证据/C-D4-D5-通知核对.json)。U1 的四种适用性也由该脚本实际核对。结果属于本地执行，计划仍为 `saved_to_cloud=false`。

实际结果：修复前 9/10 条通过，C07 漏身份证；修复后 10/10 条及 U1 4/4 通过，模块/随包实现与提示词两组一致性核对通过。受影响的 M2 测试 34/34、通知运行时 16/16 通过。修复前输入/输出与本地运行记录留在忽略目录 `.m2-output/c-d4-d5/`。

源网址、本次 GET 时间、HTTP/重定向及内容匹配结果见 [来源复核](证据/C-D4-D5-来源复核.json) 和 [短台账](../knowledge/D4-D5-来源复核.md)。学校通知的 7 条栏目标题不是 7 篇全文，不能替代正文核验。

新回归使用原材料 fixture，实际保存到本地表格格式 CSV 后执行同一事项的材料与地点更正，再重放原文和更正，最后恢复快照核对业务编号、根来源、原文及一条历史。它会在修复前材料遗漏处失败，不是把本地计划当作云端回读。

## 证据复用范围

- 既有 2023 级原位更正、2022 级新增、确认门槛、完整更正版路由、重放与独立任务恢复，复用 [PR #11](https://github.com/65638/scut-academic-schedule-assistant/pull/11) 的 C **0.4.0** 原生证据。该 PR 已同步最新 A 基线，保留 0.5.0、分享链接与 M3 完成状态；尚未由本交付合并。
- 0.5.0 已发布包的云端结果及 A 的两次独立任务回读分别见 [平台记录](平台验收-0.5.0.md) 与 [A D4/D5 交付](A-D4-D5交付.md)。C 本次未重做这些未变流程，也不把它们记为 C 新平台测试。
- 本轮只运行受材料解析修订影响的 M2 和通知运行时测试；未重复根目录不相关的课表、冲突和呈现测试。

## A 接入口与发布边界

代码入口仍为 `modules/m2/notice.py`、随包 `scripts/m2/notice.py` 和 `scripts/notice_runtime.py`，公共接口不变。知识材料入口为 [发布说明](../knowledge/D4-D5-发布说明.md)；随包位于 `skills/scut-schedule/references/knowledge/`，通知核对结果位于 `references/C-D4-D5-通知核对.json`。

候选包沿用专家版本号 0.5.0，并明确标识为 **C D4/D5 未发布候选**。源包、隔离注册及 ZIP 的实际核对另附包证据；它不能覆盖 [历史发布记录](平台验收-0.5.0.md) 的原包哈希，也不能称为已更新线上专家。

2026-11-11 00:05（UTC+08:00），WorkBuddy 官方 expert-manager 的 validate、隔离 register、package 均退出 0；ZIP CRC 正常，**40 个文件在源包、隔离副本及 ZIP 中逐字节一致**。逐文件 SHA256 见 [包核对](证据/C-D4-D5-包核对.json)。本机交付文件位于根工作区忽略目录 `.m2-output/c-d4-d5/package/scut-schedule.zip`，SHA256 为 `9f26cc1ec547c4cff20f8c470eda6f73eaf12b3373c28d9d7697f734cd8418e0`。这份候选包含材料修复、空摘录重放修复及新增资料，区别于 A 的仅改 README 候选。

接收方可将本分支的 `platform/scut-schedule/` 放到独立 `WORKBUDDY_CONFIG_DIR` 下的 `plugins/marketplaces/my-experts/plugins/scut-schedule`，依次运行内置 expert-manager 的 `validate_expert.py`、`register_expert.py`、`package_expert.py`。独立目录仅用于本地验证；实际平台接入和最终版本由 A 处理。

A 接入代码和资料后决定最终版本号及发布。C 本轮不替换客户端现有专家、不合并 A 分支、不生成新分享。第二账号按当前任务安排跳过，保持未测；本地合成画像与同账号会话不证明跨账号隔离。
