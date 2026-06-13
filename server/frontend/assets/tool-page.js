function initToolPage(cfg) {
  let files = [];

  const $  = (id) => document.getElementById(id);
  const uploadArea   = $('uploadArea');
  const fileInput    = $('fileInput');
  const fileList     = $('fileList');
  const convertBtn   = $('convertBtn');
  const progressArea = $('progressArea');
  const errorArea    = $('errorArea');
  const resultArea   = $('resultArea');

  function fmtSize(b) {
    return b < 1024 * 1024
      ? (b / 1024).toFixed(1) + ' KB'
      : (b / 1024 / 1024).toFixed(2) + ' MB';
  }

  function renderFiles() {
    if (!files.length) {
      uploadArea.style.display = 'block';
      fileList.style.display = 'none';
      convertBtn.disabled = true;
      return;
    }
    uploadArea.style.display = 'none';
    fileList.style.display = 'block';
    convertBtn.disabled = false;
    fileList.innerHTML = files.map((f, i) => `
      <div class="file-item">
        <i class="ti ti-file file-item-icon"></i>
        <div class="file-item-info">
          <div class="file-item-name">${f.name}</div>
          <div class="file-item-size">${fmtSize(f.size)}</div>
        </div>
        <button type="button" class="file-item-remove" onclick="window._removeFile(${i})"><i class="ti ti-x"></i></button>
      </div>`).join('');
  }

  function resetAll() {
    files = [];
    renderFiles();
    if (errorArea)  errorArea.style.display  = 'none';
    if (resultArea) resultArea.style.display = 'none';
    fileInput.value = '';
  }

  window._removeFile = (i) => {
    files.splice(i, 1);
    renderFiles();
  };

  function addFiles(list) {
    const arr = Array.from(list).filter((f) => {
      if (!cfg.accept) return true;
      const exts = cfg.accept.split(',').map((e) => e.trim().replace('.', '').toLowerCase());
      const ext = f.name.split('.').pop().toLowerCase();
      return exts.includes(ext);
    });
    if (!arr.length) {
      alert(cfg.acceptHint || '文件格式不对，请重新选择');
      return;
    }
    files = cfg.multiple ? files.concat(arr) : [arr[0]];
    renderFiles();
  }

  // 注入粉色选择按钮（若页面未自带）
  if (!uploadArea.querySelector('.upload-btn')) {
    const pickBtn = document.createElement('button');
    pickBtn.type = 'button';
    pickBtn.className = 'upload-btn';
    pickBtn.style.cssText = 'display:inline-flex;align-items:center;gap:8px;background:#e94c88;color:#fff;font-size:13px;font-weight:700;padding:10px 24px;border-radius:24px;border:none;cursor:pointer;font-family:inherit;margin-top:16px;';
    pickBtn.innerHTML = `<i class="ti ti-folder-open"></i>${cfg.uploadBtnText || '选择文件'}`;
    pickBtn.onmouseover = () => { pickBtn.style.background = '#d43d79'; };
    pickBtn.onmouseout  = () => { pickBtn.style.background = '#e94c88'; };
    pickBtn.onclick = (e) => { e.stopPropagation(); fileInput.click(); };
    uploadArea.appendChild(pickBtn);
  }

  fileInput.addEventListener('change', () => addFiles(fileInput.files));
  uploadArea.addEventListener('click', () => fileInput.click());
  uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('drag'); });
  uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag'));
  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag');
    addFiles(e.dataTransfer.files);
  });

  function injectAgainBtn() {
    if (!resultArea || resultArea.querySelector('.convert-again-btn')) return;
    const btn = document.createElement('button');
    btn.className = 'convert-again-btn';
    btn.style.cssText = 'margin-top:16px;display:inline-flex;align-items:center;gap:6px;background:none;border:1px solid var(--border,#ebebeb);border-radius:20px;padding:7px 16px;font-size:13px;color:#888;cursor:pointer;font-family:inherit;transition:all 0.15s;';
    btn.innerHTML = '<i class="ti ti-refresh"></i>再转一个文件';
    btn.onmouseover = () => { btn.style.borderColor = 'var(--pink,#e94c88)'; btn.style.color = 'var(--pink,#e94c88)'; };
    btn.onmouseout  = () => { btn.style.borderColor = 'var(--border,#ebebeb)'; btn.style.color = '#888'; };
    btn.onclick = resetAll;
    resultArea.appendChild(btn);
  }

  function progressOpts() {
    if (typeof cfg.progressOpts === 'function') return cfg.progressOpts(files);
    return cfg.progressOpts || {};
  }

  window.startProcess = async function () {
    if (!files.length) { alert('请先选择文件'); return; }

    const fd = new FormData();
    if (cfg.multiple) {
      files.forEach((f) => fd.append('files', f));
    } else {
      fd.append('file', files[0]);
    }
    (cfg.extraFields || []).forEach(({ id, name }) => {
      const el = $(id);
      if (el) fd.append(name, el.value);
    });

    if (progressArea) progressArea.style.display = 'block';
    if (errorArea)    errorArea.style.display    = 'none';
    if (resultArea)   resultArea.style.display   = 'none';
    convertBtn.disabled = true;

    const totalSize = files.reduce((s, f) => s + f.size, 0);
    const pseudoFile = { size: totalSize, name: files[0].name };
    let barCtrl = { stop() {}, complete() {} };
    if (cfg.progressTask && globalThis.ConvertProgress) {
      barCtrl = ConvertProgress.showProgress(
        $('progressLabel'),
        $('progressBar'),
        $('progressPct'),
        cfg.progressTask,
        pseudoFile,
        progressOpts()
      );
    }

    try {
      const res  = await fetch(cfg.api, { method: 'POST', body: fd });
      const data = await res.json();
      barCtrl.complete();

      if (data.success) {
        setTimeout(() => {
          if (progressArea) progressArea.style.display = 'none';
          convertBtn.disabled = false;
          if (resultArea) resultArea.style.display = 'block';
          const btn = $('downloadBtn');
          if (btn) {
            btn.href = '/api/download/' + data.filename;
            btn.innerHTML = '<i class="ti ti-download"></i> ' + (cfg.downloadText || '下载文件');
          }
          injectAgainBtn();
        }, 500);
      } else {
        barCtrl.stop();
        if (progressArea) progressArea.style.display = 'none';
        convertBtn.disabled = false;
        throw new Error(data.error || '转换失败');
      }
    } catch (e) {
      barCtrl.stop();
      if (progressArea) progressArea.style.display = 'none';
      convertBtn.disabled = false;
      if (errorArea) {
        errorArea.style.display = 'block';
        const errEl = $('errorText');
        if (errEl) errEl.textContent = e.message || '转换失败，请换一个文件试试';
        else errorArea.textContent = e.message || '转换失败，请换一个文件试试';
      }
    }
  };
}
