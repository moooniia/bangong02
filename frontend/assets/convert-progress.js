/**
 * 转换类工具：按文件大小粗算耗时，驱动进度条与文案
 */
(function (global) {
  const MB = 1024 * 1024;

  function estimatePdfPages(bytes) {
    const mb = bytes / MB;
    if (mb < 0.3) return Math.max(1, Math.round(mb * 4));
    if (mb < 1.5) return Math.max(1, Math.round(mb * 3));
    return Math.max(3, Math.round(mb * 6));
  }

  function isLikelyScan(bytes) {
    const mb = bytes / MB;
    const pages = estimatePdfPages(bytes);
    return mb > 1.2 || mb / Math.max(pages, 1) > 0.35;
  }

  const TASK = {
    'pdf-to-word': (bytes) => {
      if (isLikelyScan(bytes)) {
        return Math.min(600, estimatePdfPages(bytes) * 10 + 15);
      }
      return Math.max(4, Math.round(3 + (bytes / MB) * 12));
    },
    'pdf-to-excel': (bytes) => {
      if (isLikelyScan(bytes)) {
        return Math.min(300, estimatePdfPages(bytes) * 6 + 10);
      }
      return Math.max(5, Math.round(4 + (bytes / MB) * 15));
    },
    'pdf-to-ppt': (bytes) => {
      if (isLikelyScan(bytes)) {
        return Math.min(400, estimatePdfPages(bytes) * 8 + 20);
      }
      return Math.max(6, Math.round(5 + (bytes / MB) * 18));
    },
    'office-to-pdf': (bytes) => {
      return Math.max(5, Math.min(120, Math.round(4 + (bytes / MB) * 20)));
    },
    'office-convert': (bytes, opts = {}) => {
      const target = opts.targetFormat || 'pdf';
      const name = (opts.fileName || '').toLowerCase();
      if (name.endsWith('.pdf') && target !== 'pdf') {
        const map = { docx: 'pdf-to-word', xlsx: 'pdf-to-excel', pptx: 'pdf-to-ppt' };
        const sub = map[target];
        if (sub) return TASK[sub](bytes);
      }
      if (!name.endsWith('.pdf') && target === 'pdf') return TASK['office-to-pdf'](bytes);
      return Math.max(8, Math.round(6 + (bytes / MB) * 18));
    },
    ocr: (bytes) => Math.min(600, estimatePdfPages(bytes) * 10 + 10),
    translate: (bytes) => Math.max(15, Math.min(180, Math.round(12 + (bytes / MB) * 35))),
    'pdf-to-image': (bytes) => Math.min(180, estimatePdfPages(bytes) * 2.5 + 5),
    'pdf-process': (bytes) => Math.max(3, Math.min(60, Math.round(2 + (bytes / MB) * 8))),
    'image-process': (bytes) => Math.max(2, Math.min(30, Math.round(2 + (bytes / MB) * 5))),
  };

  const VERB = {
    'pdf-to-word': '转换',
    'pdf-to-excel': '提取表格',
    'pdf-to-ppt': '转换',
    'office-to-pdf': '转换',
    'office-convert': '转换',
    ocr: '识别',
    translate: '翻译',
    'pdf-to-image': '转图片',
    'pdf-process': '处理',
    'image-process': '处理',
  };

  function estimateSeconds(task, fileSize, opts = {}) {
    const fn = TASK[task] || TASK['pdf-process'];
    return fn(fileSize, opts);
  }

  function formatEta(sec) {
    sec = Math.max(3, Math.round(sec));
    if (sec < 60) return `约 ${sec} 秒`;
    const lo = Math.floor(sec / 60);
    const hi = Math.ceil(sec / 60);
    if (lo === hi) return `约 ${lo} 分钟`;
    return `约 ${lo}～${hi} 分钟`;
  }

  function buildLabel(task, file, opts = {}) {
    const o = { ...opts, fileName: file.name };
    const sec = estimateSeconds(task, file.size, o);
    const eta = formatEta(sec);
    const verb = VERB[task] || '处理';
    if (task === 'ocr') return `正在逐页${verb}，预计 ${eta}，请勿关闭页面…`;
    if (task === 'pdf-to-word' && isLikelyScan(file.size)) {
      return `扫描件识别中，预计 ${eta}，请勿关闭页面…`;
    }
    return `正在${verb}，预计 ${eta}，请勿关闭页面…`;
  }

  function startBar(barEl, pctEl, estimatedSec) {
    let p = 0;
    const target = 88;
    const interval = 300;
    const totalMs = Math.max(estimatedSec * 1000, 4000);
    const step = target / (totalMs / interval);
    const timer = setInterval(() => {
      if (p < target) {
        p += step + Math.random() * 1.5;
        const v = Math.min(p, target);
        barEl.style.width = v + '%';
        pctEl.textContent = Math.floor(v) + '%';
      }
    }, interval);
    return {
      stop() { clearInterval(timer); },
      complete() {
        clearInterval(timer);
        barEl.style.width = '100%';
        pctEl.textContent = '100%';
      },
    };
  }

  function showProgress(labelEl, barEl, pctEl, task, file, opts = {}) {
    if (labelEl) labelEl.textContent = buildLabel(task, file, opts);
    if (barEl) barEl.style.width = '0%';
    if (pctEl) pctEl.textContent = '0%';
    if (!barEl || !pctEl) return { stop() {}, complete() {} };
    const sec = estimateSeconds(task, file.size, { ...opts, fileName: file.name });
    return startBar(barEl, pctEl, sec);
  }

  global.ConvertProgress = {
    estimateSeconds,
    formatEta,
    buildLabel,
    startBar,
    showProgress,
    isLikelyScan,
    estimatePdfPages,
  };
})(typeof window !== 'undefined' ? window : global);