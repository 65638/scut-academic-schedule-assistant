# 华工校园学业日程助手

面向华南理工大学大学城校区学生，专业不限。以 WorkBuddy 为交付入口，将校园通知、课表、作业和消息整理为可追溯的个人日程。

## 当前工作

团队成员先看 [协作与交接入口](docs/协作/00-从这里开始.md)。其中有你、A、B、C、D 的工作流程、首批任务、共同样例和交接格式。

A 的平台接入位于 `a/platform-v0`。0.2.0 随包接入 B 已审核的消息解析与地点更正模块（`0d509c9`）；实际验收见 [M1 接入记录](docs/M1接入.md)。

当前支持载入示例、消息拆项、保存、地点更正、重传去重、本周查询和跨任务恢复。混合消息中的未识别片段保留为待核对问题，缺发送日可原位补充；独立账号隔离仍需实际验收。

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

## 在 WorkBuddy 使用

[打开 0.2.0 测试版：校园学业日程助手](https://www.workbuddy.cn/work/launch/?sharecode=tmL4M5MTT42C01wSjtBwuF-G4pO-ZMywTHyao68tR_kKtZPOn4U7PV6EwWDHz9SJ&buddy_type=workbuddy)

本次分享卡片显示新版本功能，但平台提示“安全检测未完成或失败”。链接落地页 HTTP 200；接收方安装运行、新任务恢复与重传、第二账号隔离仍待 D 实测。以下为测试步骤，不表示这些项目已全部通过；实际证据见 M1 接入记录。

本机安装后，从“专家·技能·连接器 → 我的专家”召唤“华工日程”（职业名“校园学业日程助手”）。

1. 输入“示例模式，保存发送于2026-11-16的消息：明天19:00在A201开M1联调班会，本周五18:00前交M1信息表”。得到 11 月 17 日 19:00 的班会和 11 月 20 日 18:00 截止的交表事项。
2. 输入“示例模式，M1联调班会地点改到A202”。再重传相同原文，保留 A202，不重复建项。新任务重传省略发送日时，可复用唯一的同原文来源；多个来源则先选定。
3. 新建 WorkBuddy 任务并召唤同一专家，输入“查看示例本周安排和待核对问题，今天为2026-11-16”，从个人表恢复；可追溯原消息及更正历史。
4. 输入“查看我本周已保存的真实事项”，只列真实模式的数据，按北京时间当天计算周一至周日。

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

这些命令验证本地计算；`prepare` 不会保存到云端。消息入口为随包 `runtime.py message/location/snapshot`，具体参数见 [专家说明](platform/scut-schedule/README.md)。真实存储调用由 WorkBuddy 原生 library 执行。来源和事项在一行中关联，完整来源、问题及更正历史存于既有 `source` JSON 列，无需迁移表结构。

## 第二账号验收

账号一已在示例模式保存独有合成事项“隔离验收甲 20261108”（11 月 18 日 18:00，地点“测试数据”）。不要仅用双方都有的班会示例判断隔离。账号二通过专家分享链接召唤后：

1. 载入示例，确认随包脚本与示例可运行。
2. 查看示例本周安排（今天 2026-11-16），确认没有账号一的独有标题；再于示例模式创建“隔离验收乙 20261108”。
3. 分别新建任务恢复，确认各自事项仍在，且两个账号互不可见。

用户当前没有第二账号，已决定先交付并保留以上步骤。第二账号访问、随包资源交付和账号隔离保持“未验收”。

B 的消息解析可在仓库根目录运行 `python -X utf8 -m modules.m1.demo` 验证。输入、输出和 A 的调用方式见 [M1 模块说明](modules/m1/README.md)。

## 使用边界

通知保留来源和原日期；演示课表、消息和画像明确标注为示例。真实校历与作息采用经核对的大学城校区资料。仅在影响当前行为时询问缺失信息。

产品面向各专业；通知本身的学院、专业、年级限制仍按原文处理。GitHub 仓库用于协作和版本管理，评委最终从 WorkBuddy 入口体验。

M0 先支持单人顺序操作；平台表格未提供业务编号唯一约束，暂不承诺多会话并发写入的去重。通知判断、课表解析、冲突分析和定时提醒尚未接入。
