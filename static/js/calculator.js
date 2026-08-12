// Cost calculator — dynamic rows, auto calculation

let rowIndex = 0;

// Add initial rows
document.addEventListener("DOMContentLoaded", () => {
    addRow("material");
    addRow("labor");
    addRow("utility");
});

document.getElementById("addRowBtn").addEventListener("click", () => addRow("other"));
document.getElementById("calcBtn").addEventListener("click", calculate);
document.getElementById("clearBtn").addEventListener("click", clearAll);
document.getElementById("exportBtn").addEventListener("click", exportResult);

function addRow(defaultType = "other") {
    const tbody = document.getElementById("costItems");
    const idx = rowIndex++;

    const typeOptions = Object.entries(ITEM_TYPES)
        .map(([k, v]) => `<option value="${k}" ${k === defaultType ? "selected" : ""}>${v}</option>`)
        .join("");

    const tr = document.createElement("tr");
    tr.id = `row-${idx}`;
    tr.innerHTML = `
        <td><select class="form-select form-select-sm item-type" data-row="${idx}">${typeOptions}</select></td>
        <td><input type="text" class="form-control form-control-sm item-name" placeholder="项目名称"></td>
        <td><input type="text" class="form-control form-control-sm item-unit" value="pcs"></td>
        <td><input type="number" class="form-control form-control-sm item-price" value="0" min="0" step="0.01"></td>
        <td><input type="number" class="form-control form-control-sm item-qty" value="1" min="0.01" step="0.01"></td>
        <td><span class="item-subtotal fw-semibold">¥0.00</span></td>
        <td><button class="btn btn-sm btn-outline-danger del-row" data-row="${idx}"><i class="bi bi-x"></i></button></td>`;
    tbody.appendChild(tr);

    // Bind delete
    tr.querySelector(".del-row").addEventListener("click", () => {
        tr.remove();
        updateGrandTotal();
    });

    // Auto calc on change
    tr.querySelectorAll("input").forEach((inp) => {
        inp.addEventListener("input", () => updateRowSubtotal(idx));
    });
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
    const subtotals = document.querySelectorAll(".item-subtotal");
    let total = 0;
    subtotals.forEach((el) => {
        total += parseFloat(el.textContent.replace("¥", "")) || 0;
    });
    document.getElementById("grandTotal").textContent = `¥${total.toFixed(2)}`;
}

async function calculate() {
    const rows = document.querySelectorAll("#costItems tr");
    const items = [];
    rows.forEach((row) => {
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

        // Breakdown
        const breakdown = document.getElementById("breakdown");
        breakdown.innerHTML = `
            <table class="table table-sm">
                ${Object.entries(data.subtotals)
                    .map(
                        ([k, v]) => `
                    <tr>
                        <td>${k}</td>
                        <td class="text-end fw-semibold">¥${v.toFixed(2)}</td>
                        <td class="text-end text-muted">${data.grand_total > 0 ? ((v / data.grand_total) * 100).toFixed(1) : 0}%</td>
                    </tr>`
                    )
                    .join("")}
                <tr class="table-primary fw-bold">
                    <td>合计</td>
                    <td class="text-end">¥${data.grand_total.toFixed(2)}</td>
                    <td></td>
                </tr>
            </table>`;
    } catch (e) {
        alert(`计算失败: ${e.message}`);
    }
}

function clearAll() {
    document.getElementById("costItems").innerHTML = "";
    document.getElementById("grandTotal").textContent = "¥0.00";
    document.getElementById("breakdown").innerHTML = '<p class="text-muted">点击"计算"查看费用构成分析</p>';
    rowIndex = 0;
    addRow("material");
    addRow("labor");
    addRow("utility");
}

function exportResult() {
    const rows = document.querySelectorAll("#costItems tr");
    const lines = ["费用类型,项目名称,单位,单价,数量,小计"];
    rows.forEach((row) => {
        const cells = [
            row.querySelector(".item-type option:checked")?.text || "",
            row.querySelector(".item-name").value,
            row.querySelector(".item-unit").value,
            row.querySelector(".item-price").value,
            row.querySelector(".item-qty").value,
            row.querySelector(".item-subtotal").textContent,
        ];
        lines.push(cells.join(","));
    });
    lines.push(`合计,,,,,${document.getElementById("grandTotal").textContent}`);
    const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `成本核算_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
}
