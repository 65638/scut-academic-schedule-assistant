# A D4/D5 交付

2026-11-10（UTC+08:00）。成员／任务：A，个人表会话边界复核、候选包与实际回读记录。基线 `8f66576`，交付分支 `a/platform-v0`。

## 候选包

版本仍为 **0.5.0**。本轮只修正包内 README 的安装、验收和分享状态；业务脚本、Skill、样例和知识资料未改变。未重新安装或发布专家。

| 文件／记录 | SHA256 | 含义 |
| --- | --- | --- |
| 工作区 `outputs/scut-schedule-v0.5.0-d4d5-candidate.zip` | `54f234cb460e5a3f68837e4e864d6c99016f37bbabe6dbff6728cec871faef59` | 本次候选，36 文件 |
| 工作区 `outputs/scut-schedule-v0.5.0.zip` | 同上 | 已用候选修复的本地交付副本 |
| 已发布 0.5.0 的原包历史记录 | `dd54df4de191e1f036227fd1b7ca4413c81e3454eb1f8d51363e42cd3a6d97d6` | 发布时的原包；不代表现在同名本地 ZIP |

候选相对已发布实现提交 `8433e8b`，忽略 Git 换行差异后只改变 `README.md`。线上专家仍是已发布版本，不能把候选哈希改写成历史发布哈希。

此前暂存目录路径过长，Python 漏收 4 个资料文件，得到不完整 ZIP。改用短暂存目录后，官方校验和打包均退出 0，ZIP CRC 正常，36 文件逐字节等于当前源包；主管另行核对两份本地 ZIP 后确认相同结果。本轮沿用这些证据，没有再次打包或跑全套业务测试。

本机修复记录为工作区 `work/p55/package-result.json`、`validate_expert.py.log`、`package_expert.py.log`。下列命令记录当次短路径校验／打包方法；路径相对工作区 `x-z`，不是要求重新安装：

```powershell
$candidateConfig = (Resolve-Path 'work/p55/c').Path
$candidateExpert = Join-Path $candidateConfig 'plugins/marketplaces/my-experts/plugins/scut-schedule'
$managerScripts = 'C:/Users/21393/.workbuddy/plugins/cache/workbuddy-builtin/skill-expert-manager/5.9.3-wb.42398134.gd4692421.h480e8d1fee0f/scripts'
$pythonExe = 'C:/Users/21393/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$previousConfig = $env:WORKBUDDY_CONFIG_DIR
try {
    $env:WORKBUDDY_CONFIG_DIR = $candidateConfig
    & $pythonExe -B -X utf8 "$managerScripts/validate_expert.py" $candidateExpert
    & $pythonExe -B -X utf8 "$managerScripts/package_expert.py" $candidateExpert 'work/p55/pack'
} finally {
    $env:WORKBUDDY_CONFIG_DIR = $previousConfig
}
```

新接收方安装仍通过 WorkBuddy 内置 expert-manager 导入源包、校验并注册，再从“我的专家”召唤；现有安装无需重做。

## 边界复核与验证

- 原生 library 每个新任务发现当前 `category=personal` 空间，分页查找精确标题“华工个人日程 v0”，核对 database 类型和 `spaceId` 归属；每次操作重新取得在线 CSV。
- 更新由业务事项编号定位唯一平台记录，不按标题或行号更新。脚本不保存账号状态，源码、配置和样例没有固定个人空间、表或记录标识。
- 完成、取消、更正历史及原来源随快照恢复；跨日结束日期通过 `source.event_end_date` 往返保存。
- A 负责的发现、定位、保存与恢复边界未发现需修复的问题。沿用本轮此前已完成的根目录 69 项通过记录；此后业务代码没有变化。本次新增验证仅覆盖两个独立原生任务回读。

## 两个独立原生任务

两个任务均已完成，实际加载安装包 **0.5.0** 与内置 library。每个任务重新发现个人空间和目标表，并调用原生接口取得自己的新 CSV；本轮零云端写入。

