// Cost calculator — dynamic rows, auto calculation, pie chart
let rowIndex = 0;
let costPieChart = null;
let lastPieData = null;

// 类型 → 配色槽位（固定映射，颜色跟随实体不随排序）
const TYPE_SERIES = {
    material: "series1",
    labor: "series2",
    utility: "series3",
    processing_out: "series4",
    processing_own: "series5",
    mold: "series6",
    freight: "series7",
    packaging: "series8",
    loss: "series6",
    other: "series6",
};

// 材料价格联动：name → {unit, price}
let materialMap = {};

// 模板缓存 + 保存弹窗
let templateCache = [];
let saveModal = null;
let pendingSaveName = ""; // Excel 导入后建议的模板名

// 主题切换重绘饼图 + 材料走势图
window.redrawCharts = () => {
    if (lastPieData) renderPieChart(lastPieData);
    if (calcTrendChart && calcTrendChart._data) drawCalcTrend(calcTrendChart._data);
};

let calcTrendChart = null;   // 材料价格走势折线
let trendModal = null;

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("addRowBtn").addEventListener("click", () => addRow("other"));
    document.getElementById("calcBtn").addEventListener("click", calculate);
    document.getElementById("clearBtn").addEventListener("click", clearAll);
    document.getElementById("exportBtn").addEventListener("click", exportResult);
    document.getElementById("loadTemplateBtn").addEventListener("click", loadTemplate);
    document.getElementById("saveTemplateBtn").addEventListener("click", openSaveModal);
    document.getElementById("confirmSaveBtn").addEventListener("click", saveTemplate);
    document.getElementById("deleteTemplateBtn").addEventListener("click", deleteTemplate);
    document.getElementById("importExcelBtn").addEventListener("click", () => document.getElementById("excelInput").click());
    document.getElementById("excelInput").addEventListener("change", (e) => importExcel(e.target.files[0]));

    saveModal = new bootstrap.Modal(document.getElementById("saveTemplateModal"));
    trendModal = new bootstrap.Modal(document.getElementById("calcTrendModal"));

    loadTemplates();
    loadMaterials();

    addRow("material");
    addRow("labor");
    addRow("utility");
});

function addRow(defaultType = "other", data = null) {
    const tbody = document.getElementById("costItems");
    const idx = rowIndex++;

    const typeOptions = Object.entries(ITEM_TYPES)
        .map(([k, v]) => `<option value="${k}" ${k === defaultType ? "selected" : ""}>${v}</option>`)
        .join("");

    const tr = document.createElement("tr");
    tr.id = `row-${idx}`;
    tr.innerHTML = `
        <td><select class="form-select form-select-sm item-type">${typeOptions}</select></td>
        <td><div class="d-flex align-items-center gap-1">
            <input type="text" class="form-control form-control-sm item-name flex-grow-1" placeholder="项目名称" list="materialOptions">
            <button type="button" class="btn btn-sm btn-outline-secondary mat-trend d-none"
                title="查看该材料价格走势" style="line-height:1"><i class="bi bi-graph-up"></i></button>
        </div></td>
        <td><input type="text" class="form-control form-control-sm item-unit" value="pcs"></td>
        <td><input type="number" class="form-control form-control-sm item-price" value="0" min="0" step="0.01"></td>
        <td><input type="number" class="form-control form-control-sm item-qty" value="1" min="0.01" step="0.01"></td>
        <td><span class="item-subtotal fw-semibold" style="font-variant-numeric: tabular-nums">¥0.00</span></td>
        <td><button class="btn btn-sm btn-outline-danger del-row"><i class="bi bi-x"></i></button></td>`;
    tbody.appendChild(tr);

    // 预填模板数据
    if (data) {
        tr.querySelector(".item-type").value = data.item_type || data.type || "other";
        tr.querySelector(".item-name").value = data.name || "";
        tr.querySelector(".item-unit").value = data.unit || "pcs";
        tr.querySelector(".item-price").value = data.unit_price ?? 0;
        tr.querySelector(".item-qty").value = data.quantity ?? 1;
    }

    tr.querySelector(".del-row").addEventListener("click", () => {
        tr.remove();
        updateGrandTotal();
    });
    tr.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", () => updateRowSubtotal(idx)));

    // 材料价格联动：选中材料名后自动填充单位与单价
    const nameInput = tr.querySelector(".item-name");
    const typeSelect = tr.querySelector(".item-type");
    nameInput.addEventListener("change", () => applyMaterialLink(nameInput, tr));
    typeSelect.addEventListener("change", () => applyMaterialLink(nameInput, tr));

    // 价格走势按钮：命中材料库时弹出该材料折线图
    tr.querySelector(".mat-trend").addEventListener("click", () => {
        const id = tr.dataset.matId;
        if (!id) return;
        const label = tr.dataset.matName || nameInput.value.trim();
        const unit = tr.querySelector(".item-unit").value || "pcs";
        showMaterialTrend(id, label, unit);
    });

    updateRowSubtotal(idx);
    return tr;
}

