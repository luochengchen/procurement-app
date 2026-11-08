# procurement-app · 项目手册

跨境采购助手：Flask + SQLite 单体应用，服务端渲染（Jinja2 + Bootstrap 5 + Chart.js CDN），
另带一个把整站嵌进 DSH Web UI 的本地插件（`dsh-plugin/`）。

## 目录地图

```
app.py              Flask 入口：建表 + 空库 seed + 注册 7 个 blueprint + /api/ping
config.py           路径与外部 API 配置（全部读环境变量）；RENDER=true 时数据写 /tmp
database.py         engine / session / init_db()
models.py           SQLAlchemy 模型
seed_data.py        初始材料分类、材料、认证数据
data.db             运行期 SQLite（已 gitignore；首次启动自动建表 + 空库 seed）
modules/            <name>/__init__.py 定义 blueprint；复杂模块另带 service.py / routes.py
templates/          base.html + 每模块一页 + partials/image_drop.html
static/js/          <name>.js，全部走 fetch("/api/...")
dsh-plugin/         DSH Web UI 入口（反代 /procure，端口 5127）
```

## 七个功能模块

| blueprint | 页面 | 作用 |
|---|---|---|
| dashboard | `/` | 首页概览与快捷入口 |
| materials | `/materials` | 材料库检索与比价 |
| calculator | `/calculator` | 成本核算 / 报价模板 |
| image_search | `/image-search` | 识图搜品（VL 模型） |
| certification | `/certification` | 认证要求查询 |
| factory | `/factory` | 工厂匹配 |
| competitor | `/competitor` | 竞品分析报告 |

## 运行

```powershell
# 开发（debug + 自动重载，端口 5000）
.\.venv\Scripts\python.exe app.py

# 后台无黑窗（端口取 PORT，默认 5000）
$env:PORT=5127; .\.venv\Scripts\pythonw.exe app.py
```

- 依赖已装在 `F:\dsh项目\procurement-app\.venv`：flask 3.1.3、sqlalchemy 2.1.5、requests、openpyxl。
  新增依赖要同步写 `requirements.txt` 并装进 venv。
- 生产入口是 `start.sh`（gunicorn，Render 用），端口读 `$PORT`。
- SQLite 文件是 `data.db`；`app.py` 在 import 阶段建表并在空库时 seed —— gunicorn 多 worker 下也成立，
  但**新增 seed 逻辑必须幂等**。

## 代码约定

- 后端：4 空格缩进、snake_case、`from __future__ import annotations`；蓝图放 `modules/<name>/__init__.py`。
- 路由二分：页面路由返回 `render_template`，数据路由统一挂 `/api/<module>/...` 且返回 JSON。
- 前端：原生 JS + Bootstrap 5；明暗主题靠 `data-bs-theme` + `localStorage.theme`（`templates/base.html` 内已有切换）。
- 模板里静态资源用 `url_for('static', ...)`；不要在模板里写死 `/static/...`。
- 新增页面必须同时挂进 `templates/base.html` 导航。

## 验证要求（改完必做）

1. 后端改动：启动服务，`/api/ping` 200 + 打开受影响页面，确认无 500。
2. 前端改动：真正用 curl/浏览器看渲染结果，不要只做语法检查。
3. 动了路由、静态路径、模板链接：**必须重跑 `dsh-plugin/.selftest.mjs`**（见下）。
4. 恢复现场：测试拉起的后端进程要杀掉（按 `CommandLine` 过滤 `serve.py`，见「坑」）。

## dsh-plugin（DSH Web UI 入口）

- 作用：在 DSH Web UI 左下角加一个图标，点开是宿主内浮窗，内容是本项目整站。
- 结构：`index.js`（HTTP 反代 + 多页路径改写 + 启动中页）· `client.js`（浮窗 UI）· `serve.py`（被 spawn 的后端）·
  `cordis.patch.yml`（root / path `/procure` / port 5127）。
- 已接入：`E:\dsh-home\profiles\desktop\package.json` 的 `dependencies` 与 `dsh.profile.bundles` 各有一条
  `@local/procurement-desk`，`node_modules\@local\` 下是 junction。**改动插件后必须完全重启 DSH 才加载。**
- 自测：`node dsh-plugin\.selftest.mjs`（会自己在 5199 端口拉起后端，先轮询 ping 就绪再断言）；
  `node dsh-plugin\.e2e.mjs`（冷启动 5128，验证 503 → 启动页 → 逐页改写）。
- 关键规则：站点是多页应用，所有根绝对路径（`href="/materials"`、`fetch("/api/...")`、
  `window.location.href = "/factory?q="`）都要被改写成 `/procure/...`。
  **任何新增的导航方式（JS 跳转、表单 action、动态拼接 URL）都要确认改写规则覆盖到；改完跑自测。**

## 坑（踩过的）

- **`pythonw.exe` 是启动器**：真正监听端口的可能是它 CreateProcess 出的孙进程。只杀 launcher 会留孤儿，
  之后再起后端就 `Address already in use`。清理要按 `CommandLine -like '*serve.py*'` 全杀。
- **反代必须要求上游不压缩**：`forward()` 里固定 `'accept-encoding': 'identity'`，否则 HTTP 层拿到 gzip 二进制，
  内存改写会失败、content-length 也对不上。
- **不要用 PowerShell 的 `Get-Content`/`Set-Content` 读写中文文件**：本机 pwsh 是 5.1，会把 UTF-8 当 GBK，
  中文永久损坏。读用 read 工具，写用 write/edit 工具，或用 node 以 utf8 处理。
- **不要为了「能跑在子路径」把模板改成相对路径**：多页应用相对路径会互相错位；统一用绝对路径 + 反代改写。
- `uploads/` 与 `.dsh/` 是运行期目录，不入库（`.gitignore` 已包含 `.dsh/`）。

## 边界

- 不经要求不 `git commit` / `git push`。
- 不擅自升级依赖、不重构现有架构；改数据模型要考虑已有 `data.db`。
- 外部 API key（TIANYANCHA / APEZERO / VISION 等）只走环境变量，不写进代码或提交。
