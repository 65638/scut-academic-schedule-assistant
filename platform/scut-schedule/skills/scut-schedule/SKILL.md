---
name: scut-schedule
description: 华工大学城校区个人学业日程的示例载入、事项保存、本周查询和跨会话恢复。日程保存在当前账号的 WorkBuddy 个人资料库。
---

# 华工日程 M0

使用 WorkBuddy 内置 library 技能及其正式脚本访问在线表格。本技能的 Python 脚本只计算，不存账号状态，不联网。
源代码位于本技能的 `scripts/schedule.py`，示例位于 `examples/m0-demo.json`。Python 3.9+，仅标准库。

## 找到当前用户的日程表

1. 加载内置 library 技能。通过 `space_api.py space.workspace.list-user-spaces --limit 100` 取得 `category=personal` 的空间；有分页则继续。使用平台返回的 ID，不从本地缓存、用户输入的账号名或示例复制账号标识。
2. 在该空间根目录按 `manage/entry.md` 列出节点并处理分页，定位标题精确为 **华工个人日程 v0**、类型为 `database` 的表。首次未找到时，查询直接告知尚无日程；保存才创建。同名多表时让用户选定，避免误写。
3. 对目标调用 `space.workspace.node-info`，确认 `spaceId` 等于当前个人空间且类型为 `database`。读写只在这张个人表内进行，不把团队或别人分享的表作为个人日程。
4. 每次通过 `database/get_database_content.py --database-id ...` 读取最新 CSV。搜索摘要会滞后，不能用于恢复状态或判断重复。本地 CSV 仅是本次操作的快照，不可用旧文件替代远端读取；新会话重新发现表。

## 载入示例或保存事项

示例使用随包 `examples/m0-demo.json`，演示今天为 2026-11-16，班会为 11 月 17 日 19:00、A201。示例学期不是官方校历。
真实事项沿用示例的 bundle 结构，`mode=real`，`timezone=Asia/Shanghai`，`campus=大学城校区`。保留来源原文、发布日期或发送日；事项和来源使用稳定编号（新事项可用 UUID）。同一来源的重试沿用原编号。
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

## 本批边界

本技能不建立定时提醒、不抓取教务账号、不实现通知相关性或冲突算法。保留原始来源供后续模块使用。
用户要求修改或完成已有事项时，按内置 library 的增量更新流程定位唯一事项并保留来源，更新后回读；重复载入示例不是重置命令。