// 材料价格联动：当类型为「原材料」且名称匹配材料库时，填充单位与单价，并显示走势按钮
function applyMaterialLink(nameInput, tr) {
    const type = tr.querySelector(".item-type").value;
    const name = nameInput.value.trim();
    const trendBtn = tr.querySelector(".mat-trend");
    if (type !== "material" || !name) {
        trendBtn.classList.add("d-none");
        return;
    }
    const key = Object.keys(materialMap).find((k) => k.includes(name));
    if (!key) {
        trendBtn.classList.add("d-none");
        return;
    }
    const mat = materialMap[key];
    tr.querySelector(".item-unit").value = mat.unit;
    tr.querySelector(".item-price").value = mat.price;
    if (mat.id) {
        tr.dataset.matId = mat.id;
        tr.dataset.matName = key;
        trendBtn.classList.remove("d-none");
    }
    const idx = tr.id.split("-")[1];
    updateRowSubtotal(idx);
}

function updateRowSubtotal(idx) {
    const row = document.getElementById(`row-${idx}`);
    if (!row) return;
    const price = parseFloat(row.querySelector(".item-price").value) || 0;
    const qty = parseFloat(row.querySelector(".item-qty").value) || 0;
    row.querySelector(".item-subtotal").textContent = `¥${(price * qty).toFixed(2)}`;
    updateGrandTotal();
}

function updateGrandTotal() {
    let total = 0;
    document.querySelectorAll(".item-subtotal").forEach((el) => {
        total += parseFloat(el.textContent.replace("¥", "")) || 0;
    });
    document.getElementById("grandTotal").textContent = `¥${total.toFixed(2)}`;
}

