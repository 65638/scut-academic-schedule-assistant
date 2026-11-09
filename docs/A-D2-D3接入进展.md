# A：D2 + D3 接入进展

2026-11-09，任务 #4。本次交审公开资料检索和展示数据衔接，整批仍在开发中；未同步安装本次新增功能或发布新版分享。

## 可运行部分

`platform/scut-schedule/skills/scut-schedule/scripts/knowledge_runtime.py` 提供 `search --query` 与 `read --source-id`，只用标准库读取随包台账和正文。支持按空格分隔的多个关键词检索，保留原链接、发布日期和收录时间；无匹配返回空列表。只返回有正文的真实来源，不把合成联调通知当公开通知。

读取结果的 `document` 是整理资料，`source` 是可用的原文节选或 null。求职补贴节选从 C 已交付的真实来源对象原样带入，不包含测试画像；`text_scope` 明示为正文节选。个人截止为 2026-11-10，时刻仍为空。校历与作息提供整理资料及原链接。

```sh
python platform/scut-schedule/skills/scut-schedule/scripts/knowledge_runtime.py search --query "求职 补贴"
python platform/scut-schedule/skills/scut-schedule/scripts/knowledge_runtime.py read --source-id scut-student-2026-1027-job-subsidy
python platform/scut-schedule/skills/scut-schedule/scripts/notice_runtime.py snapshot --existing latest.csv --mode example --today 2026-11-17 --out current_bundle.json
```

前两条无需 WorkBuddy 登录；最后一条在平台使用时，`latest.csv` 必须来自本轮本人在线表读取。`notice_runtime.py snapshot` 已能向 D 提供完整 `sources/events/questions`：空值、待确认字段、完成和取消状态、每条事项的 `history`、通知的 `m2.extraction` 和更正来源。D 根据状态筛掉提醒与占用，历史查询仍可使用全部事项；日期变化按 `history[].applied_at` 判断，不能凭当前日期编造。

本次用共同 D 的六项输入，加通知保存与日期更正、混合消息，共八项做本地衔接。生成的 `display-snapshot.json` 包含一条通知更正历史及混合消息待核对问题；对应 `synthetic-schedule.csv` 是本地合成快照，未写入云端。共同样例的课程区间仍为 14:00–15:40。

## 验证与待接入项

- 根目录 `python -B -X utf8 -m unittest discover -s tests -v`：30 项通过，包括新增 4 项公开检索与 1 项混合数据快照测试。检索入口在复制出的独立 Skill 目录中可运行，通知节选与 C 来源对象一致。
- 官方 expert-manager 在临时专家目录校验并打包成功，ZIP 的 29 个文件与源包逐字节一致。仅生成开发交审包，没有注册到当前客户端；插件版本仍沿用 0.3.0，本次内容以 Git 提交识别。
- 本次未修改 B/C 业务模块，沿用基线已有模块测试结果；尚未出现 B 的课表与完整状态更新入口、D 的呈现模块提交。收到实际接口后接入，不预设新 API。
- 官方 `space_api.py space.workspace.list-user-spaces --limit 100` 返回 `E_AUTH_FAILED; msg=PAR failed`。本轮未读写个人表，通知云端保存、回读、更正、新任务恢复、积分消耗未验证。
- 桌面工具返回 `Computer Use native pipe is unavailable`，无法用它继续平台操作或取得新分享链接。此前安装的 0.3.0 与线上 0.2.0 不包含本次检索改动；本次开发源包另列，不替换旧包。
- 当前没有可切换的第二账号，按用户要求先交开发结果。[D 的双向隔离步骤](协作/D-呈现与验收.md)保留，仍记未验收；同账号恢复不代替账号隔离。

平台可用后继续既定链路：读取最新个人表 → 保存随包通知并回读 → 重放零新增 → 更正并回读 → 新任务恢复原编号、材料和历史。然后接 B/D 的实际模块，完成整批联调后交主管审查，再安排新版分享。
