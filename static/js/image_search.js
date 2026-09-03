// Image search — upload preview, drag & drop, search
const uploadZone = document.getElementById("uploadZone");
const fileInput = document.getElementById("fileInput");
const previewContainer = document.getElementById("previewContainer");
const previewImg = document.getElementById("previewImg");
const clearPreviewBtn = document.getElementById("clearPreview");
const searchBtn = document.getElementById("searchBtn");
const resultsContainer = document.getElementById("resultsContainer");
const searchNote = document.getElementById("searchNote");

let selectedFile = null;

// Click to select
uploadZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => handleFile(e.target.files[0]));

// Drag & drop
uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("drag-over");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("drag-over");
    handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
    if (!file) return;
    if (!file.type.startsWith("image/")) return alert("请选择图片文件");
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewContainer.style.display = "block";
        uploadZone.style.display = "none";
        searchBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

clearPreviewBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    previewContainer.style.display = "none";
    uploadZone.style.display = "block";
    searchBtn.disabled = true;
    resultsContainer.innerHTML = '<p class="text-muted text-center py-4">上传图片后点击搜索</p>';
    searchNote.textContent = "";
});

searchBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append("image", selectedFile);
    formData.append("keyword", document.getElementById("keywordInput").value.trim());

    searchBtn.disabled = true;
    searchBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 搜索中...';
    resultsContainer.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';

    try {
        const res = await fetch("/api/image-search/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        if (data.note) searchNote.textContent = data.note;

        // 联动跳转：按识别关键词匹配可生产工厂 / 查询该产品所需认证
        const kw = data.keyword || "";
        const matchBar = kw
            ? `<div class="d-flex gap-2 flex-wrap mb-3">
                 <a href="/factory?q=${encodeURIComponent(kw)}" class="btn btn-sm btn-outline-primary">
                   <i class="bi bi-buildings me-1"></i> 工厂详情页
                 </a>
                 <a href="/certification?q=${encodeURIComponent(kw)}" class="btn btn-sm btn-outline-success">
                   <i class="bi bi-patch-check me-1"></i> 查认证要求（强制 / 附加值）
                 </a>
               </div>`
            : "";

        // 识图关键词自动带入下方工厂筛选栏并触发筛选
        if (kw) {
            document.getElementById("imgFactoryQ").value = kw;
            searchImgFactories();
        }

        resultsContainer.innerHTML = matchBar + data.results
            .map(
                (r) => `
            <div class="card mb-2 supplier-card">
                <div class="card-body position-relative">
                    <span class="badge bg-primary platform-badge">${r.platform}</span>
                    <h6 class="card-title pe-5">${r.title}</h6>
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="fw-bold text-success">${r.price}</span>
                            <small class="text-muted ms-2">${r.supplier}</small>
                        </div>
                        <small class="text-muted">${r.location}</small>
                    </div>
                    <a href="${r.url}" target="_blank" class="btn btn-sm btn-outline-primary mt-2">
                        <i class="bi bi-box-arrow-up-right"></i> 查看详情
                    </a>
                </div>
            </div>`
            )
            .join("");
    } catch (e) {
        resultsContainer.innerHTML = `<p class="text-danger text-center py-4">搜索失败: ${e.message}</p>`;
    } finally {
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="bi bi-search"></i> 开始搜索';
    }
});

// ===== 嵌入式工厂筛选（复用 /api/factory 真实筛选，识图关键词自动带入） =====
let imgFactories = [];       // 当前工厂结果缓存，供详情弹窗使用
let imgFactoryModal = null;

function bindFactoryPanel() {
    if (!document.getElementById("imgFactoryQ")) return; // 非识图页则跳过
    imgFactoryModal = new bootstrap.Modal(document.getElementById("imgFactoryModal"));
    document.getElementById("imgFactoryBtn").addEventListener("click", searchImgFactories);
    document.getElementById("imgFactoryQ").addEventListener("keydown", (e) => {
        if (e.key === "Enter") searchImgFactories();
    });
    loadImgFactoryFilters();
    searchImgFactories(); // 进入页面先展示全量（本地模拟）工厂，可直接筛选
}

function populateImgSelect(id, options, placeholder) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = `<option value="">${placeholder}</option>` +
        options.map((o) => `<option value="${o}">${o}</option>`).join("");
}

async function loadImgFactoryFilters() {
    try {
        const res = await fetch("/api/factory/filters");
        if (!res.ok) return;
        const data = await res.json();
        populateImgSelect("imgFactoryRegion", data.regions, "全部地区");
        populateImgSelect("imgFactoryIndustry", data.industries, "全部行业");
        const scaleEl = document.getElementById("imgFactoryScale");
        scaleEl.innerHTML = '<option value="">不限规模</option>' +
            (data.scales || []).map((s) => `<option value="${s.value}">${s.label}</option>`).join("");
    } catch (e) {
        console.warn("工厂筛选项加载失败", e);
    }
}

