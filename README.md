# 华工校园学业日程助手

面向华南理工大学大学城校区学生，专业不限。以 WorkBuddy 为交付入口，将校园通知、课表、作业和消息整理为可追溯的个人日程。

## 当前工作

**当前版本：0.5.1，已完成原生验证并发布 WorkBuddy 专家分享。** 本轮已接入 B/C/D 的 D4/D5 交付，修复无日期通知材料遗漏及空摘录重放冲突。实际安装、验收、包哈希与分享入口见 [0.5.1 平台记录](docs/平台验收-0.5.1.md)。

- B 的日期与状态回归：[交接](docs/证据/B-D4-D5/交接.md)。
- C 的材料修复、10 条来源核对：[交付](docs/C-D4-D5交付.md)、[知识库说明](knowledge/D4-D5-发布说明.md)。
- D 的简介、五分钟演示、清单和证据：[0.5.0 材料](docs/交付/0.5.0/README.md)。材料保留原验收版本，当前版本以本页为准。
- A 的 0.5.0 候选和两次独立回读：[历史交付](docs/A-D4-D5交付.md)。本轮沿用未变的同账号恢复证据，第二账号跳过。

0.5.0 已接通周计划、冲突、空档、简报和准备建议，相关历史结果见 [M3 接入](docs/M3接入.md) 与 [0.5.0 平台及发布记录](docs/平台验收-0.5.0.md)。

C 在 0.4.0 的同账号通知、更正版路由、新适用用户及新任务恢复证据见 [C 0.4.0 核验](docs/C-0.4.0联调.md)；该记录保留实际覆盖版本，不作为 C 对 0.5.0 的重新验收。

团队成员先看 [协作与交接入口](docs/协作/00-从这里开始.md)。其中有你、A、B、C、D 的工作流程、首批任务、共同样例和交接格式。

A 的平台接入位于 `a/platform-v0`。0.2.0 随包接入 B 已审核的消息解析与地点更正模块（`0d509c9`）；实际验收见 [M1 接入记录](docs/M1接入.md)。

0.4.0 已于 2026-11-10 完成同账号课表、调课取消、作业延期完成、通知更正与独立任务恢复，见 [0.4.0 平台记录](docs/平台验收-0.4.0.md)。0.5.1 在 0.5.0 的能力上修复通知材料与地点更正，并完成原生验证和新分享。

源包支持载入示例、消息拆项、保存更新、去重、周计划、冲突、准备建议与简报。混合消息中的未识别片段保留为待核对问题，缺发送日可原位补充。第二账号按用户最新决定本次跳过，状态为未测。

- [启动方案](docs/启动方案.md)：已确认的范围、阶段和审查标准。
- [A 首批任务](docs/A首批任务.md)：当前实施任务与预期结果。
- [协作约定](AGENTS.md)：开发和交接要求。
- [平台核查](docs/平台能力核查.md)：原生能力、实测结果和待验收项。
- [专家源包](platform/scut-schedule/)：入口、Skill、示例和计算脚本。

C 组 M2 资料与判断模块位于 `modules/m2/`，包含通知抽取、相关性判断、更正对比、公开栏目刷新、模型提示词、公开资料和回归测试。

```sh
python -m modules.m2.cli extract --input modules/m2/fixtures/handoff_c.json
python -m modules.m2.cli compare --input modules/m2/fixtures/handoff_c_correction.json
python -m modules.m2.cli refresh --input modules/m2/fixtures/refresh_sources.json
python -m unittest discover -s modules/m2/tests -v
```

公开资料和来源台账见 `knowledge/`，C 组交接说明见 `modules/m2/HANDOFF.md`。

复现 C 的 10 条来源及 U1 核对：

```sh
python -B -X utf8 tools/check_c_d4_d5.py --out work/c-d4-d5-notices.json
```

该命令只读取既有样例并输出本地结果，不请求网络或写入个人表。

## 在 WorkBuddy 使用

