---
name: scut-schedule
description: 华工大学城校区消息日期与截止解析、个人事项保存、地点更正、重传去重、本周查询和跨会话恢复。日程存于当前账号的 WorkBuddy 个人资料库。
---

# 华工日程 0.2.0 · M0 + M1

使用 WorkBuddy 内置 library 技能及其正式脚本访问在线表格。本技能的 Python 脚本只计算，不存账号状态，不联网。
源代码位于本技能的 `scripts/schedule.py`，示例位于 `examples/m0-demo.json`。Python 3.9+，仅标准库。
消息接入入口是 `scripts/runtime.py`；同目录 `m1/message.py`、`m1/updates.py` 为已审核 B 提交 0d509c9 的原样副本。所有运行文件均在专家包内，不依赖开发仓库。

## 找到当前用户的日程表

1. 加载内置 library 技能。通过 `space_api.py space.workspace.list-user-spaces --limit 100` 取得 `category=personal` 的空间；有分页则继续。使用平台返回的 ID，不从本地缓存、用户输入的账号名或示例复制账号标识。
2. 在该空间根目录按 `manage/entry.md` 列出节点并处理分页，定位标题精确为 **华工个人日程 v0**、类型为 `database` 的表。首次未找到时，查询直接告知尚无日程；保存才创建。同名多表时让用户选定，避免误写。
3. 对目标调用 `space.workspace.node-info`，确认 `spaceId` 等于当前个人空间且类型为 `database`。读写只在这张个人表内进行，不把团队或别人分享的表作为个人日程。
4. 每次通过 `database/get_database_content.py --database-id ...` 读取最新 CSV。搜索摘要会滞后，不能用于恢复状态或判断重复。本地 CSV 仅是本次操作的快照，不可用旧文件替代远端读取；新会话重新发现表。

## 校园消息、地点更正与补发送日

消息输入 JSON：`text` 为完整原文，`sent_on` 为原发送日（YYYY-MM-DD 或 null），`mode` 为 example/real，`today` 为本次查看日。时区 Asia/Shanghai。可传 `source_id`、来源 `title`；地点更正可传 `target_event_id`。保持完整原文，不删掉未识别的分句。

消息运行：`python3 "<本技能目录>/scripts/runtime.py" message --input "<消息.json>" --existing "<本轮在线快照.csv>" --out "<计划.json>"`。
地点更正运行同一命令，把 `message` 换成 `location`。首次没有表时省略 `--existing`，只在计划有 records 时建表。

输入支持：ISO 日期、今天/明天/后天、本周星期；活动“在A201开班会”、提交“18:00前交材料”；更正“班会地点改到A202/改为A202”。不支持的片段按返回 questions 展示核对问题。全句无法解析时报失败，不绕过已审核解析器补造结果。

计划的 `records` 是原生新增载荷，`updates` 每项含 event_id 和原生 properties。生成计划不代表已保存：

1. 有 records：沿用下文 M0 的建表、读结构和 batch_add 流程；不要再把整个原消息 bundle 交给 prepare 重复新增。
2. 有 updates：通过 `query_database_record.py` 读取当前表记录并处理分页，把业务 event_id 精确映射到唯一 record_id，调用 `batch_update_database_records.py`，只写计划 properties。不得按行号或仅按标题盲选。候选不唯一时展示候选，让用户选定后重跑同一更正。
3. 每个新增或更新都以 get_database_record 回读确认，失败项据实报告；全部为空就是无需写入。显示 questions，即使有已成功保存的事项也不省略待核对片段。

缺原发送日先保存无日期事项并询问。用户补充日期时，以**同一完整原文**和原 source_id 重跑 message；若未提供编号，runtime 会从当前表按原文和发送日找回原来源。它只原位补日期、待确认字段和来源，不重置用户改过的地点或状态。不同来源候选无法唯一确定才询问。

