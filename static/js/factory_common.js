// 工厂结果渲染公共层 —— 工厂页与识图页共用同一套表格行/详情弹窗渲染。
//
// 抽取原因：此前 factory.js 与 image_search.js 各自复制了一份完全相同的
// escapeHtml / truncate / fmtRevenue / fmtScale / renderRow / renderDetail，
// 改一处要改两遍且已经出现行为不一致（识图页的详情漏渲染了工艺/认证/出口市场）。
//
// 用法：window.FactoryUI.renderRow(f) / window.FactoryUI.renderDetail(f)
// 注意：本文件不声明任何顶层全局变量（仅挂 window.FactoryUI），
// 因为 image_search.js 顶层已有一批全局 const，避免撞名。
(function () {
    "use strict";

    function escapeHtml(s) {
        return String(s ?? "").replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        }[c]));
    }

    function truncate(s, n) {
        s = String(s ?? "");
        return s.length > n ? s.slice(0, n) + "…" : s;
    }

    function fmtRevenue(v) {
        // 年销售额单位：万元 → 自动转「亿/万」
        if (v == null) return "—";
        if (v >= 10000) return `${(v / 10000).toFixed(1)}亿`;
        return `${v}万`;
    }

    // 规模列：真实工商数据没有员工数/厂房面积，用注册资本换算档位并标注口径；
    // 模拟数据把员工/面积/年销售额合并展示，避免「年销售额」在真实数据下永远是空列。
    function fmtScale(f) {
        if (f.is_external) {
            if (!f.scale_label && !f.reg_capital) return "—";
            return [f.scale_label, f.reg_capital].filter(Boolean).join(" · ");
        }
        const parts = [];
        if (f.employees != null) parts.push(`${f.employees}人`);
        if (f.factory_area != null) parts.push(`${(f.factory_area / 10000).toFixed(1)}万㎡`);
        if (f.annual_revenue != null) parts.push(`年销${fmtRevenue(f.annual_revenue)}`);
        return parts.join(" · ") || "—";
    }

    function scaleTitle(f) {
        // 悬停说明规模数字的口径，避免被误读成员工数
        return f.is_external ? (f.scale_basis || "按注册资本换算") : "员工数 · 厂房面积 · 年销售额";
    }

    // 联系方式：采购真正用得上的字段。工商数据提供电话/邮箱，模拟数据没有。
    function contactCell(f) {
        const phone = (f.phone || "").trim();
        const email = (f.email || "").trim();
        if (!phone && !email) return '<small class="text-muted">—</small>';
        const bits = [];
        if (phone) {
            bits.push(`<a class="contact-link" href="tel:${escapeHtml(phone)}" title="点击拨号">
                <i class="bi bi-telephone"></i>${escapeHtml(phone)}</a>`);
        }
        if (email) {
            bits.push(`<a class="contact-link" href="mailto:${escapeHtml(email)}" title="${escapeHtml(email)}">
                <i class="bi bi-envelope"></i>邮箱</a>`);
        }
        bits.push(`<button type="button" class="btn btn-sm btn-link p-0 copy-contact"
            data-copy="${escapeHtml([phone, email].filter(Boolean).join(" / "))}"
            title="复制联系方式"><i class="bi bi-clipboard"></i></button>`);
        return `<div class="d-flex flex-wrap align-items-center gap-2">${bits.join("")}</div>`;
    }

    // 标记「生产型 / 可出口」—— 工商经营范围解析出来的关键结论
    function capabilityBadges(f) {
        const out = [];
        if (f.is_manufacturer) out.push('<span class="badge-soft text-success">生产型</span>');
        if (f.can_export) out.push('<span class="badge-soft">可出口</span>');
        if (f.belt) out.push(`<span class="badge-soft" title="${escapeHtml(f.belt)}">产业带</span>`);
        return out.join("");
    }

    // 「可生产产品」列：优先用经营范围解析出的品类词，解析不出再回退整段经营范围
    function productCell(f) {
        const matched = new Set(f.matched_products || []);
        if (f.main_products && f.main_products.length) {
            return f.main_products.slice(0, 5).map((p) => {
                const hit = matched.has(p);
                return `<span class="badge border${hit ? " badge-soft" : ""}" style="margin:1px">${escapeHtml(p)}${hit ? " <i class='bi bi-check2'></i>" : ""}</span>`;
            }).join("");
        }
        if (f.is_external && f.business_scope) {
            return `<small class="text-muted" title="${escapeHtml(f.business_scope)}">${escapeHtml(truncate(f.business_scope, 40))}</small>`;
        }
        return '<small class="text-muted">—</small>';
    }

    function renderRow(f) {
        const subtitle = (f.certifications || []).slice(0, 2).join(" · ") || f.source || "";
        return `
        <tr>
            <td>
                <div class="fw-semibold">${escapeHtml(f.name)}
                    ${f.verified ? '<i class="bi bi-patch-check-fill text-primary ms-1" title="已验证"></i>' : ""}
                </div>
                <small class="text-muted">${escapeHtml(subtitle)}</small>
            </td>
            <td><span class="badge-soft">${escapeHtml(f.industry)}</span></td>
            <td class="text-muted" title="${escapeHtml(f.region)}">${escapeHtml(truncate(f.region, 22))}</td>
            <td><small title="${escapeHtml(scaleTitle(f))}">${escapeHtml(fmtScale(f))}</small></td>
            <td>${contactCell(f)}</td>
            <td>${productCell(f)}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-outline-primary view-detail" data-id="${f.id}">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        </tr>`;
    }

    function field(label, value) {
        return value ? `
        <div class="col-md-6">
            <div class="text-muted small">${label}</div>
            <div class="fw-semibold">${escapeHtml(value)}</div>
        </div>` : "";
    }

    function chips(label, items) {
        if (!items || !items.length) return "";
        return `<div class="col-12"><div class="text-muted small mb-1">${label}</div>
            <div>${items.map((x) => `<span class="badge-soft me-1">${escapeHtml(x)}</span>`).join("")}</div></div>`;
    }

    function renderDetail(f) {
        const rows = [];
        rows.push(field("行业", f.industry));
        rows.push(field("地址", f.region));
        rows.push(field("规模", fmtScale(f)));
        rows.push(field("规模口径", f.is_external ? f.scale_basis : ""));

        if (f.is_external) {
            rows.push(field("英文名", f.english_name));
            rows.push(field("法定代表人", f.legal_person));
            rows.push(field("成立日期", f.established));
            rows.push(field("登记状态", f.reg_status));
            rows.push(field("企业类型", f.company_org_type));
            rows.push(field("统一社会信用代码", f.credit_code));
            rows.push(field("联系电话", f.phone));
            rows.push(field("联系邮箱", f.email));
        } else {
            rows.push(field("员工规模", f.employees != null ? `${f.employees} 人` : ""));
            rows.push(field("厂房面积", f.factory_area != null ? `${f.factory_area.toLocaleString()} ㎡` : ""));
            rows.push(field("年销售额", fmtRevenue(f.annual_revenue)));
        }
        rows.push(field("数据来源", `${f.source}${f.verified ? "（已认证）" : ""}`));
        if (f.belt) rows.push(field("所在产业带", f.belt));

        rows.push(chips("可生产产品", f.main_products));
        rows.push(field("能否自营出口", f.is_external ? (f.can_export ? "经营范围含进出口资质" : "未见表述") : ""));

        if (f.business_scope) {
            rows.push(`
            <div class="col-12">
                <div class="text-muted small mb-1">经营范围（工商登记原文）</div>
                <div class="scope-text">${escapeHtml(f.business_scope)}</div>
            </div>`);
        }

        // 模拟数据专属：工艺 / 认证 / 出口市场
        rows.push(chips("加工工艺", f.processes));
        rows.push(chips("资质认证", f.certifications));
        rows.push(chips("主要出口市场", f.export_markets));

        return `<div class="row g-3">${rows.join("")}</div>`;
    }

    // 复制联系方式：事件委托挂在 document 上，页面重渲染后无需重新绑定
    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".copy-contact");
        if (!btn) return;
        const text = btn.dataset.copy || "";
        const done = () => {
            const old = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-check2"></i>';
            setTimeout(() => { btn.innerHTML = old; }, 1200);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(done).catch(() => done());
        } else {
            done();
        }
    });

    window.FactoryUI = {
        escapeHtml, truncate, fmtRevenue, fmtScale, contactCell,
        renderRow, renderDetail,
        // 表格列头统一放这里，两个页面共用一份，避免再次不一致
        HEADERS: ["工厂名称", "行业", "地址", "规模", "联系方式", "可生产产品", "操作"],
    };
})();
