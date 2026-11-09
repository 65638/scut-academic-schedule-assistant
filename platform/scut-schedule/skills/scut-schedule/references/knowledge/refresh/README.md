# 学生工作部公开通知栏目刷新记录

## 栏目

- 页面：https://www2.scut.edu.cn/student/
- 页面单位：华南理工大学学生工作部
- 适用功能：U7 刷新公开栏目

## 本次刷新

- 第一次读取：2026-11-09T00:48:12+08:00
- 第二次读取：2026-11-09T00:50:12+08:00
- 两次页面 SHA256：`0B0927C06147A658AC0E1947C40D910A3242FCF8185942CB313A91AEE0F6F1FF`
- 比较记录：7 条公开通知
- 实际结果：没有新增来源，没有更正来源

两次读取的完整页面字节一致。输入快照保存在 `student_information_refresh_input.json`，M2 CLI 的实际输出保存在 `student_information_refresh_output.json`。该记录只证明本次手动刷新可运行；项目没有启用定时抓取。

运行命令：

```powershell
python -m modules.m2.cli refresh --input knowledge/refresh/student_information_refresh_input.json --output knowledge/refresh/student_information_refresh_output.json
```
