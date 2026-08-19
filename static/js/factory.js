// Factory matching — search factories by product/region/scale, view detail
let factoryModal = null;
let currentFactories = [];   // 当前结果缓存，供详情弹窗直接使用（真实数据不落库）

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("searchBtn").addEventListener("click", searchFactories);
    document.getElementById("searchInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") searchFactories();
    });
    factoryModal = new bootstrap.Modal(document.getElementById("factoryModal"));

    // 支持从识图搜索联动跳转：/factory?q=<产品关键词>
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
        document.getElementById("searchInput").value = q;
        searchFactories();
    }
});

function fmtRevenue(v) {
    // 年销售额单位：万元 → 自动转「亿/万」；真实工商数据缺失则显示 —
    if (v == null) return "—";
    if (v >= 10000) return `${(v / 10000).toFixed(1)}亿`;
    return `${v}万`;
}

function fmtScale(f) {
    // 真实工商数据无员工数/厂房面积，展示注册资本；模拟数据展示员工+面积
    if (f.is_external) {
        return f.reg_capital ? `注册资本 ${f.reg_capital}` : "—";
    }
    const emp = f.employees != null ? `${f.employees}人` : "";
    const area = f.factory_area != null ? `${(f.factory_area / 10000).toFixed(1)}万㎡` : "";
    return [emp, area].filter(Boolean).join(" · ") || "—";
}

function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function truncate(s, n) {
    s = String(s ?? "");
    return s.length > n ? s.slice(0, n) + "…" : s;
}

async function searchFactories() {
    const q = document.getElementById("searchInput").value.trim();
    const region = document.getElementById("regionFilter").value;
    const industry = document.getElementById("industryFilter").value;
    const scale = document.getElementById("scaleFilter").value;
    const sort = document.getElementById("sortBy").value;

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (region) params.set("region", region);
    if (industry) params.set("industry", industry);
    if (scale) params.set("scale", scale);
    params.set("sort", sort);

    const tbody = document.getElementById("factoryTable");
    const countEl = document.getElementById("resultCount");
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div> 匹配中...</td></tr>';

    try {
        const res = await fetch(`/api/factory?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const data = await res.json();

        currentFactories = data.results || [];
        const sourceLabel = data.data_source ? ` · 数据源：${data.data_source}` : "";
        countEl.textContent = `共 ${data.total} 家工厂${sourceLabel}`;

        if (!data.total) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">未找到匹配的工厂，换个关键词试试</td></tr>';
            return;
        }

        tbody.innerHTML = data.results.map(renderFactoryRow).join("");
        tbody.querySelectorAll(".view-detail").forEach((btn) => {
            btn.addEventListener("click", () => openDetail(btn.dataset.id));
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">加载失败: ${e.message}</td></tr>`;
    }
}

function renderFactoryRow(f) {
    const matched = new Set(f.matched_products || []);

    // 可生产产品列：真实数据展示经营范围，模拟数据展示产品 badge
    let productCell;
    if (f.is_external && f.business_scope) {
        productCell = `<small class="text-muted" title="${escapeHtml(f.business_scope)}">${escapeHtml(truncate(f.business_scope, 42))}</small>`;
    } else if (f.main_products && f.main_products.length) {
        productCell = f.main_products
            .map((p) => {
                const hit = matched.has(p);
                return `<span class="badge border ${hit ? "badge-soft" : ""}" style="margin:1px">${escapeHtml(p)}${hit ? " <i class='bi bi-check2'></i>" : ""}</span>`;
            })
            .join("");
    } else {
        productCell = '<small class="text-muted">—</small>';
    }

    return `
    <tr>
        <td>
            <div class="fw-semibold">${escapeHtml(f.name)}
                ${f.verified ? '<i class="bi bi-patch-check-fill text-primary ms-1" title="已验证"></i>' : ""}
            </div>
            <small class="text-muted">${escapeHtml((f.certifications || []).slice(0, 2).join(" · ")) || escapeHtml(f.source)}</small>
        </td>
        <td><span class="badge-soft">${escapeHtml(f.industry)}</span></td>
        <td class="text-muted" title="${escapeHtml(f.region)}">${escapeHtml(truncate(f.region, 22))}</td>
        <td><small>${escapeHtml(fmtScale(f))}</small></td>
        <td><strong style="font-variant-numeric: tabular-nums">${fmtRevenue(f.annual_revenue)}</strong></td>
        <td>${productCell}</td>
        <td class="text-end">
            <button class="btn btn-sm btn-outline-primary view-detail" data-id="${f.id}">
                <i class="bi bi-eye"></i>
            </button>
        </td>
    </tr>`;
}

function openDetail(id) {
    const f = currentFactories.find((x) => String(x.id) === String(id));
    if (!f) return alert("未找到工厂详情");

    document.getElementById("factoryTitle").textContent = f.name;
    document.getElementById("factoryBody").innerHTML = renderDetail(f);
    factoryModal.show();
}

function renderDetail(f) {
    const field = (label, value) =>
        value ? `
        <div class="col-md-6">
            <div class="text-muted small">${label}</div>
            <div class="fw-semibold">${escapeHtml(value)}</div>
        </div>` : "";

    const rows = [];
    rows.push(field("行业", f.industry));
    rows.push(field("地址", f.region));

    if (f.is_external) {
        rows.push(field("注册资本", f.reg_capital));
        rows.push(field("法定代表人", f.legal_person));
        rows.push(field("成立日期", f.established));
        rows.push(field("统一社会信用代码", f.credit_code));
    } else {
        rows.push(field("员工规模", f.employees != null ? `${f.employees} 人` : ""));
        rows.push(field("厂房面积", f.factory_area != null ? `${f.factory_area.toLocaleString()} ㎡` : ""));
        rows.push(field("年销售额", fmtRevenue(f.annual_revenue)));
    }
    rows.push(field("数据来源", `${f.source}${f.verified ? "（已认证）" : ""}`));

    // 可生产什么：真实数据=经营范围，模拟数据=主营产品
    if (f.is_external && f.business_scope) {
        rows.push(`
            <div class="col-12">
                <div class="text-muted small mb-1">经营范围</div>
                <div>${escapeHtml(f.business_scope)}</div>
            </div>`);
    } else if (f.main_products && f.main_products.length) {
        rows.push(`
            <div class="col-12">
                <div class="text-muted small mb-1">可生产产品</div>
                <div>${f.main_products.map((p) => `<span class="badge-soft me-1">${escapeHtml(p)}</span>`).join("")}</div>
            </div>`);
    }

    // 模拟数据专属：工艺 / 认证 / 出口市场
    if (!f.is_external) {
        if (f.processes && f.processes.length) {
            rows.push(`<div class="col-12"><div class="text-muted small mb-1">加工工艺</div>
                <div>${f.processes.map((p) => `<span class="badge border me-1">${escapeHtml(p)}</span>`).join("")}</div></div>`);
        }
        if (f.certifications && f.certifications.length) {
            rows.push(`<div class="col-12"><div class="text-muted small mb-1">资质认证</div>
                <div>${f.certifications.map((c) => `<span class="badge-soft me-1">${escapeHtml(c)}</span>`).join("")}</div></div>`);
        }
        if (f.export_markets && f.export_markets.length) {
            rows.push(`<div class="col-12"><div class="text-muted small mb-1">主要出口市场</div>
                <div>${f.export_markets.map((m) => `<span class="badge border me-1">${escapeHtml(m)}</span>`).join("")}</div></div>`);
        }
    }

    return `<div class="row g-3">${rows.join("")}</div>`;
}
