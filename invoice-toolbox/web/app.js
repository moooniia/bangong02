const state = {
  folder: "",
  records: [],
  selectedIndex: -1,
};

const fieldLabels = {
  buyer_name: "购买方抬头",
  buyer_tax: "购买方税号",
  seller_name: "销售方名称",
  seller_tax: "销售方税号",
  invoice_date: "开票日期",
  pretax_amount: "不含税金额",
  tax_amount: "税额",
  total_amount: "价税合计",
};

const rowsEl = document.querySelector("#recordRows");
const formEl = document.querySelector("#detailForm");

document.querySelector("#scanBtn").addEventListener("click", () => {
  scanFolder(document.querySelector("#folderInput").value.trim());
});

document.querySelector("#exportBtn").addEventListener("click", exportReport);
formEl.addEventListener("submit", saveSelectedRecord);

scanFolder(document.querySelector("#folderInput").value.trim());

async function scanFolder(folder) {
  const response = await fetch(`/api/scan?folder=${encodeURIComponent(folder)}`);
  const data = await response.json();
  if (!response.ok) {
    alert(data.error || "扫描失败");
    return;
  }
  state.folder = data.folder;
  state.records = data.records;
  state.selectedIndex = state.records.length ? 0 : -1;
  document.querySelector("#folderText").textContent = data.folder;
  renderTable();
  renderDetail();
}

function renderTable() {
  rowsEl.innerHTML = "";
  state.records.forEach((record, index) => {
    const tr = document.createElement("tr");
    tr.className = index === state.selectedIndex ? "active" : "";
    tr.addEventListener("click", () => {
      state.selectedIndex = index;
      renderTable();
      renderDetail();
    });

    tr.append(
      cell(record.status, record.fields_needing_review.length ? "statusReview" : ""),
      cell(record.buyer_name, reviewClass(record, "buyer_name")),
      cell(record.seller_name, reviewClass(record, "seller_name")),
      cell(record.invoice_date, reviewClass(record, "invoice_date")),
      cell(record.total_amount, reviewClass(record, "total_amount")),
      cell(reviewSummary(record), record.fields_needing_review.length ? "review" : ""),
      cell(record.original_name, "")
    );
    rowsEl.appendChild(tr);
  });

  const reviewCount = state.records.filter((record) => record.fields_needing_review.length).length;
  document.querySelector("#totalCount").textContent = `${state.records.length} 张`;
  document.querySelector("#reviewCount").textContent = `${reviewCount} 需确认`;
}

function renderDetail() {
  const record = state.records[state.selectedIndex];
  const title = document.querySelector("#detailTitle");
  const image = document.querySelector("#previewImage");
  const openFile = document.querySelector("#openFile");
  if (!record) {
    title.textContent = "选择一张发票";
    image.removeAttribute("src");
    openFile.href = "#";
    formEl.reset();
    document.querySelector("#reviewReasons").textContent = "无";
    return;
  }

  title.textContent = record.original_name;
  const fileUrl = `/api/file?path=${encodeURIComponent(record.original_path)}`;
  image.src = fileUrl;
  openFile.href = fileUrl;

  for (const input of formEl.querySelectorAll("input[name]")) {
    input.value = record[input.name] || "";
    input.classList.toggle("review", record.fields_needing_review.includes(input.name));
  }
  document.querySelector("#reviewReasons").textContent = reviewSummary(record) || "无";
}

function saveSelectedRecord(event) {
  event.preventDefault();
  const record = state.records[state.selectedIndex];
  if (!record) return;

  const data = new FormData(formEl);
  for (const [key, value] of data.entries()) {
    record[key] = String(value).trim();
  }

  for (const field of [...record.fields_needing_review]) {
    if (record[field]) {
      record.fields_needing_review = record.fields_needing_review.filter((item) => item !== field);
      delete record.review_reasons[field];
    }
  }
  record.status = record.fields_needing_review.length ? "需人工确认" : "已确认";
  document.querySelector("#savedState").textContent = "已保存本行";
  renderTable();
  renderDetail();
}

async function exportReport() {
  const response = await fetch("/api/export", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({folder: state.folder, records: state.records, archive_mode: "month"}),
  });
  const data = await response.json();
  if (!response.ok) {
    alert(data.error || "导出失败");
    return;
  }
  document.querySelector("#savedState").textContent = `已导出：${data.path}`;
  alert(`已导出：${data.path}`);
}

function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text || "";
  if (className) td.className = className;
  return td;
}

function reviewClass(record, field) {
  return record.fields_needing_review.includes(field) ? "review" : "";
}

function reviewSummary(record) {
  const parts = [];
  for (const [field, reasons] of Object.entries(record.review_reasons || {})) {
    const label = fieldLabels[field] || field;
    if (reasons.length) parts.push(`${label}: ${reasons.join("; ")}`);
  }
  return parts.join("\n");
}
