const root = document.documentElement;
const shell = document.querySelector("#appShell");
const drawer = document.querySelector("#reviewDrawer");
const floatingPreview = document.querySelector("#floatingPreview");
const previewCard = document.querySelector("#openPreview");
const previewThumb = document.querySelector("#previewThumb");
const largePreview = document.querySelector("#largePreview");
const stage = document.querySelector("#previewStage");
const floatingToolbar = document.querySelector("#floatingToolbar");
const aboutOverlay = document.querySelector("#aboutOverlay");
const aboutButton = document.querySelector("#aboutButton");
const aboutDialog = document.querySelector(".aboutDialog");
const folderInput = document.querySelector("#folderInput");
const outputInput = document.querySelector("#outputInput");
const folderChooseButton = document.querySelector("#folderChooseButton");
const outputChooseButton = document.querySelector("#outputChooseButton");
const scanButton = document.querySelector("#scanButton");
const resetButton = document.querySelector("#resetButton");
const exportButton = document.querySelector("#exportButton");
const saveButton = document.querySelector("#saveButton");
const rowsEl = document.querySelector("#invoiceRows");
const toast = document.querySelector("#toast");

const editableFields = [
  "buyer_name",
  "buyer_tax",
  "seller_name",
  "seller_tax",
  "invoice_date",
  "pretax_amount",
  "tax_amount",
  "total_amount",
  "tax_rate",
  "invoice_type",
  "invoice_no",
  "category",
  "line_items",
];

const state = {
  records: [],
  folder: folderInput.value.trim(),
  selectedIndex: -1,
  busy: false,
  scanJobId: "",
  scanTimer: 0,
};

const savedTheme = localStorage.getItem("invoice-theme");
if (savedTheme) root.dataset.theme = savedTheme;

document.querySelector("#themeToggle").addEventListener("click", () => {
  const next = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  localStorage.setItem("invoice-theme", next);
});

scanButton.addEventListener("click", startScan);
resetButton.addEventListener("click", resetTask);
folderChooseButton.addEventListener("click", () => chooseFolder(folderInput));
outputChooseButton.addEventListener("click", () => chooseFolder(outputInput));
exportButton.addEventListener("click", exportReport);
saveButton.addEventListener("click", saveSelectedRecord);
document.querySelector("#closeDrawer").addEventListener("click", closeDrawer);
previewCard.addEventListener("click", openPreview);
aboutButton.addEventListener("click", openAbout);
document.querySelector("#closeAbout").addEventListener("click", closeAbout);
aboutOverlay.addEventListener("click", (event) => {
  if (event.target === aboutOverlay) closeAbout();
});
document.querySelector("#closePreview").addEventListener("pointerdown", (event) => {
  event.preventDefault();
  event.stopPropagation();
  closePreview();
});
document.querySelector("#closePreview").addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  closePreview();
});
document.querySelector("#zoomIn").addEventListener("click", () => setZoom(imageState.scale + 0.18));
document.querySelector("#zoomOut").addEventListener("click", () => setZoom(imageState.scale - 0.18));
document.querySelector("#fitImage").addEventListener("click", fitImage);
document.querySelector("#rotateImage").addEventListener("click", () => {
  imageState.rotation = (imageState.rotation + 90) % 360;
  renderImage();
});

let imageState = {
  scale: 0.62,
  rotation: 0,
  x: 0,
  y: 0,
  dragging: false,
  startX: 0,
  startY: 0,
};

let floatingState = {
  dragging: false,
  startX: 0,
  startY: 0,
  left: 314,
  top: 86,
};

renderTable();
renderStats();
if (state.folder) startScan();

async function chooseFolder(targetInput) {
  targetInput.disabled = true;
  try {
    const response = await fetch("/api/select-folder");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "无法打开文件夹选择器");
    if (data.path) {
      targetInput.value = data.path;
      if (targetInput === folderInput) state.folder = data.path;
      showToast("已选择文件夹");
    }
  } catch (error) {
    showToast(error.message || "无法打开文件夹选择器");
  } finally {
    targetInput.disabled = false;
  }
}

