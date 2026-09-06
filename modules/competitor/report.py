"""竞品分析报告生成器 —— 把模板 + 用户填写内容编译成可直接使用的 Markdown / HTML 文档。

answers 约定: { section_id: value }
  - 非重复节 repeat=False → value 为 { field_key: str }
  - 重复节   repeat=True  → value 为 [ { field_key: str }, ... ]（每组一行）
空值字段在报告中省略，保证成品干净。
"""
from __future__ import annotations

import html
from datetime import date


def _cn_num(i: int) -> str:
    return "一二三四五六七八九十"[i - 1] if 1 <= i <= 10 else str(i)


def _field_label(tpl_section: dict, key: str) -> str:
    for f in tpl_section.get("fields", []):
        if f["key"] == key:
            return f.get("label", key)
    return key


def _first_text_of(item: dict, section: dict) -> str:
    """取一组数据里第一个有内容的 text 字段当组标题（如竞品名/供应商名），没有则返回空。"""
    for f in section.get("fields", []):
        v = (item.get(f["key"]) or "").strip()
        if v and f.get("type") == "text":
            return v
    return ""


def _section_content(section, answers) -> bool:
    """该节是否填了内容（决定报告里是否保留；重复节任一非空即视为有内容）。"""
    ans = answers.get(section["id"]) if isinstance(answers, dict) else None
    if section.get("repeat"):
        rows = ans if isinstance(ans, list) else []
        return any(isinstance(it, dict) and any((v or "").strip() for v in it.values()) for it in rows)
    item = ans if isinstance(ans, dict) else {}
    return any((v or "").strip() for v in item.values())


def _sections_to_answer_lines(section, item) -> list[tuple[str, str]]:
    """把一组的 field → value 拍平成 (label, value) 列表，跳过空值。"""
    out = []
    for f in section.get("fields", []):
        v = (item.get(f["key"]) or "").strip()
        if v:
            out.append((f.get("label", f["key"]), v))
    return out


def build_markdown(template: dict, answers: dict) -> str:
    today = date.today().isoformat()
    name = template["name"]
    lines: list[str] = []
    lines.append(f"# 竞品分析报告")
    lines.append("")
    lines.append(f"> 模板：{name}　·　生成日期：{today}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 只保留填了内容的节，重新连续编号，避免跳号
    visible = [s for s in template["sections"] if _section_content(s, answers)]
    for i, section in enumerate(visible, 1):
        ans = answers.get(section["id"]) if isinstance(answers, dict) else None
        if section.get("repeat"):
            rows = ans if isinstance(ans, list) else []
            lines.append(f"## {_cn_num(i)}、{section['title']}")
            lines.append("")
            for gi, item in enumerate(rows, 1):
                if not isinstance(item, dict):
                    continue
                title = _first_text_of(item, section) or f"第 {gi} 组"
                lines.append(f"### {title}")
                lines.append("")
                for label, value in _sections_to_answer_lines(section, item):
                    lines.append(f"- **{label}**：{value}")
                lines.append("")
        else:
            item = ans if isinstance(ans, dict) else {}
            pairs = _sections_to_answer_lines(section, item)
            if not pairs:
                continue
            lines.append(f"## {_cn_num(i)}、{section['title']}")
            lines.append("")
            for label, value in pairs:
                lines.append(f"- **{label}**：{value}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("> 报告由「跨境采购助手 · 竞品分析」生成，请结合最新实时数据复核后再做采购/上架决策。")
    return "\n".join(lines).strip() + "\n"


def build_html(template: dict, answers: dict) -> str:
    today = date.today().isoformat()
    e = html.escape

    body: list[str] = []
    body.append(f'<div class="report-head"><h1>竞品分析报告</h1>'
                f'<p class="meta">模板：{e(template["name"])} · 生成日期：{e(today)}</p></div>')

    visible = [s for s in template["sections"] if _section_content(s, answers)]
    for i, section in enumerate(visible, 1):
        ans = answers.get(section["id"]) if isinstance(answers, dict) else None
        if section.get("repeat"):
            rows = ans if isinstance(ans, list) else []
            body.append(f'<h2>{_cn_num(i)}、{e(section["title"])}</h2>')
            for gi, item in enumerate(rows, 1):
                if not isinstance(item, dict):
                    continue
                title = e(_first_text_of(item, section) or f"第 {gi} 组")
                body.append(f'<div class="group"><h3>{title}</h3><dl>')
                for label, value in _sections_to_answer_lines(section, item):
                    body.append(f"<dt>{e(label)}</dt><dd>{e(value)}</dd>")
                body.append("</dl></div>")
        else:
            item = ans if isinstance(ans, dict) else {}
            pairs = _sections_to_answer_lines(section, item)
            if not pairs:
                continue
            body.append(f'<h2>{_cn_num(i)}、{e(section["title"])}</h2><dl>')
            for label, value in pairs:
                body.append(f"<dt>{e(label)}</dt><dd>{e(value)}</dd>")
            body.append("</dl>")

    body.append('<div class="footer">报告由「跨境采购助手 · 竞品分析」生成，请结合最新实时数据复核后再做采购/上架决策。</div>')

    css = """
    body{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;color:#1f2937;margin:0;
         background:#eef1f5;padding:24px;line-height:1.6}
    .sheet{max-width:860px;margin:0 auto;background:#fff;border-radius:10px;box-shadow:0 1px 8px rgba(0,0,0,.08);
           padding:36px 44px}
    h1{font-size:24px;margin:0 0 4px}
    .meta{color:#6b7280;font-size:13px;margin:0 0 16px}
    .report-head{border-bottom:2px solid #1d4ed8;padding-bottom:12px;margin-bottom:20px}
    h2{font-size:18px;margin:26px 0 10px;padding-left:10px;border-left:4px solid #1d4ed8}
    .group{background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;margin:10px 0}
    h3{font-size:15px;margin:0 0 6px;color:#111827}
    dl{margin:0;display:grid;grid-template-columns:minmax(150px,auto) 1fr;gap:4px 14px}
    dt{color:#4b5563;font-size:13px;font-weight:600;text-align:left}
    dd{margin:0;font-size:14px;white-space:pre-wrap;word-break:break-word}
    .footer{color:#9ca3af;font-size:12px;border-top:1px solid #e5e7eb;margin-top:28px;padding-top:10px}
    @media print{.sheet{box-shadow:none;border-radius:0}body{background:#fff;padding:0}}
    """
    doc = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{e(template["name"])} · 竞品分析报告</title><style>{css}</style></head>'
        f'<body><div class="sheet">{"".join(body)}</div></body></html>'
    )
    return doc