| 原生任务 | 在线读取时间（UTC+08:00） | 实际结果 |
| --- | --- | --- |
| 甲：华工日程 0.5.0 D4 验收回读 | 2026-11-10 23:04:06 | 当前个人空间内唯一同名 database；15 列、19 行；四份呈现完成 |
| 乙：华工日程0.5.0 D4独立回读验收乙 | 2026-11-10 23:06:52 | 独立重新发现及读取；15 列、19 行；四份呈现完成 |

A 直接核对两任务的原始响应：节点列表和节点信息的请求 traceid 分别不同；目标均属于本次发现的个人空间；15 个文本字段与 CSV 表头一致，每份 CSV 均等于该任务自己的原生内容响应。两份快照内容一致，SHA256 均为 `1eb45e53931b01125188efebc0a327a0ab4dec707a69e537258f06f396aab0c3`。没有用同一任务的二次读取充数。

| 输入／预期 | 两次实际恢复 |
| --- | --- |
| 已完成作业：保留延期和完成 | `m1-event-63d86109c9e113bd9f324ea0`，2026-11-22 21:00，`completed`；两条 history 为 postpone、complete，原来源和 PDF 要求保留；退出截止提醒 |
| 已取消课程：保留调课和取消 | `m1-course-eac36755927d45228a2b6e3e`，11-18 14:00–15:35，B202，`cancelled`；两条 history 为 reschedule、cancel；不占用时段 |
| 更正通知：恢复最新值与两版来源 | `u4-complete-event-001`，11-25 18:30、B202、申请表及承诺书、2023/2022 级；原通知与一条 notice_correction 历史保留 |
| 两项跨日事项：结束日期不能丢失 | `release-050-night-a/b` 的 `end_date` 均为 11-18；周计划和完整冲突页显示两个 30 分钟区间，共 60 分钟 |

已读取并核对本次输出。乙报告称今晚简报“只列第一段冲突”；检查 `presentation.py` 的 `build_report` 后，确认今晚的冲突窗口只取明日，故 11-18 00:00–00:30 不在 11-17 的分段日期内。该段在周计划与完整冲突页存在，跨日字段未丢失。本轮保留此呈现边界，不将今晚简报写成展示全部 60 分钟。

原始响应、CSV、每次原生报告和四份呈现留在忽略目录 `work/d4-native/session-a/`、`session-b/`；甲使用完整示例快照，乙的 `results/` 只展示指定五条合成事项，并保留完整输出在 `raw/`。甲空间列表原始响应已保存；乙空间列表调用记于原生任务记录和报告，未单独保存该响应。

A 已将两份实际运行时 bundle 的目标字段、完整 history 和原来源原文与在线表逐项比较，全部一致。任务各自的 `business.json` 是字段摘要，完整证据以原生快照和运行时 bundle 为准。可提交的五条业务记录、完整来源／历史和核对摘要见 [独立回读证据](证据/A-D4-D5-独立回读.json)，不含账号、表格、平台记录标识或凭据。

## 接入与剩余项

- 本交付入口为 `platform/scut-schedule/README.md`、上述候选 ZIP 和本记录；不改变公共接口。
- 第二账号按用户决定跳过，记录为未测。本轮两个任务属于同一账号，不能证明跨账号隔离。
- C [PR #11](https://github.com/65638/scut-academic-schedule-assistant/pull/11) 仍由主管接入。已读的有效点是模块工作流四个更新补 `mode=example` 及 0.4.0 证据；包内对应样例已有该字段，不能用 PR 的旧版说明覆盖当前 0.5.0 说明。
- B/C 的 D4/D5 有效修订待交；D 在 [#14](https://github.com/65638/scut-academic-schedule-assistant/issues/14) 回报的 ZIP、核验脚本和材料仍待提供可读取文件。本轮不重复实现。
- 旧外部调用的 OA 授权错误不列为当前阻塞。桌面本地入口已可用，0.5.0 原生保存和回读的既有实测见 [平台记录](平台验收-0.5.0.md)。分享落地页与第二账号状态沿用该记录，未将本轮候选当作新发布。
