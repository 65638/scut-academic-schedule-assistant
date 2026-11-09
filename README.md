# 华工校园学业日程助手

面向华南理工大学大学城校区学生，专业不限。以 WorkBuddy 为交付入口，将校园通知、课表、作业和消息整理为可追溯的个人日程。

## 当前工作

团队成员先看 [协作与交接入口](docs/协作/00-从这里开始.md)。其中有你、A、B、C、D 的工作流程、首批任务、共同样例和交接格式。

A 的平台接入位于 `a/platform-v0`。当前 0.2.0 已接入 B 组审核通过的消息拆项、地点更正和重传去重，并支持载入示例、保存、查询本周安排和跨任务恢复；独立账号访问与隔离仍待实际验收。当前能力和验证步骤以 [A 分支 README](https://github.com/65638/scut-academic-schedule-assistant/blob/a/platform-v0/README.md) 为准。

- [启动方案](docs/启动方案.md)：已确认的范围、阶段和审查标准。
- [A 首批任务](docs/A首批任务.md)：当前实施任务与预期结果。
- [协作约定](AGENTS.md)：开发和交接要求。

C 组 M2 资料与判断模块已放在 `modules/m2/`，包含通知抽取、相关性判断、更正对比、公开栏目刷新、模型提示词、公开资料和回归测试。A 的平台配置仍在独立分支接入。

运行 C 组共同样例：

```sh
python -m modules.m2.cli extract --input modules/m2/fixtures/handoff_c.json
python -m modules.m2.cli compare --input modules/m2/fixtures/handoff_c_correction.json
python -m modules.m2.cli refresh --input modules/m2/fixtures/refresh_sources.json
python -m unittest discover -s modules/m2/tests -v
```

公开资料和来源台账见 `knowledge/`，C 组交接说明见 `modules/m2/HANDOFF.md`。

## 使用边界

通知保留来源和原日期；演示课表、消息和画像明确标注为示例。真实校历与作息采用经核对的大学城校区资料。仅在影响当前行为时询问缺失信息。

产品面向各专业；通知本身的学院、专业、年级限制仍按原文处理。GitHub 仓库用于协作和版本管理，评委最终从 WorkBuddy 入口体验。
