/**
 * 通用工具页逻辑 — 行政人员只需：选文件 → 点按钮 → 下载
 */
function initToolPage(cfg) {
  let files = [];

  const $ = (id) => document.getElementById(id);
  const uploadArea = $('uploadArea');
  const fileInput = $('fileInput');
  const fileList = $('fileList');
  const convertBtn = $('convertBtn');

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

  fileInput.addEventListener('change', () => addFiles(fileInput.files));
  uploadArea.addEventListener('click', () => fileInput.click());
  uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('drag'); });
  uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag'));
  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag');
    addFiles(e.dataTransfer.files);
  });

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

    $('progressArea').style.display = 'block';
    $('errorArea').style.display = 'none';
    $('resultArea').style.display = 'none';
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
      const res = await fetch(cfg.api, { method: 'POST', body: fd });
      const data = await res.json();
      barCtrl.complete();

      if (data.success) {
        setTimeout(() => {
          $('progressArea').style.display = 'none';
          convertBtn.disabled = false;
          $('resultArea').style.display = 'block';
          const btn = $('downloadBtn');
          btn.href = '/api/download/' + data.filename;
          if (data.display_name) btn.textContent = '';
          btn.innerHTML = '<i class="ti ti-download"></i> ' + (cfg.downloadText || '下载文件');
        }, 500);
      } else {
        barCtrl.stop();
        $('progressArea').style.display = 'none';
        convertBtn.disabled = false;
        throw new Error(data.error || '处理失败');
      }
    } catch (e) {
      barCtrl.stop();
      $('progressArea').style.display = 'none';
      convertBtn.disabled = false;
      $('errorArea').style.display = 'block';
      const errEl = $('errorText');
      if (errEl) errEl.textContent = e.message || '处理失败，请换一份文件试试';
      else $('errorArea').textContent = e.message || '处理失败，请换一份文件试试';
    }
  };
}