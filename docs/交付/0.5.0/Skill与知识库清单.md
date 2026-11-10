# Skill、提示词与知识库清单

对应专家版本0.5.0，业务实现8433e8b，当前材料基线8f66576。本清单描述仓库及随包中实际存在的内容，不表示本批调用了所有平台能力。

## 实际组成与分工

| 项目 | 仓库/源包位置 | 用途与边界 |
| --- | --- | --- |
| 专家声明与角色提示 | `platform/scut-schedule/.codebuddy-plugin/plugin.json`、`agents/scut-schedule.md` | 版本和专家行为入口；不在本批改版 |
| 项目 Skill | `platform/scut-schedule/skills/scut-schedule/SKILL.md` | 当前会话个人表发现、在线读取、写入回读、示例/真实分离、调用M1/M2/M3；随0.5.0发布 |
| 平台内置 library | WorkBuddy 内置，未复制到源包 | 当前个人空间、资料库表结构、增改记录与回读；需要平台实际授权上下文，不由离线CLI替代 |
| 平台 expert-manager | WorkBuddy 官方内置，未复制到源包 | 专家校验、注册与打包；上游已使用，本批仅重建源文件ZIP，不声称重新注册或验证安装副本 |
| M2 提示词 | `modules/m2/PROMPT.md`；随包 `references/M2-PROMPT.md` | 通知抽取、适用性、材料和证据核对；版本以本批基线Git内容为准，无独立版本号 |
| M0/M1/M2/M3 运行脚本 | `scripts/schedule.py`、`m1/`、`m2/notice.py`、`presentation.py`及runtime适配入口 | 保存准备、消息/课表/更新、通知、周计划与分析；Python标准库，无额外数据库或后台服务 |
| 知识检索 | `scripts/knowledge_runtime.py`、`references/knowledge/` | 搜索/读取随包资料，保留来源范围；不是联网抓取和自动订阅 |
| 合成示例 | `examples/m0-demo.json`、`m3-demo.json`、`m2-notice-*.json`、课表CSV与学期配置 | 可复现输入；不能充当真实学校通知或官方校历 |
| 本批交付核验 | `modules/m3/verify_delivery.py` | 开发侧生成合成文本证据及校验源包，不纳入36文件专家源包，不读个人表 |

AI负责理解用户自然语言、按证据提取和组织回复；脚本负责已覆盖规则、日期/状态处理及结构化计算，个人表读写由平台执行。复杂未覆盖表达需原文核对，不能以模型推测补全。开发辅助工具不属于学生使用时的必需运行依赖。

## 随包知识来源摘要

来源台账：`knowledge/source_ledger.json`；源包副本：`references/knowledge/source_ledger.json`。三份真实资料的台账收录时间为2026-11-09T00:32:22+08:00。本批仅读取已有资料，未联网重抓学校网页；公开链接当前可达性及内容是否更新，需C按来源任务复核。

| 资料 | 原发布/范围 | 原始来源 | 本地内容与使用限制 |
| --- | --- | --- | --- |
| 2027届毕业生一次性求职补贴申领通知 | 2026-10-27；全校包含大学城；毕业学年且符合原文三类条件之一 | [学工处通知](https://www2.scut.edu.cn/student/2026/1027/c9326a638593/page.htm) | `official/scut_2027_graduate_job_subsidy.md`及`.source.json`和抽取结果；仅保留的原文范围可作为引文，不扩展适用对象 |
| 2026–2027学年第一学期校历 | 2026-05-22；全校 | [本科生院校历附件](https://jw.scut.edu.cn/zhinan/cms/article/download.do?id=eec18a7b9dfc61df019e4d781cce0095) | `official/scut_academic_calendar_2026_2027_1.xlsx`及整理MD；开学周起点2026-08-31，共20周至2027-01-17；整理文字不是完整网页原文 |
| 大学城校区作息 | 原发布日期未知，不补造；原页覆盖大学城和国际校区 | [本科生院作息安排](https://jw.scut.edu.cn/zhinan/cms/category/index.do?id=f25701314e913361014e91450b510010) | `official/scut_university_town_schedule.md`；使用大学城部分。5–6节14:00–15:35，与联调合成课程14:00–15:40不同，演示中须区分 |
| 示例报名通知 | 合成发布日2026-11-16；大学城全体本科生 | 无真实网页，`联调样例.json#C.input` | `mode=example`、非真实学校机构；本批11-27更正展示取随包样例，不作为真实政策 |

`references/knowledge/refresh/` 是已有资料刷新示例及结果，不能据此宣称持续自动更新。读取知识时保留 `text_scope`，区分“原文摘录”与“整理内容”；适用性不足时先问，不因为项目“专业不限”而忽略通知限制。

## 文件与版本校验

源包包含36文件，具体路径和SHA256见 [源包文件校验.json](证据/源包文件校验.json)。本批ZIP由当前源码重新压缩，文件回读一致；ZIP整体哈希见 [检查结果.json](证据/检查结果.json)。由于压缩元数据等差异，它不是上游官方发布ZIP的逐字节副本，不能拿新哈希替代原发布包哈希。

未对整个项目声明新的开源许可证。复用公开资料保留发布者和URL；提交渠道若要求许可证或资料授权说明，按实际文件及正式规则补充，不推断。
