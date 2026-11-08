# 华工校园学业日程助手

面向华南理工大学大学城校区学生，专业不限。以 WorkBuddy 为交付入口，将校园通知、课表、作业和消息整理为可追溯的个人日程。

## 当前工作

团队成员先看 [协作与交接入口](docs/协作/00-从这里开始.md)。其中有你、A、B、C、D 的工作流程、首批任务、共同样例和交接格式。

A 的首批平台代码已推送到 `a/platform-v0`，提交 `5c55bb1`，待主管审查；主分支中的任务包可供 B、C、D 先行开发各自模块。

项目处于 M0 平台接入和 M1 消息解析阶段。A 负责载入示例、保存事项、查询本周安排、重新进入后恢复；B 的消息解析模块负责将混合消息拆成带来源的事项，独立账号隔离仍需实际验收。

- [启动方案](docs/启动方案.md)：已确认的范围、阶段和审查标准。
- [A 首批任务](docs/A首批任务.md)：当前实施任务与预期结果。
- [协作约定](AGENTS.md)：开发和交接要求。
- [平台核查](docs/平台能力核查.md)：原生能力、实测结果和待验收项。
- [专家源包](platform/scut-schedule/)：入口、Skill、示例和计算脚本。

## 在 WorkBuddy 使用

[打开作品：校园学业日程助手](https://www.workbuddy.cn/work/launch/?sharecode=pXgN0nr6Xq7kTkH3y5wNUPK83zPcAxtQCbFURxdRncq8Vx6CX2SvJMvjkJRV9AVS&expertname=%E6%A0%A1%E5%9B%AD%E5%AD%A6%E4%B8%9A%E6%97%A5%E7%A8%8B%E5%8A%A9%E6%89%8B&buddy_type=workbuddy)

本机安装后，从“专家·技能·连接器 → 我的专家”召唤“华工日程”（职业名“校园学业日程助手”）。

1. 输入“载入示例并查看本周安排”。示例今天固定为 2026-11-16，预期出现 11 月 17 日 19:00、A201 的班会。
2. 再次载入不新增记录；修改过的状态、地点保留。
3. 新建 WorkBuddy 任务并召唤同一专家，输入“查看示例本周安排，今天为 2026-11-16”，应从个人表恢复。
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
python platform/scut-schedule/skills/scut-schedule/scripts/schedule.py prepare --bundle examples/m0-demo.json --out-dir work/demo
python platform/scut-schedule/skills/scut-schedule/scripts/schedule.py week --csv work/demo/schedule.csv --mode example --today 2026-11-16
```

这些命令验证本地计算；`prepare` 不会保存到云端。真实存储调用由 WorkBuddy 原生 library 执行。输入结构参见 `examples/m0-demo.json`，来源和事项在一行中关联，完整来源存于 `source` JSON 列。

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