[打开 0.5.1：校园学业日程助手](https://www.workbuddy.cn/work/launch/?sharecode=4qjU7FO6QIPfgqD-sNHQuUvpDAVEahk1mQwE4xU3kmIvvuj_FJEJu9PZtDXnrTZL&expertname=%E6%A0%A1%E5%9B%AD%E5%AD%A6%E4%B8%9A%E6%97%A5%E7%A8%8B%E5%8A%A9%E6%89%8B&buddy_type=workbuddy)

2026-11-11 从已安装并实测的 0.5.1 专家生成分享；平台安全检测完成后展示分享卡片，并提示“分享链接已复制到剪贴板”。分享地址已从临时草稿回读核对，草稿随后清空且未发送。第二账号本次跳过。GitHub 连接已恢复，0.5.1 代码、发布记录与 D4/D5 任务卡随本次提交推送至 `a/platform-v0`。

本机安装后，从“专家·技能·连接器 → 我的专家”召唤“华工日程”（职业名“校园学业日程助手”）。

1. 输入“示例模式，保存发送于2026-11-16的消息：明天19:00在A201开M1联调班会，本周五18:00前交M1信息表”。得到 11 月 17 日 19:00 的班会和 11 月 20 日 18:00 截止的交表事项。
2. 输入“示例模式，M1联调班会地点改到A202”。再重传相同原文，保留 A202，不重复建项。新任务重传省略发送日时，可复用唯一的同原文来源；多个来源则先选定。
3. 新建 WorkBuddy 任务并召唤同一专家，输入“查看示例本周安排和待核对问题，今天为2026-11-16”，从个人表恢复；可追溯原消息及更正历史。
4. 输入“查看我本周已保存的真实事项”，只列真实模式的数据，按北京时间当天计算周一至周日。

以下是从 `v0.3.0` 起已实测、在后续版本保留的通知主链复现步骤：

1. 输入“示例模式，读取随包 m2-notice-save.json 并明确保存该示例通知”。回读后为 2026-11-25 17:00 截止；再次原样导入应零写入。
2. 输入“示例模式，按随包 m2-notice-correction.json 更正同一事项”。回读后截止改为 2026-11-27 17:00，仍只有一条事项，原来源、报名表 PDF 和更正历史保留。
3. 新建任务并召唤同一专家，输入“示例模式，今天为2026-11-23，恢复已保存的通知事项和更正历史”。本次账号已实测恢复上述更正结果。

个人表名为“华工个人日程 v0”。表格在每个账号自己的“我的文档”中发现和创建，专家包不固定作者的空间或表格 ID。
收到明确“保存”请求后，助手保留来源并写入表格；平台回读成功才确认保存。结束时刻未知则留空。

## 安装与开发

依赖 WorkBuddy 原生 `library`、`expert-manager` 和 Python 3.9+；业务脚本仅使用标准库。
在 WorkBuddy 项目任务中，请内置 expert-manager 将 `platform/scut-schedule/` 安装到当前客户端的专家目录，执行校验和注册。安装目录由该客户端的 `WORKBUDDY_CONFIG_DIR` 决定。
修改源包后同步安装副本、重新校验并注册；不手改 marketplace.json。

从仓库根目录运行：

```sh
python -m unittest discover -s tests -v
python -X utf8 -m modules.m1.demo
python platform/scut-schedule/skills/scut-schedule/scripts/schedule.py prepare --bundle examples/m0-demo.json --out-dir work/demo
python platform/scut-schedule/skills/scut-schedule/scripts/schedule.py week --csv work/demo/schedule.csv --mode example --today 2026-11-16
```

这些命令验证本地计算；`prepare` 不会保存到云端。消息、课表与更新入口为随包 `runtime.py message/timetable/update/location/snapshot`，通知入口为 `notice_runtime.py notice/correction/snapshot`，具体参数见 [专家说明](platform/scut-schedule/README.md)。真实存储调用由 WorkBuddy 原生 library 执行。来源和事项在一行中关联，完整来源、问题及更正历史存于既有 `source` JSON 列，无需迁移表结构。

呈现入口 `presentation_runtime.py week/tonight/week-brief/conflicts/free/prepare` 接本人最新表格 CSV，经 notice_snapshot 恢复后计算。共同合成演示可运行 `python -B -X utf8 -m modules.m3.demo`；完整用法见 [M3 模块](modules/m3/README.md)。

## 第二账号验收

账号一已在示例模式保存独有合成事项“隔离验收甲 20261108”（11 月 18 日 18:00，地点“测试数据”）。不要仅用双方都有的班会示例判断隔离。账号二通过专家分享链接召唤后：

1. 载入示例，确认随包脚本与示例可运行。
2. 查看示例本周安排（今天 2026-11-16），确认没有账号一的独有标题；再于示例模式创建“隔离验收乙 20261108”。
3. 分别新建任务恢复，确认各自事项仍在，且两个账号互不可见。

2026-11-10 用户明确本次跳过第二账号验收并直接发布；以上步骤保留供日后使用。第二账号访问、随包资源交付和账号隔离保持“未测”，不作为本轮发布阻塞。

B 的消息解析可在仓库根目录运行 `python -X utf8 -m modules.m1.demo` 验证。输入、输出和 A 的调用方式见 [M1 模块说明](modules/m1/README.md)。

B 的课表 CSV 本地运行命令为 `python -X utf8 -m modules.m1.timetable --csv modules/m1/examples/timetable.csv --config modules/m1/examples/term-config.json`。

## 使用边界

通知保留来源和原日期；演示课表、消息和画像明确标注为示例。真实校历与作息采用经核对的大学城校区资料。仅在影响当前行为时询问缺失信息。

产品面向各专业；通知本身的学院、专业、年级限制仍按原文处理。GitHub 仓库用于协作和版本管理，评委最终从 WorkBuddy 入口体验。

当前支持单人顺序操作；平台表格未提供业务编号唯一约束，暂不承诺多会话并发写入的去重。提醒为用户查询时的对话内提示，未接后台定时推送。空档按用户给定窗口和已知占用计算，未知时刻会提示核对；准备建议不改教师 DDL。