async function startScan() {
  const folder = folderInput.value.trim();
  if (!folder) {
    showToast("请先填写发票文件夹路径");
    return;
  }
  clearTaskState(true);
  state.folder = folder;
  setBusy(true, "准备识别...");
  updateScanProgress(0, 0, "正在准备识别");
  try {
    const response = await fetch("/api/scan/start", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({folder}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "扫描失败");
    state.scanJobId = data.job_id;
    pollScanProgress();
  } catch (error) {
    showToast(error.message || "扫描失败");
    setBusy(false);
  }
}

async function pollScanProgress() {
  if (!state.scanJobId) return;
  try {
    const response = await fetch(`/api/scan/progress?id=${encodeURIComponent(state.scanJobId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "无法读取识别进度");
    state.records = Array.isArray(data.records) ? data.records : [];
    state.selectedIndex = state.records.length ? Math.min(state.selectedIndex < 0 ? 0 : state.selectedIndex, state.records.length - 1) : -1;
    renderTable();
    renderStats();
    updateScanProgress(data.completed, data.total, data.current || (data.status === "completed" ? "识别完成" : "正在处理"));
    if (data.status === "queued" || data.status === "running") {
      state.scanTimer = window.setTimeout(pollScanProgress, 350);
      return;
    }
    if (data.status === "failed") throw new Error(data.error || "识别失败");
    setBusy(false);
    state.scanJobId = "";
    if (state.selectedIndex >= 0) openDrawer(state.selectedIndex);
    showToast(`已识别 ${state.records.length} 张发票`);
  } catch (error) {
    setBusy(false);
    state.scanJobId = "";
    showToast(error.message || "扫描失败");
  }
}

function updateScanProgress(completed, total, current) {
  const progress = document.querySelector("#scanProgress");
  progress.hidden = false;
  const ratio = total ? Math.min(100, Math.round((completed / total) * 100)) : 4;
  document.querySelector("#scanProgressBar").style.width = `${ratio}%`;
  document.querySelector("#scanProgressCount").textContent = `${completed} / ${total || "?"}`;
  document.querySelector("#scanProgressCurrent").textContent = current || "等待开始";
  document.querySelector("#scanProgressLabel").textContent = total && completed >= total ? "识别完成" : "正在识别";
}

function clearTaskState(keepFolder = true) {
  window.clearTimeout(state.scanTimer);
  state.scanTimer = 0;
  state.scanJobId = "";
  state.records = [];
  state.selectedIndex = -1;
  closeDrawer();
  renderTable();
  renderStats();
  if (!keepFolder) {
    state.folder = "";
    folderInput.value = "";
    outputInput.value = "";
  }
}

function resetTask() {
  if (state.busy && !window.confirm("识别正在进行，确定要停止当前任务并重新开始吗？")) return;
  clearTaskState(true);
  setBusy(false);
  document.querySelector("#scanProgress").hidden = true;
  showToast("已清空当前任务，可以重新开始");
}

async function exportReport() {
  if (!state.records.length) {
    showToast("没有可导出的发票");
    return;
  }
  saveSelectedRecord({ silent: true });
  setBusy(true, "导出中...");
  try {
    const response = await fetch("/api/export", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        folder: state.folder,
        output_folder: outputInput.value.trim(),
        archive_mode: selectedArchiveMode(),
        records: state.records,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "导出失败");
    if (Array.isArray(data.records)) state.records = data.records;
    renderTable();
    renderStats();
    renderDrawer();
    showToast(`已导出：${data.path}`);
  } catch (error) {
    showToast(error.message || "导出失败");
  } finally {
    setBusy(false);
  }
}

function renderTable() {
  rowsEl.innerHTML = "";
  if (!state.records.length) {
    const tr = document.createElement("tr");
    tr.className = "emptyRow";
    const td = document.createElement("td");
    td.colSpan = 15;
    td.textContent = "还没有发票数据，点击左侧开始识别";
    tr.append(td);
    rowsEl.append(tr);
    return;
  }

  state.records.forEach((record, index) => {
    const tr = document.createElement("tr");
    if (index === state.selectedIndex) tr.classList.add("selected");
    tr.addEventListener("click", () => openDrawer(index));

    tr.append(
      tableCell(record, "buyer_name"),
      tableCell(record, "buyer_tax"),
      tableCell(record, "seller_name"),
      tableCell(record, "seller_tax"),
      tableCell(record, "invoice_date"),
      amountCell(record.pretax_amount),
      amountCell(record.tax_amount),
      amountCell(record.total_amount, true),
      plainCell(record.tax_rate),
      plainCell(record.invoice_type),
      plainCell(record.invoice_no),
      plainCell(record.category || "（未分类）"),
      plainCell(archiveMonth(record)),
      fileCell(record.original_path),
      fileCell(record.archived_path)
    );
    rowsEl.append(tr);
  });
}

function renderStats() {
  const reviewCount = state.records.filter((record) => (record.fields_needing_review || []).length).length;
  const confirmed = Math.max(0, state.records.length - reviewCount);
  const total = sumAmount(state.records);
  document.querySelector("#totalFiles").textContent = state.records.length;
  document.querySelector("#confirmedFiles").textContent = confirmed;
  document.querySelector("#reviewFiles").textContent = reviewCount;
  document.querySelector("#duplicateFiles").textContent = 0;
  document.querySelector("#totalAmount").textContent = money(total);
  document.querySelector("#tableTotalLabel").textContent = `合计（共 ${state.records.length} 张）`;
  document.querySelector("#tableTotalAmount").textContent = money(total);
  document.querySelector("#summaryText").textContent = state.records.length
    ? `${state.records.length} 张 · ${reviewCount} 张待确认`
    : "未加载";
}

function renderDrawer() {
  const record = state.records[state.selectedIndex];
  if (!record) {
    document.querySelector("#drawerFileName").textContent = "选择一张发票";
    previewThumb.removeAttribute("src");
    largePreview.removeAttribute("src");
    for (const input of drawer.querySelectorAll(".fieldList input[name]")) input.value = "";
    return;
  }

  document.querySelector("#drawerFileName").textContent = record.original_name || "未命名文件";
  const fileUrl = previewUrl(record.original_path);
  previewThumb.src = fileUrl;
  largePreview.src = fileUrl;

  for (const input of drawer.querySelectorAll(".fieldList input[name]")) {
    const field = input.name;
    const needsReview = (record.fields_needing_review || []).includes(field);
    input.value = record[field] || (needsReview ? "待确认" : "");
    input.classList.toggle("reviewInput", needsReview);
  }
}

function openDrawer(index = state.selectedIndex) {
  if (Number.isInteger(index)) state.selectedIndex = index;
  shell.classList.add("drawerOpen");
  drawer.setAttribute("aria-hidden", "false");
  renderTable();
  renderDrawer();
}

function closeDrawer() {
  shell.classList.remove("drawerOpen");
  drawer.setAttribute("aria-hidden", "true");
  closePreview();
}

function saveSelectedRecord(options = {}) {
  const record = state.records[state.selectedIndex];
  if (!record) return;

  for (const input of drawer.querySelectorAll(".fieldList input[name]")) {
    const value = input.value.trim();
    record[input.name] = value === "待确认" ? "" : value;
  }

  record.fields_needing_review = (record.fields_needing_review || []).filter((field) => {
    return editableFields.includes(field) && !record[field];
  });
  for (const field of editableFields) {
    if (record[field] && record.review_reasons) delete record.review_reasons[field];
  }
  record.status = record.fields_needing_review.length ? "需人工确认" : "已确认";
  renderTable();
  renderStats();
  renderDrawer();
  if (!options.silent) showToast("已保存本行修改");
}

function tableCell(record, field) {
  const needsReview = (record.fields_needing_review || []).includes(field);
  const td = plainCell(record[field] || (needsReview ? "待确认" : ""));
  if (needsReview) td.classList.add("needsReview");
  return td;
}

function plainCell(text) {
  const td = document.createElement("td");
  td.textContent = text || "";
  return td;
}

function amountCell(value, strong = false) {
  const td = plainCell(value ? money(Number(String(value).replace(/,/g, ""))) : "");
  td.classList.add("amount");
  if (strong) td.classList.add("strong");
  return td;
}

function fileCell(path) {
  const td = document.createElement("td");
  if (!path) return td;
  const link = document.createElement("a");
  link.href = `/api/file?path=${encodeURIComponent(path)}`;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = "打开文件";
  link.addEventListener("click", (event) => event.stopPropagation());
  td.append(link);
  return td;
}

function previewUrl(path) {
  const encoded = encodeURIComponent(path);
  return path.toLowerCase().endsWith(".pdf")
    ? `/api/preview?path=${encoded}`
    : `/api/file?path=${encoded}`;
}

function archiveMonth(record) {
  if (!record.invoice_date || record.invoice_date.length < 7) return "待确认月份";
  const [year, month] = record.invoice_date.slice(0, 7).split("-");
  return `${year}年${month}月`;
}

function selectedArchiveMode() {
  return document.querySelector("input[name='archiveMode']:checked")?.value || "month";
}

function sumAmount(records) {
  return records.reduce((total, record) => {
    const value = Number(String(record.total_amount || "").replace(/,/g, ""));
    return Number.isFinite(value) ? total + value : total;
  }, 0);
}

function money(value) {
  const number = Number.isFinite(value) ? value : 0;
  return `¥${number.toLocaleString("zh-CN", {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
}

function setBusy(busy, label = "处理中...") {
  state.busy = busy;
  scanButton.disabled = busy;
  exportButton.disabled = busy || !state.records.length;
  saveButton.disabled = busy || state.selectedIndex < 0;
  resetButton.disabled = false;
  folderChooseButton.disabled = busy;
  outputChooseButton.disabled = busy;
  scanButton.innerHTML = busy
    ? `<svg><use href="#icon-play"/></svg>${label}`
    : `<svg><use href="#icon-play"/></svg>开始识别`;
}

let toastTimer = 0;
function showToast(message) {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add("show");
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3600);
}

function openPreview() {
  if (!largePreview.getAttribute("src")) return;
  floatingPreview.classList.remove("closing");
  floatingPreview.setAttribute("aria-hidden", "false");
  placeFloatingWindow();
  setPreviewOrigin();
  fitImage();
  window.requestAnimationFrame(() => {
    floatingPreview.classList.add("open");
  });
}

function closePreview() {
  if (!floatingPreview.classList.contains("open")) return;
  setPreviewOrigin();
  floatingPreview.classList.remove("open");
  floatingPreview.classList.add("closing");
  window.setTimeout(() => {
    floatingPreview.classList.remove("closing");
    floatingPreview.setAttribute("aria-hidden", "true");
  }, 230);
}

function openAbout() {
  aboutOverlay.classList.remove("closing");
  aboutOverlay.classList.add("preparing");
  aboutOverlay.setAttribute("aria-hidden", "false");
  window.requestAnimationFrame(() => {
    setAboutOrigin();
    aboutOverlay.classList.remove("preparing");
    aboutOverlay.classList.add("open");
  });
}

function closeAbout() {
  if (!aboutOverlay.classList.contains("open")) return;
  setAboutOrigin();
  aboutOverlay.classList.remove("open");
  aboutOverlay.classList.add("closing");
  window.setTimeout(() => {
    aboutOverlay.classList.remove("closing");
    aboutOverlay.setAttribute("aria-hidden", "true");
  }, 250);
}

function setZoom(value) {
  imageState.scale = Math.max(0.25, Math.min(3, value));
  renderImage();
}

function fitImage() {
  imageState.scale = 0.62;
  imageState.x = 0;
  imageState.y = 0;
  imageState.rotation = 0;
  renderImage();
}

function renderImage() {
  largePreview.style.transform = `translate(calc(-50% + ${imageState.x}px), calc(-50% + ${imageState.y}px)) rotate(${imageState.rotation}deg) scale(${imageState.scale})`;
}

stage.addEventListener("pointerdown", (event) => {
  imageState.dragging = true;
  imageState.startX = event.clientX - imageState.x;
  imageState.startY = event.clientY - imageState.y;
  stage.classList.add("dragging");
  stage.setPointerCapture(event.pointerId);
});

stage.addEventListener("pointermove", (event) => {
  if (!imageState.dragging) return;
  imageState.x = event.clientX - imageState.startX;
  imageState.y = event.clientY - imageState.startY;
  renderImage();
});

stage.addEventListener("pointerup", (event) => {
  imageState.dragging = false;
  stage.classList.remove("dragging");
  if (stage.hasPointerCapture(event.pointerId)) stage.releasePointerCapture(event.pointerId);
});

stage.addEventListener("wheel", (event) => {
  event.preventDefault();
  setZoom(imageState.scale + (event.deltaY < 0 ? 0.12 : -0.12));
}, { passive: false });

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (aboutOverlay.classList.contains("open")) {
      closeAbout();
    } else if (floatingPreview.classList.contains("open")) {
      closePreview();
    } else {
      closeDrawer();
    }
  }
});

floatingToolbar.addEventListener("pointerdown", (event) => {
  if (event.target.closest("[data-no-drag], button")) return;
  floatingState.dragging = true;
  const rect = floatingPreview.getBoundingClientRect();
  floatingState.left = rect.left;
  floatingState.top = rect.top;
  floatingState.startX = event.clientX - rect.left;
  floatingState.startY = event.clientY - rect.top;
  floatingToolbar.setPointerCapture(event.pointerId);
});

floatingToolbar.addEventListener("pointermove", (event) => {
  if (!floatingState.dragging) return;
  moveFloatingWindow(event.clientX - floatingState.startX, event.clientY - floatingState.startY);
});

floatingToolbar.addEventListener("pointerup", (event) => {
  floatingState.dragging = false;
  if (floatingToolbar.hasPointerCapture(event.pointerId)) floatingToolbar.releasePointerCapture(event.pointerId);
});

floatingToolbar.addEventListener("pointercancel", (event) => {
  floatingState.dragging = false;
  if (floatingToolbar.hasPointerCapture(event.pointerId)) floatingToolbar.releasePointerCapture(event.pointerId);
});

function placeFloatingWindow() {
  const sidebarWidth = 292;
  const drawerWidth = shell.classList.contains("drawerOpen") ? 372 : 0;
  const left = sidebarWidth + 16;
  const top = 74;
  const width = Math.max(460, window.innerWidth - sidebarWidth - drawerWidth - 32);
  const height = Math.max(360, window.innerHeight - top - 24);
  floatingPreview.style.width = `${width}px`;
  floatingPreview.style.height = `${height}px`;
  moveFloatingWindow(left, top);
}

function setPreviewOrigin() {
  const cardRect = previewCard.getBoundingClientRect();
  const previewRect = floatingPreview.getBoundingClientRect();
  const scale = Math.max(0.18, Math.min(cardRect.width / Math.max(previewRect.width, 1), cardRect.height / Math.max(previewRect.height, 1)));
  floatingPreview.style.setProperty("--preview-origin-x", `${cardRect.left - previewRect.left}px`);
  floatingPreview.style.setProperty("--preview-origin-y", `${cardRect.top - previewRect.top}px`);
  floatingPreview.style.setProperty("--preview-origin-scale", scale.toFixed(3));
}

function setAboutOrigin() {
  const buttonRect = aboutButton.getBoundingClientRect();
  const dialogRect = aboutDialog.getBoundingClientRect();
  const buttonCenterX = buttonRect.left + buttonRect.width / 2;
  const buttonCenterY = buttonRect.top + buttonRect.height / 2;
  const dialogCenterX = dialogRect.left + dialogRect.width / 2;
  const dialogCenterY = dialogRect.top + dialogRect.height / 2;
  aboutDialog.style.setProperty("--about-origin-x", `${buttonCenterX - dialogCenterX}px`);
  aboutDialog.style.setProperty("--about-origin-y", `${buttonCenterY - dialogCenterY}px`);
}

function moveFloatingWindow(left, top) {
  const rect = floatingPreview.getBoundingClientRect();
  const maxLeft = window.innerWidth - rect.width - 12;
  const maxTop = window.innerHeight - rect.height - 12;
  floatingState.left = Math.max(12, Math.min(left, maxLeft));
  floatingState.top = Math.max(12, Math.min(top, maxTop));
  floatingPreview.style.left = `${floatingState.left}px`;
  floatingPreview.style.top = `${floatingState.top}px`;
}

renderImage();
