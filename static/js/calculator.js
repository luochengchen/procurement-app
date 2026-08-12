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
    other: "series6",
};

// 主题切换重绘饼图
window.redrawCharts = () => {
    if (lastPieData) renderPieChart(lastPieData);
};

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("addRowBtn").addEventListener("click", () => addRow("other"));
    document.getElementById("calcBtn").addEventListener("click", calculate);
    document.getElementById("clearBtn").addEventListener("click", clearAll);
    document.getElementById("exportBtn").addEventListener("click", exportResult);

    addRow("material");
    addRow("labor");
    addRow("utility");
});

function addRow(defaultType = "other") {
    const tbody = document.getElementById("costItems");
    const idx = rowIndex++;

    const typeOptions = Object.entries(ITEM_TYPES)
        .map(([k, v]) => `<option value="${k}" ${k === defaultType ? "selected" : ""}>${v}</option>`)
        .join("");

    const tr = document.createElement("tr");
    tr.id = `row-${idx}`;
    tr.innerHTML = `
        <td><select class="form-select form-select-sm item-type">${typeOptions}</select></td>
        <td><input type="text" class="form-control form-control-sm item-name" placeholder="项目名称"></td>
        <td><input type="text" class="form-control form-control-sm item-unit" value="pcs"></td>
        <td><input type="number" class="form-control form-control-sm item-price" value="0" min="0" step="0.01"></td>
        <td><input type="number" class="form-control form-control-sm item-qty" value="1" min="0.01" step="0.01"></td>
        <td><span class="item-subtotal fw-semibold" style="font-variant-numeric: tabular-nums">¥0.00</span></td>
        <td><button class="btn btn-sm btn-outline-danger del-row"><i class="bi bi-x"></i></button></td>`;
    tbody.appendChild(tr);

    tr.querySelector(".del-row").addEventListener("click", () => {
        tr.remove();
        updateGrandTotal();
    });
    tr.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", () => updateRowSubtotal(idx)));
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

    const order = ["material", "labor", "utility", "processing_out", "processing_own", "other"];
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
