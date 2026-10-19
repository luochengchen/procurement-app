"""Entry point used by the DSH plugin (dsh-plugin/index.js).

为什么要单独一个入口而不是直接 `python app.py`：
  - app.py 的 `__main__` 里写死 `debug=True`，会额外起一个 reloader 进程（多一个
    python 进程，日志也乱），对一个被宿主拉起的常驻后端没有意义；
  - 插件需要显式绑定 127.0.0.1，避免 Windows 防火墙弹窗。

项目本身（app.py / templates / static）不做任何改动。
"""
from __future__ import annotations

import os
import sys

ROOT = os.environ.get("PROCUREMENT_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from app import app  # noqa: E402  （import 时完成建表与种子数据）

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5127")),
        debug=False,
        use_reloader=False,
        threaded=True,
    )