来源列仍是原始来源对象，增加 `event_history` 保存本事项的每次更正：前后变化、完整更正来源及实际时间；原 source_id/source_excerpt 不替换。来源的 `questions` 保留混合消息待核对片段。无需加列或迁移旧表；不要把新生成的 source 覆盖回整个表。

交给展示模块或恢复待核对问题时运行 `runtime.py snapshot --existing "<本轮在线快照.csv>" --mode example --today 2026-11-16 --out "<current_bundle.json>"`。结果还原 null、pending_fields 数组，含 sources/events、事项 history、questions。只读取当前模式；新任务也要展示仍待核对的片段。

## 载入示例或保存事项

示例使用随包 `examples/m0-demo.json`，演示今天为 2026-11-16，班会为 11 月 17 日 19:00、A201。示例学期不是官方校历。
此段用于 M0 固定示例或其他模块已经提供的结构化 bundle；普通校园消息优先走上面的 M1 入口。真实事项沿用示例的 bundle 结构，`mode=real`，`timezone=Asia/Shanghai`，`campus=大学城校区`。保留来源原文、发布日期或发送日；事项和来源使用稳定编号（新事项可用 UUID）。同一来源的重试沿用原编号。
时刻未给留空。日期影响本周归属而无法判断时询问用户；只存待确认事项时 date 留空、写明 pending_fields。相对日期依据消息发送日解析，不拿录入日替代历史消息发送日。

1. 读取最新远端 CSV，首次保存没有表时可从空表开始。在本次临时目录准备 bundle 和远端快照。
2. 运行 `python3 "<本技能目录>/scripts/schedule.py" prepare --bundle "<bundle.json>" --existing "<最新.csv>" --out-dir "<临时目录>"`。首次无表省略 `--existing`。输出 `schedule.csv`（合并快照）和 `records.json`（仅新增的原生字段载荷）。脚本的 `saved_to_cloud=false` 表示尚未保存。
3. 首次创建：按内置 `database/create_database.py` 创建标题为“华工个人日程 v0”的表，显式传当前个人 `space_id`，字段采用 CSV 表头，全部 `config={"text":""}`。随后按下一步写入。不要每次上传创建新表。
4. 已有表或刚建表：先读表结构。将 `records.json` 作为 `database/batch_add_database_records.py` 的 records 参数，最多 100 条一批。为空则不写；重复编号保留远端已有内容，不覆盖用户改过的地点、状态等字段。
5. 检查每条返回值，再用 `get_database_record.py` 按返回的 record_id 回读新行，确认字段与准备内容一致后才说“已保存”。接口错误或回读不一致时说明未确认保存，保留输入，不把本地文件成功当云端成功。下一次尝试前先读远端判断是否已写入，不盲目重放整批。

只返回简短保存结果及平台返回的表格链接。链接用 `[查看我的日程](平台返回的URL)` 单独一行，中文标点放在链接之外。个人表保持原有个人权限，不发布、不分享，不把数据或其 ID 写进专家包。M0 采用单人顺序写入；平台没有业务编号唯一约束，不承诺多会话同时写入的去重。

## 查询本周

取得本轮远端 CSV 后运行：

`python3 "<本技能目录>/scripts/schedule.py" week --csv "<最新.csv>" --mode example --today 2026-11-16`

真实模式用 `--mode real`，省略 today 即北京时间当天；用户明确指定某天时传该日。本周按周一到周日计算，示例和真实分别显示，取消事项不列入安排；无日期的记录放入待确认区。
将结果整理成日期、时刻、事项、地点、状态、来源的简表。不要直接把内部 JSON、脚本路径或记录 ID 塞进用户回复。
submission 的 start_time 显示为“截止”；日期未知列入待确认。同时运行 snapshot 恢复来源 questions，避免换会话后丢掉未识别片段。

## 本批边界

本技能不建立定时提醒、不抓取教务账号、不实现通知相关性或冲突算法。地点更正走 M1；用户要求完成已有事项时，按内置 library 的增量更新流程定位唯一事项并保留来源，更新后回读；重复载入示例不是重置命令。
