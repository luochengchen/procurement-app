# 新工作区开场提示词

> 用法：在 DSH 里新建工作区，目录选 `F:\dsh项目\procurement-app`，把下面「提示词正文」整段粘进第一个会话发出去。
> 项目根目录已有 `AGENTS.md`（项目手册），正常会被自动加载；即使没加载，这段提示词也会要求我先读它。

## 提示词正文

```text
这个工作区只做一件事：维护 F:\dsh项目\procurement-app（跨境采购助手），不要碰其他项目。

第一步：读根目录 AGENTS.md（项目手册：结构、运行命令、七个功能模块、编码约定、验证要求、坑）。
读完后用 3–5 行向我确认你理解的现状，然后等我的任务。不要在这一步改代码。

项目速览（以 AGENTS.md 为准，这里是备份）：
- Flask + SQLite 单体，Jinja2 + Bootstrap 5，7 个 blueprint：
  dashboard(/) / materials(/materials) / calculator(/calculator) / image_search(/image-search)
  / certification(/certification) / factory(/factory) / competitor(/competitor)
- 数据：data.db（根目录），app.py 在 import 阶段建表 + 空库 seed（seed_data.py），改动要幂等
- 配置：config.py 全部走环境变量；RENDER=true 时写 /tmp
- 依赖已装在 .venv：flask 3.1.3、sqlalchemy 2.1.5、requests、openpyxl
- dsh-plugin/ 是本项目在 DSH Web UI 的入口（/procure 同源反代 → 127.0.0.1:5127），
  已接进 desktop profile；改插件后需完全重启 DSH 生效

启动与验证：
  .\.venv\Scripts\python.exe app.py                     # 开发，http://127.0.0.1:5000
  curl http://127.0.0.1:5000/api/ping                    # 期望 {"status":"ok",...}
  node dsh-plugin\.selftest.mjs                          # 动过路由/静态路径/模板链接后必须跑
  node dsh-plugin\.e2e.mjs                               # 冷启动 + 逐页改写验证

工作方式（硬约束）：
- 中文沟通，代码与术语保持英文。
- 先读相关文件再改；改完必须真的启动服务验证（后端看 /api/ping + 目标页面，前端看渲染结果），
  不要只做 py_compile / 语法检查就宣布完成。
- 不改与任务无关的文件；不擅自升级依赖或重构架构；改数据模型要考虑已有 data.db。
- 不 git commit / git push，除非我明确说。
- 测试拉起的后端进程收尾要杀干净（按 CommandLine 过滤 serve.py；pythonw 是启动器，会留孙进程）。
- 不要用 PowerShell 的 Get-Content/Set-Content 读写中文文件（PS 5.1 会按 GBK 解码，永久损坏）。

我的任务：<在这里写这次要做什么>
```

## 后续在这个工作区里的用法

- 每开一个新会话，先让它读 `AGENTS.md`，再直接给任务，不需要重复项目背景。
- 涉及 DSH 入口（浮窗、反代、路径改写）的改动：改完必须跑 `.selftest.mjs`，并提醒我完全重启 DSH。
- 涉及纯业务页面：按「验证要求」跑服务看页面即可。