async function searchImgFactories() {
    const params = new URLSearchParams();
    const q = document.getElementById("imgFactoryQ").value.trim();
    const region = document.getElementById("imgFactoryRegion").value;
    const industry = document.getElementById("imgFactoryIndustry").value;
    const scale = document.getElementById("imgFactoryScale").value;
    const sort = document.getElementById("imgFactorySort").value;
    if (q) params.set("q", q);
    if (region) params.set("region", region);
    if (industry) params.set("industry", industry);
    if (scale) params.set("scale", scale);
    params.set("sort", sort);

    const tbody = document.getElementById("imgFactoryTable");
    const countEl = document.getElementById("imgFactoryCount");
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-3"><div class="spinner-border spinner-border-sm"></div> 匹配中...</td></tr>';

    try {
        const res = await fetch(`/api/factory?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const data = await res.json();

        imgFactories = data.results || [];
        countEl.textContent = data.data_source
            ? `共 ${data.total} 家工厂 · 数据源：${data.data_source}`
            : `共 ${data.total} 家工厂`;

        if (!data.total) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">未找到匹配的工厂，换个关键词或筛选条件试试</td></tr>';
            return;
        }
        tbody.innerHTML = data.results.map(renderImgFactoryRow).join("");
        tbody.querySelectorAll(".view-detail").forEach((btn) =>
            btn.addEventListener("click", () => openImgFactoryDetail(btn.dataset.id)));
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">加载失败: ${e.message}</td></tr>`;
    }
}

function escImg(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function truncImg(s, n) {
    s = String(s ?? "");
    return s.length > n ? s.slice(0, n) + "…" : s;
}

function fmtRevenueImg(v) {
    if (v == null) return "—";
    if (v >= 10000) return `${(v / 10000).toFixed(1)}亿`;
    return `${v}万`;
}

function fmtScaleImg(f) {
    if (f.is_external) {
        return f.reg_capital ? `注册资本 ${f.reg_capital}` : "—";
    }
    const emp = f.employees != null ? `${f.employees}人` : "";
    const area = f.factory_area != null ? `${(f.factory_area / 10000).toFixed(1)}万㎡` : "";
    return [emp, area].filter(Boolean).join(" · ") || "—";
}

function renderImgFactoryRow(f) {
    const matched = new Set(f.matched_products || []);
    let productCell;
    if (f.is_external && f.business_scope) {
        productCell = `<small class="text-muted" title="${escImg(f.business_scope)}">${escImg(truncImg(f.business_scope, 42))}</small>`;
    } else if (f.main_products && f.main_products.length) {
        productCell = f.main_products
            .map((p) => {
                const hit = matched.has(p);
                return `<span class="badge border ${hit ? "badge-soft" : ""}" style="margin:1px">${escImg(p)}${hit ? " <i class='bi bi-check2'></i>" : ""}</span>`;
            })
            .join("");
    } else {
        productCell = '<small class="text-muted">—</small>';
    }

    return `
    <tr>
        <td>
            <div class="fw-semibold">${escImg(f.name)}
                ${f.verified ? '<i class="bi bi-patch-check-fill text-primary ms-1" title="已验证"></i>' : ""}
            </div>
            <small class="text-muted">${escImg((f.certifications || []).slice(0, 2).join(" · ")) || escImg(f.source)}</small>
        </td>
        <td><span class="badge-soft">${escImg(f.industry)}</span></td>
        <td class="text-muted" title="${escImg(f.region)}">${escImg(truncImg(f.region, 22))}</td>
        <td><small>${escImg(fmtScaleImg(f))}</small></td>
        <td><strong style="font-variant-numeric: tabular-nums">${fmtRevenueImg(f.annual_revenue)}</strong></td>
        <td>${productCell}</td>
        <td class="text-end">
            <button class="btn btn-sm btn-outline-primary view-detail" data-id="${f.id}">
                <i class="bi bi-eye"></i>
            </button>
        </td>
    </tr>`;
}

function openImgFactoryDetail(id) {
    const f = imgFactories.find((x) => String(x.id) === String(id));
    if (!f) return alert("未找到工厂详情");

    document.getElementById("imgFactoryTitle").textContent = f.name;
    document.getElementById("imgFactoryBody").innerHTML = renderImgFactoryDetail(f);
    imgFactoryModal.show();
}

function renderImgFactoryDetail(f) {
    const field = (label, value) =>
        value ? `
        <div class="col-md-6">
            <div class="text-muted small">${label}</div>
            <div class="fw-semibold">${escImg(value)}</div>
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
        rows.push(field("年销售额", fmtRevenueImg(f.annual_revenue)));
    }
    rows.push(field("数据来源", `${f.source}${f.verified ? "（已认证）" : ""}`));

    if (f.is_external && f.business_scope) {
        rows.push(`
            <div class="col-12">
                <div class="text-muted small mb-1">经营范围</div>
                <div>${escImg(f.business_scope)}</div>
            </div>`);
    } else if (f.main_products && f.main_products.length) {
        rows.push(`
            <div class="col-12">
                <div class="text-muted small mb-1">可生产产品</div>
                <div>${f.main_products.map((p) => `<span class="badge-soft me-1">${escImg(p)}</span>`).join("")}</div>
            </div>`);
    }

    return `<div class="row g-3">${rows.join("")}</div>`;
}

bindFactoryPanel();