async function calculate() {
    const items = [];
    document.querySelectorAll("#costItems tr").forEach((row) => {
        items.push({
            type: row.querySelector(".item-type").value,
            name: row.querySelector(".item-name").value || "未命名",
            unit: row.querySelector(".item-unit").value || "pcs",
            unit_price: parseFloat(row.querySelector(".item-price").value) || 0,
            quantity: parseFloat(row.querySelector(".item-qty").value) || 1,
        });
    });

    if (!items.length) return alert("请先添加成本明细");

    try {
        const res = await fetch("/api/calculator/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        document.getElementById("grandTotal").textContent = `¥${data.grand_total.toFixed(2)}`;
        renderBreakdownTable(data);
        renderPieChart(data);
    } catch (e) {
        alert(`计算失败: ${e.message}`);
    }
}

function renderBreakdownTable(data) {
    const container = document.getElementById("breakdownTable");
    container.innerHTML = `
        <table class="table table-sm align-middle">
            ${Object.entries(data.subtotals)
                .map(
                    ([k, v]) => `
                <tr>
                    <td>${k}</td>
                    <td class="text-end fw-semibold" style="font-variant-numeric: tabular-nums">¥${v.toFixed(2)}</td>
                    <td class="text-end text-muted" style="width:60px">${data.grand_total > 0 ? ((v / data.grand_total) * 100).toFixed(1) : 0}%</td>
                </tr>`
                )
                .join("")}
            <tr class="fw-bold" style="border-top: 1px solid var(--border)">
                <td>合计</td>
                <td class="text-end" style="color: var(--primary); font-variant-numeric: tabular-nums">¥${data.grand_total.toFixed(2)}</td>
                <td></td>
            </tr>
        </table>`;
}

function renderPieChart(data) {
    const container = document.getElementById("pieChartContainer");
    const canvas = document.getElementById("costPieChart");
    if (!canvas) return;

    // 从 items 聚合 type → subtotal，按固定顺序
    const byType = {};
    data.items.forEach((item) => {
        byType[item.type] = (byType[item.type] || 0) + item.subtotal;
    });

    const order = ["material", "labor", "utility", "processing_out", "processing_own", "mold", "freight", "packaging", "loss", "other"];
    const entries = order
        .filter((t) => byType[t] > 0)
        .map((t) => ({ type: t, label: ITEM_TYPES[t], value: byType[t] }));

    if (!entries.length) {
        container.style.display = "none";
        return;
    }

    const colors = window.chartColors();
    const bgColors = entries.map((e) => colors[TYPE_SERIES[e.type]]);

    lastPieData = data;
    container.style.display = "block";

    if (costPieChart) costPieChart.destroy();

    costPieChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: entries.map((e) => e.label),
            datasets: [
                {
                    data: entries.map((e) => e.value),
                    backgroundColor: bgColors,
                    borderColor: colors.surface, // 2px 表面间隙
                    borderWidth: 2,
                    hoverOffset: 4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "62%",
            plugins: {
                legend: {
                    position: "right",
                    labels: {
                        color: colors.ink,
                        usePointStyle: true,
                        pointStyle: "circle",
                        padding: 14,
                        font: { size: 12 },
                    },
                },
                tooltip: {
                    backgroundColor: colors.surface,
                    titleColor: colors.ink,
                    bodyColor: colors.ink,
                    borderColor: colors.gridline,
                    borderWidth: 1,
                    callbacks: {
                        label: (ctx) => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                            return ` ¥${ctx.parsed.toFixed(2)} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
}

// 加载材料库，供「原材料」行做价格联动（自动填充单位与单价）
async function loadMaterials() {
    try {
        const res = await fetch("/api/materials?sort=name");
        if (!res.ok) return;
        const materials = await res.json();
        const dl = document.getElementById("materialOptions");
        const seen = new Set();
        materials.forEach((m) => {
            const key = `${m.name} ${m.spec} (${m.region})`;
            if (seen.has(key)) return;
            seen.add(key);
            materialMap[key] = { unit: m.unit, price: m.current_price, id: m.id };
            const opt = document.createElement("option");
            opt.value = key;
            dl.appendChild(opt);
        });
    } catch (e) {
        console.warn("材料库加载失败", e);
    }
}

// 加载预设成本模板到下拉框（并缓存，供加载/删除使用）
async function loadTemplates() {
    try {
        const res = await fetch("/api/calculator/templates");
        if (!res.ok) return;
        templateCache = await res.json();
        const sel = document.getElementById("templateSelect");
        sel.innerHTML = '<option value="">选择模板...</option>';
        templateCache.forEach((t) => {
            const opt = document.createElement("option");
            opt.value = t.id;
            opt.textContent = t.name;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.warn("模板加载失败", e);
    }
}

// 按选中模板填充成本明细行
function loadTemplate() {
    const id = document.getElementById("templateSelect").value;
    if (!id) return alert("请先选择一个模板");
    const tpl = templateCache.find((t) => String(t.id) === id);
    if (!tpl) return alert("模板不存在");

    document.getElementById("costItems").innerHTML = "";
    rowIndex = 0;
    (tpl.items || []).forEach((item) => addRow(item.item_type, item));
}

// 收集当前表格的所有成本明细
function collectItems() {
    const items = [];
    document.querySelectorAll("#costItems tr").forEach((row) => {
        items.push({
            type: row.querySelector(".item-type").value,
            name: row.querySelector(".item-name").value || "未命名",
            unit: row.querySelector(".item-unit").value || "pcs",
            unit_price: parseFloat(row.querySelector(".item-price").value) || 0,
            quantity: parseFloat(row.querySelector(".item-qty").value) || 1,
        });
    });
    return items;
}

// 打开保存弹窗，预填名称
function openSaveModal() {
    const items = collectItems();
    if (!items.length) return alert("请先添加成本明细");
    document.getElementById("saveRowCount").textContent = items.length;
    document.getElementById("templateNameInput").value = pendingSaveName || "";
    document.getElementById("templateDescInput").value = "";
    saveModal.show();
}

// 保存当前明细为预设模板
async function saveTemplate() {
    const name = document.getElementById("templateNameInput").value.trim();
    if (!name) return alert("请填写模板名称");
    const items = collectItems();
    if (!items.length) return alert("请先添加成本明细");

    const btn = document.getElementById("confirmSaveBtn");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 保存中...';
    try {
        const res = await fetch("/api/calculator/templates", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                description: document.getElementById("templateDescInput").value.trim(),
                items,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "保存失败");

        saveModal.hide();
        pendingSaveName = "";
        await loadTemplates();
        document.getElementById("templateSelect").value = String(data.id);
        alert(`模板「${data.name}」已保存到预设模板`);
    } catch (e) {
        alert(`保存失败: ${e.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-save"></i> 保存';
    }
}

// 删除选中的模板
async function deleteTemplate() {
    const id = document.getElementById("templateSelect").value;
    if (!id) return alert("请先选择一个模板");
    const tpl = templateCache.find((t) => String(t.id) === id);
    if (!tpl) return alert("模板不存在");
    if (!confirm(`确定删除模板「${tpl.name}」吗？此操作不可恢复。`)) return;
    try {
        const res = await fetch(`/api/calculator/templates/${id}`, { method: "DELETE" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "删除失败");
        await loadTemplates();
    } catch (e) {
        alert(`删除失败: ${e.message}`);
    }
}

// 导入 Excel：上传 → 后端解析 → 填入表格 → 打开保存弹窗
async function importExcel(file) {
    if (!file) return;
    if (!/\.(xlsx|xlsm)$/i.test(file.name)) return alert("请选择 .xlsx 或 .xlsm 格式的 Excel 文件");

    const formData = new FormData();
    formData.append("file", file);

    const btn = document.getElementById("importExcelBtn");
    btn.disabled = true;
    const original = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 解析中...';
    try {
        const res = await fetch("/api/calculator/templates/import", { method: "POST", body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "导入失败");

        document.getElementById("costItems").innerHTML = "";
        rowIndex = 0;
        data.items.forEach((item) => addRow(item.type, item));
        pendingSaveName = data.suggested_name || "";
        openSaveModal();
    } catch (e) {
        alert(e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = original;
        document.getElementById("excelInput").value = "";
    }
}

function clearAll() {
    document.getElementById("costItems").innerHTML = "";
    document.getElementById("grandTotal").textContent = "¥0.00";
    document.getElementById("breakdownTable").innerHTML = '<p class="text-muted">点击"计算"查看费用构成分析</p>';
    const container = document.getElementById("pieChartContainer");
    if (container) container.style.display = "none";
    if (costPieChart) {
        costPieChart.destroy();
        costPieChart = null;
    }
    lastPieData = null;
    rowIndex = 0;
    addRow("material");
    addRow("labor");
    addRow("utility");
}

function exportResult() {
    const rows = document.querySelectorAll("#costItems tr");
    const lines = ["费用类型,项目名称,单位,单价,数量,小计"];
    rows.forEach((row) => {
        lines.push([
            row.querySelector(".item-type option:checked")?.text || "",
            row.querySelector(".item-name").value,
            row.querySelector(".item-unit").value,
            row.querySelector(".item-price").value,
            row.querySelector(".item-qty").value,
            row.querySelector(".item-subtotal").textContent,
        ].join(","));
    });
    lines.push(`合计,,,,,${document.getElementById("grandTotal").textContent}`);
    const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `成本核算_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
}

// ===== 材料价格走势同步（原材料行命中材料库后弹出折线图） =====
async function showMaterialTrend(id, name, unit) {
    document.getElementById("calcTrendTitle").textContent = `${name} · 价格走势 (${unit})`;
    trendModal.show();
    try {
        const res = await fetch(`/api/materials/${id}/history`);
        if (!res.ok) throw new Error("加载失败");
        const history = await res.json();
        history.sort((a, b) => a.recorded_date.localeCompare(b.recorded_date));
        drawCalcTrend(history);
    } catch (e) {
        alert(`走势加载失败: ${e.message}`);
    }
}

function drawCalcTrend(history) {
    const canvas = document.getElementById("calcTrendChart");
    if (!canvas || !history || !history.length) return;

    const colors = window.chartColors();
    const labels = history.map((h) => h.recorded_date);
    const values = history.map((h) => h.price);

    if (calcTrendChart) calcTrendChart.destroy();

    calcTrendChart = new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    data: values,
                    borderColor: colors.series1,
                    backgroundColor: colors.series1,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    tension: 0.3,
                    fill: true,
                    backgroundColor: (ctx) => {
                        const { ctx: c, chartArea } = ctx.chart;
                        if (!chartArea) return "transparent";
                        const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        g.addColorStop(0, colors.series1 + "55");
                        g.addColorStop(1, colors.series1 + "00");
                        return g;
                    },
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.surface,
                    titleColor: colors.ink,
                    bodyColor: colors.ink,
                    borderColor: colors.gridline,
                    borderWidth: 1,
                    callbacks: { label: (ctx) => ` ¥${ctx.parsed.y.toFixed(2)}` },
                },
            },
            scales: {
                x: {
                    ticks: { color: colors.muted, font: { size: 11 }, maxRotation: 45 },
                    grid: { display: false },
                    border: { display: false },
                },
                y: {
                    ticks: { color: colors.muted, font: { size: 11 } },
                    grid: { color: colors.gridline, drawTicks: false },
                    border: { display: false },
                },
            },
        },
    });
    calcTrendChart._data = history; // 供主题切换重绘
}
