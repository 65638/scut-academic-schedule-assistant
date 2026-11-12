# 华工日程 0.5.1 运行文件与工具清单

本清单供 A 定位试用与接入文件，供 D 填写技术、工具和贡献披露。2026-11-12 核对的 A 开发基线为 `2850893682147dd641055647f485f912fe185f9e`，含任务基线 `beca33b`。专家发布版本为 **0.5.1**，发布提交为 `81a1ca4e27f663177b19f40981243cb614a26b6d`。开发基线与发布提交的专家目录逐文件一致。[Issue #17](https://github.com/65638/scut-academic-schedule-assistant/issues/17) · [发布提交](https://github.com/65638/scut-academic-schedule-assistant/commit/81a1ca4e27f663177b19f40981243cb614a26b6d)

## 实际运行文件

发布树的 [platform/scut-schedule](../../../platform/scut-schedule/) 共 **40 个文件**，包括 5 个入口及配套文件、11 个 Python 文件、7 个示例与配置、17 个参考文件。发布 ZIP `scut-schedule-v0.5.1.zip` 的 SHA256 为 `64d90998cd8650d4e712ec46a7d47467e83819e5b316857d8fb8bbbd3feeb56e`。文件数由发布树核对，ZIP 的逐文件一致性和哈希引用 A 的验收记录。[发布树](https://github.com/65638/scut-academic-schedule-assistant/tree/81a1ca4e27f663177b19f40981243cb614a26b6d/platform/scut-schedule) · [包及平台验收](../../平台验收-0.5.1.md)

| 入口及配套文件 | 实际用途 |
| --- | --- |
| [plugin.json](../../../platform/scut-schedule/.codebuddy-plugin/plugin.json) | 声明专家 `scut-schedule`、版本 0.5.1、Agent 和 Skill 路径、提示入口及头像。 |
| [Agent](../../../platform/scut-schedule/agents/scut-schedule.md) · [SKILL.md](../../../platform/scut-schedule/skills/scut-schedule/SKILL.md) | Agent 加载同包 Skill。Skill 编排个人表发现、读取、增改、回读、示例与真实模式及各脚本入口。 |
| [包内 README](../../../platform/scut-schedule/README.md) · [头像](../../../platform/scut-schedule/avatars/expert.png) | README 记录安装和运行方式。头像供专家卡片使用，由 WorkBuddy 图片生成工具生成。 |

| Python 入口 | 用途和随包调用 |
| --- | --- |
| [schedule.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/schedule.py) | M0 将 bundle 变成 15 列 CSV 及新增载荷，按业务编号去重。结构化事项的跨日 `end_date` 放入对应行来源 JSON 的 `event_end_date`。也可读取 CSV 计算本周。 |
| [runtime.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/runtime.py) | M1 的 `message/location/timetable/update/snapshot`。调用 [m1/message.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/m1/message.py) 解析消息和作业，[m1/timetable.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/m1/timetable.py) 展开课次，[m1/updates.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/m1/updates.py) 定位更正、生成补丁、识别重放，以及 M0 读表和准备新增。快照还原来源、历史、提交要求、待确认字段和跨日日期。 |
| [notice_runtime.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/notice_runtime.py) | M2 的 `notice/correction/snapshot`。经 [m2/__init__.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/m2/__init__.py) 加载 [m2/notice.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/m2/notice.py)，校验通知提取、适用性及更正前值，通过 M0 准备新增，并在 M1 快照上补充通知元数据。 |
| [knowledge_runtime.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/knowledge_runtime.py) | `search/read` 从包内台账按关键词或来源编号读取整理资料与可用的原文节选。 |
| [presentation_runtime.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/presentation_runtime.py) | 通过 M2 快照读取当前个人表 CSV，调用 [presentation.py](../../../platform/scut-schedule/skills/scut-schedule/scripts/presentation.py) 计算周计划、冲突、空档、简报和准备建议。后者也可直接读取合成 bundle。 |

| 示例与参考资料 | 用途 |
| --- | --- |
| [m0-demo.json](../../../platform/scut-schedule/skills/scut-schedule/examples/m0-demo.json) · [m3-demo.json](../../../platform/scut-schedule/skills/scut-schedule/examples/m3-demo.json) | M0 班会种子及 M3 周计划、冲突和简报的合成输入。 |
| [timetable.csv](../../../platform/scut-schedule/skills/scut-schedule/examples/timetable.csv) · [term-config.json](../../../platform/scut-schedule/skills/scut-schedule/examples/term-config.json) · [d2-d3-workflow.json](../../../platform/scut-schedule/skills/scut-schedule/examples/d2-d3-workflow.json) | 八列合成课表、学期起点和节次配置，以及可分别提交的作业、延期、完成、单次调课和取消对象。 |
| [m2-notice-save.json](../../../platform/scut-schedule/skills/scut-schedule/examples/m2-notice-save.json) · [m2-notice-correction.json](../../../platform/scut-schedule/skills/scut-schedule/examples/m2-notice-correction.json) · [M2-PROMPT.md](../../../platform/scut-schedule/skills/scut-schedule/references/M2-PROMPT.md) | 合成通知的新增、更正输入及复杂通知的证据抽取提示词。 |
| [知识入口](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/README.md) · [检索台账 JSON](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/source_ledger.json) · [人工核对台账](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/source_ledger.md) | 台账连接 [求职补贴历史通知](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/official/scut_2027_graduate_job_subsidy.md) 与 [原文节选](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/official/scut_2027_graduate_job_subsidy.source.json)、[校历整理](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/official/scut_academic_calendar_2026_2027_1.md) 与 [原始校历](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/official/scut_academic_calendar_2026_2027_1.xlsx)、[大学城作息](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/official/scut_university_town_schedule.md)。分别引用发布者、原链接、日期及适用范围。 |
| [C 的随包参考](../../../platform/scut-schedule/skills/scut-schedule/references/) · [来源复核说明](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/D4-D5-来源复核.md) · [栏目列表对比示例](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/refresh/README.md) | 保存通知回归、来源复核和手动列表对比证据。用户检索走包内台账，栏目列表对比使用人工提供的列表。 |

## 可运行命令与证据

在 **包含 0.5.1 源包的仓库根目录**执行以下 PowerShell 命令。示例均用合成输入，结果写入 `work/b-final-051/`。安装与回退按 [本人优化入口](../../本人优化入口.md) 操作。

```powershell
$skill = 'platform/scut-schedule/skills/scut-schedule'
$work = 'work/b-final-051'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$flow = Get-Content -Raw -Encoding utf8 "$skill/examples/d2-d3-workflow.json" | ConvertFrom-Json
$flow.assignment | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 "$work/message.json"
$flow.reschedule | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 "$work/update.json"

python -B -X utf8 "$skill/scripts/runtime.py" timetable --csv "$skill/examples/timetable.csv" --config "$skill/examples/term-config.json" --out "$work/timetable-plan.json"
python -B -X utf8 "$skill/scripts/runtime.py" message --input "$work/message.json" --out "$work/message-plan.json"
python -B -X utf8 "$skill/scripts/schedule.py" prepare --bundle modules/m1/examples/timetable-output.json --out-dir "$work/course-table"
python -B -X utf8 "$skill/scripts/runtime.py" update --input "$work/update.json" --existing "$work/course-table/schedule.csv" --out "$work/update-plan.json"
python -B -X utf8 "$skill/scripts/notice_runtime.py" notice --input "$skill/examples/m2-notice-save.json" --out "$work/notice-plan.json"
python -B -X utf8 "$skill/scripts/knowledge_runtime.py" search --query "求职 补贴" --out "$work/knowledge.json"
python -B -X utf8 "$skill/scripts/schedule.py" prepare --bundle "$skill/examples/m3-demo.json" --out-dir "$work/demo-table"
python -B -X utf8 "$skill/scripts/presentation_runtime.py" tonight --existing "$work/demo-table/schedule.csv" --mode example --today 2026-11-16 --out "$work/tonight.md"
```

| 本轮复核的路径 | 实际输出 |
| --- | --- |
| 课表与消息计划 | 课表新增载荷 2 条，11 月 17 日及 24 日均为 14:00–15:35。消息新增载荷 1 条，作业截止为 11 月 20 日 20:00，来源中的提交要求为 PDF。 |
| 单次调课计划 | 从 [B 的课表 bundle](../../../modules/m1/examples/timetable-output.json) 生成的 CSV 中定位 11 月 17 日课次，返回 0 新增、1 更新，改至 11 月 18 日、大学城校区 B202。 |
| 通知计划 | 合成报名通知返回 1 新增、0 更新，截止为 11 月 25 日 17:00。 |
| 知识与呈现 | 搜索命中 1 条，来源编号为 `scut-student-2026-1027-job-subsidy`。M3 bundle 生成 6 行示例 CSV，今晚简报含活动确认表和 15:00–15:40 的冲突。 |

本轮 CLI 使用 Python 3.14.6、PowerShell 7.6.9。四类写入计划均返回 `saved_to_cloud=false`。线上调用时，`--existing` 取 **本轮当前账号**由 WorkBuddy 内置 `library` 读取的个人表 CSV，原生增改后逐条回读。通知更正使用 `notice_runtime.py correction`、随包更正输入和包含原目标的最新 CSV。线上查询也从同一入口读取快照；上述合成 CSV 供离线复现。[Skill 的读写及查询流程](../../../platform/scut-schedule/skills/scut-schedule/SKILL.md)

- **0.5.1 原生证据。** A 已实测无日期通知新增 1 条、同一事项材料及地点更正 1 条、两种重放各零写入，并回读原来源和一条历史。[平台验收](../../平台验收-0.5.1.md) · [脱敏原生证据](../../证据/0.5.1-原生材料更正.json) · [版本卡片](../../证据/0.5.1-版本卡片-脱敏.png) · [原生回复](../../证据/0.5.1-原生验收回复-脱敏.png)
- **历史复现。** 0.5.0 的同账号跨任务回读保留原版本。B 的日期、状态和跨日样例复用已合入的 `45256e8`。D 的 [verify_delivery.py](../../../modules/m3/verify_delivery.py) 仅用于在历史提交 `845b73e` 复现 0.5.0 交付材料，运行 `python -B -X utf8 -m modules.m3.verify_delivery --out-dir work/d4-d5-evidence`。[A 同账号跨任务证据](../../A-D4-D5交付.md) · [B 交接及输入输出](../../证据/B-D4-D5/交接.md) · [D 历史交接](../0.5.0/交接单.md)

第二账号按决定跳过，记录为未测。本阶段范围为随包输入、运行与披露，U5 截图输入和 U6 日历导出仍在本阶段范围之外。A 的两张截图用于申报举证。

## 依赖、开发工具与授权披露

| 类别及名称 | 实际用途与版本依据 | 许可或条款依据 |
| --- | --- | --- |
| 运行平台 · 腾讯 WorkBuddy | 专家对话、模型辅助理解、执行 Skill、生成分享卡片。专家为 0.5.1；本轮客户端构建号和原生任务模型版本待核实，需 A 的客户端关于页或任务日志。历史 5.9.3 记录对应早期验收。[0.5.1 验收](../../平台验收-0.5.1.md) · [早期客户端记录](../../M2接入.md) | 使用腾讯平台服务。具体客户端所适用的条款版本待 A 核对。[腾讯云协议入口](https://cloud.tencent.com.cn/document/product/1831/134427) |
| 运行能力 · WorkBuddy 内置 `library` | 发现当前账号个人空间及日程表，读取 CSV，按业务编号定位并增改，原生回读。随 WorkBuddy 客户端提供；0.5.1 验收记录确认调用，组件独立版本待核实，需当次内置 Skill 清单。[Skill](../../../platform/scut-schedule/skills/scut-schedule/SKILL.md) · [原生验收](../../平台验收-0.5.1.md) | 平台内置能力，单独分发许可待核实，需官方组件声明。[腾讯云协议入口](https://cloud.tencent.com.cn/document/product/1831/134427) |
| 运行环境 · Python 标准库 | 包内计算脚本要求 Python **3.9+**。本清单本地验证用 3.14.6。源包脚本导入标准库和随包模块。[包内说明](../../../platform/scut-schedule/README.md) | Python Software Foundation License Version 2，解释器所含组件另见对应版本许可说明。[3.9 许可](https://docs.python.org/3.9/license.html) · [3.14.6 许可文件](https://github.com/python/cpython/blob/v3.14.6/LICENSE) |
| 安装与发布辅助 · WorkBuddy 官方 `expert-manager` | 0.5.1 的源包校验、打包、安装副本校验与注册；不参与用户查询的业务计算。独立组件版本待核实，需当次打包日志中的版本记录。[发布记录](../../平台验收-0.5.1.md) | 平台内置工具，单独分发许可待核实。[腾讯云协议入口](https://cloud.tencent.com.cn/document/product/1831/134427) |
| 开发辅助 · OpenAI Codex | 协助阅读、实现、检查及文档。历史申报底稿有使用记录；项目实际使用的客户端构建号及各次模型版本待核实，需成员会话记录。[既有披露](../0.5.0/申报底稿.md) | OpenAI 服务条款涉及 Codex 与生成代码可能适用的第三方许可，具体账户适用协议待核实。[OpenAI 服务条款](https://openai.com/policies/service-terms/) |
| 版本与协作 · Git、GitHub | Git 管理提交、分支与回退，B 本轮用 Git for Windows `2.55.0.windows.3`。GitHub 用于仓库托管、Issue 与 PR，按托管服务披露。[协作约定](../../协作/00-从这里开始.md) · [Issue #17](https://github.com/65638/scut-academic-schedule-assistant/issues/17) | Git 主体 GNU GPL v2，单个文件的例外见上游。GitHub 托管受服务条款约束。[Git for Windows 对应许可](https://github.com/git-for-windows/git/blob/v2.55.0.windows.3/COPYING) · [GitHub 服务条款](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) |
| 命令复现辅助 · PowerShell | 本轮 7.6.9 用于从工作流 JSON 取出示例对象并执行复现命令。 | [PowerShell 7.6.9 MIT 许可](https://github.com/PowerShell/PowerShell/blob/v7.6.9/LICENSE.txt) |

历史 WorkBuddy 任务记录了 `DeepSeek-V4.1-Flash`（U4／恢复）和 `GLM-5.3`（公开资料检索与解读）。它们按历史平台任务使用披露，0.5.1 没有记录固定模型版本或打包模型权重。若需填写独立模型许可，待 A 提供平台当次模型标识和对应上游依据。头像生成可注明 WorkBuddy 图片生成，具体模型和独立许可待核实，缺生成任务记录。[历史模型证据](../../C-D2-D3交付.md) · [头像说明](../../../platform/scut-schedule/README.md)

原项目计划把 `agent-rules` 列为整理 `AGENTS.md` 的可选工具。现有仓库、发布树与提交记录只确认 [AGENTS.md](../../../AGENTS.md) 已存在，实际使用、上游、版本和许可均待核实，需成员提供调用记录与源链接。D 的已用工具表可先按上表填写。

2026-11-12 查得 GitHub 仓库为公开，仓库元数据 `license: null`。发布树与开发基线均未见统一 `LICENSE`、`COPYING` 或项目许可证声明，历史底稿也记录未声明整体许可。项目授权沿用负责人实际决定。学校公开资料保留出处和范围，第三方再分发授权待对应权利方声明或授权文件确认。[仓库元数据](https://api.github.com/repos/65638/scut-academic-schedule-assistant) · [GitHub 许可说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) · [来源台账](../../../platform/scut-schedule/skills/scut-schedule/references/knowledge/source_ledger.md)

**贡献依据。** A 负责平台、个人表、呈现接入、验收与发布。B 负责消息、课表、日期和状态更新及 D4/D5 验收。C 负责通知适用性、更正与公开资料。D 提供呈现候选、展示验证与申报材料。主管负责审查协调，负责人选择最终材料并主导后续优化。[协作分工](../../协作/00-从这里开始.md) · [0.5.1 实际接入提交](../../平台验收-0.5.1.md) · [最后阶段任务](../../协作/最后阶段-提交准备与本人优化.md)
