const bridge = window.AstrBotPluginPage;
bridge.pluginName = 'astrbot_plugin_setu_webui';

const fetchBtn = document.getElementById('fetchBtn');
const randomBtn = document.getElementById('randomBtn');
const sendBtn = document.getElementById('sendBtn');
const grid = document.getElementById('setuGrid');
const groupGrid = document.getElementById('groupGrid');
const resultToast = document.getElementById('resultToast');
const resultIcon = document.getElementById('resultIcon');
const resultMessage = document.getElementById('resultMessage');
const progressBar = document.getElementById('progressBar');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultsHeader = document.getElementById('resultsHeader');
const resultsCount = document.getElementById('resultsCount');
const sendPanel = document.getElementById('sendPanel');
const selectedCount = document.getElementById('selectedCount');
const selectAllGroups = document.getElementById('selectAllGroups');
const loadingState = document.getElementById('loadingState');

const uapiCatSelect = document.getElementById('uapiCategory');
const uapiTypeSelect = document.getElementById('uapiType');

const modeSlider = document.getElementById('modeSlider');
const modeBtns = document.querySelectorAll('.mode-option');
const quickSection = document.getElementById('quickSection');
const blocksSection = document.getElementById('blocksSection');
const logsSection = document.getElementById('logsSection');

const saveConfigBtn = document.getElementById('saveConfigBtn');
const deleteConfigBtn = document.getElementById('deleteConfigBtn');
const configSelect = document.getElementById('configSelect');
const configName = document.getElementById('configName');

const cmdName = document.getElementById('cmdName');
const availablePresets = document.getElementById('availablePresets');
const addStepBtn = document.getElementById('addStepBtn');
const stepList = document.getElementById('stepList');
const saveCmdBtn = document.getElementById('saveCmdBtn');
const deleteCmdBtn = document.getElementById('deleteCmdBtn');
const cmdSelect = document.getElementById('cmdSelect');

const logsList = document.getElementById('logsList');
const logsCount = document.getElementById('logsCount');
const logsPage = document.getElementById('logsPage');
const logsPrevBtn = document.getElementById('logsPrevBtn');
const logsNextBtn = document.getElementById('logsNextBtn');
const refreshLogsBtn = document.getElementById('refreshLogsBtn');

const logDetailModal = document.getElementById('logDetailModal');
const logCopyBtn = document.getElementById('logCopyBtn');
const logDetailClose = document.getElementById('logDetailClose');
const detailTime = document.getElementById('detailTime');
const detailUser = document.getElementById('detailUser');
const detailGroup = document.getElementById('detailGroup');
const detailSource = document.getElementById('detailSource');
const detailTag = document.getElementById('detailTag');
const detailResult = document.getElementById('detailResult');
const detailPrompt = document.getElementById('detailPrompt');
const detailDetail = document.getElementById('detailDetail');
const detailApi = document.getElementById('detailApi');
const detailRaw = document.getElementById('detailRaw');

const imgViewerModal = document.getElementById('imgViewerModal');
const imgViewerClose = document.getElementById('imgViewerClose');
const imgViewerImg = document.getElementById('imgViewerImg');
const imgViewerStage = document.getElementById('imgViewerStage');
const imgViewerTitle = document.getElementById('imgViewerTitle');
const imgViewerToast = document.getElementById('imgViewerToast');
const imgViewerZoom = document.getElementById('imgViewerZoom');
const imgViewerZoomIn = document.getElementById('imgViewerZoomIn');
const imgViewerZoomOut = document.getElementById('imgViewerZoomOut');
const imgViewerFit = document.getElementById('imgViewerFit');
const imgViewerCopy = document.getElementById('imgViewerCopy');

// 统一加载图标（line-md 双圈，自带旋转动画）
const LOADING_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M0 0h24v24H0z" fill="none" />
  <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2">
    <path stroke-dasharray="18" d="M12 3c4.97 0 9 4.03 9 9">
      <animate fill="freeze" attributeName="stroke-dashoffset" dur="0.3s" values="18;0" />
      <animateTransform attributeName="transform" dur="1.5s" repeatCount="indefinite" type="rotate" values="0 12 12;360 12 12" />
    </path>
    <path stroke-dasharray="60" d="M12 3c4.97 0 9 4.03 9 9c0 4.97 -4.03 9 -9 9c-4.97 0 -9 -4.03 -9 -9c0 -4.97 4.03 -9 9 -9Z" opacity=".3">
      <animate fill="freeze" attributeName="stroke-dashoffset" dur="1.2s" values="60;0" />
    </path>
  </g>
</svg>`;

const SOURCE_NAMES = {
  lolicon: 'Lolicon（Pixiv 插画）',
  uapipro: 'UApiPro（多分类壁纸）',
  bing: 'Bing（每日壁纸）',
  imgapi: 'imgapi（随机壁纸）',
  dmoe: 'dmoe（二次元）',
  loliapi: 'LoliAPI（多分类二次元）',
  alcy: '栗次元（多分类）',
};

let allImages = [];
let selectedImages = new Set();
let allGroups = [];
let selectedGroups = new Set();
let timer = null;
let currentSteps = [];
let editingCmdName = '';
let currentLogPage = 1;
let totalLogs = 0;
let lastFetch = { source: 'lolicon', params: {} };
let currentLog = null;

function escHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// Toast：带退出动画，可选自定义图标（Material Icons 代替 emoji）
function toast(msg, type, icon) {
  const map = { success: 'check_circle', error: 'error', info: 'info' };
  resultIcon.textContent = icon || map[type] || 'info';
  resultMessage.textContent = msg;
  resultToast.className = `result-toast ${type}`;
  resultToast.classList.remove('hidden');
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    resultToast.classList.add('toast-out');
    setTimeout(() => {
      resultToast.classList.add('hidden');
      resultToast.classList.remove('toast-out');
    }, 220);
  }, 2000);
}

// ─── 模式切换（滑动胶囊） ───────────────────────

modeBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.mode;
    modeSlider.className = `mode-slider-container active-${mode}`;
    quickSection.classList.toggle('hidden', mode !== 'quick');
    blocksSection.classList.toggle('hidden', mode !== 'blocks');
    logsSection.classList.toggle('hidden', mode !== 'logs');
    if (mode === 'blocks') {
      refreshAvailablePresets();
      refreshCmdList();
    }
    if (mode === 'logs') {
      loadLogs();
    }
  });
});

// ─── 源切换 ───────────────────────

function updateUapiTypes() {
  const cat = uapiCatSelect.value;
  const options = uapiTypeSelect.querySelectorAll('option');
  let found = false;
  for (const opt of options) {
    if (opt.dataset.cat === '*' || opt.dataset.cat === cat) {
      opt.style.display = '';
      if (!found) { opt.selected = true; found = true; }
    } else {
      opt.style.display = 'none';
    }
  }
}

uapiCatSelect.addEventListener('change', updateUapiTypes);

function toggleSource() {
  const v = document.querySelector('input[name="source"]:checked').value;
  let shown = null;
  document.querySelectorAll('.source-group').forEach(g => {
    const show = g.classList.contains('source-' + v);
    g.classList.toggle('hidden', !show);
    if (show) shown = g;
  });
  if (shown) {
    shown.classList.remove('anim-in');
    void shown.offsetWidth;
    shown.classList.add('anim-in');
  }

  const inp = document.getElementById('setuNum');
  if (v === 'bing') { inp.max = 8; if (parseInt(inp.value) > 8) inp.value = 8;
    document.getElementById('numHint').textContent = '最多 8 张'; }
  else if (v === 'uapipro' || v === 'imgapi' || v === 'dmoe' || v === 'loliapi' || v === 'alcy') { inp.max = 10; if (parseInt(inp.value) > 10) inp.value = 10;
    document.getElementById('numHint').textContent = '最多 10 张'; }
  else { inp.max = 20;
    document.getElementById('numHint').textContent = '最多 20 张'; }

  if (v === 'uapipro') updateUapiTypes();
}

document.querySelectorAll('input[name="source"]').forEach(r => r.addEventListener('change', toggleSource));

// ─── 获取图片（按钮变加载圈） ─────────────────────

function setFetchLoading(loading) {
  fetchBtn.disabled = loading;
  randomBtn.disabled = loading;
  fetchBtn.classList.toggle('loading', loading);
  fetchBtn.innerHTML = loading
    ? `<span style="display:inline-flex;font-size:20px;">${LOADING_SVG}</span> 正在获取...`
    : '<span class="material-icons">search</span> 获取';
  randomBtn.innerHTML = loading
    ? `<span style="display:inline-flex;font-size:20px;">${LOADING_SVG}</span> 随机中...`
    : '<span class="material-icons">casino</span> 全随机';
}

fetchBtn.addEventListener('click', async () => {
  const source = document.querySelector('input[name="source"]:checked').value;
  const r18 = parseInt(document.querySelector('input[name="r18"]:checked')?.value || 0);
  const num = parseInt(document.getElementById('setuNum').value) || 3;
  const tagRaw = document.getElementById('tagInput')?.value.trim() || '';
  const tag = tagRaw ? tagRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
  const keyword = document.getElementById('keywordInput')?.value.trim() || '';
  const uid = document.getElementById('uidInput')?.value.trim();
  const excludeAI = document.getElementById('excludeAI')?.checked || false;
  const dsc = document.getElementById('dsc')?.checked || false;
  const proxy = document.getElementById('proxyInput')?.value.trim() || '';
  const aspectRatio = document.getElementById('aspectRatioInput')?.value.trim() || '';
  const sizeCheckboxes = document.querySelectorAll('input[name="size"]:checked');
  const size = Array.from(sizeCheckboxes).map(cb => cb.value);
  const uapiCategory = uapiCatSelect?.value || 'acg';
  const uapiType = uapiTypeSelect?.value || '';
  const alcyCategory = document.getElementById('alcyCategory')?.value || 'random';
  const alcyCompress = document.getElementById('alcyCompress')?.value || '800';
  const bingSource = document.querySelector('input[name="bingSource"]:checked')?.value || 'uapi';
  const imgapiZd = document.getElementById('imgapiZd')?.value || '';
  const imgapiFl = document.getElementById('imgapiFl')?.value || '';
  const loliapiCategory = document.getElementById('loliapiCategory')?.value || 'random';

  const params = { source, r18, num, tag, keyword, excludeAI, dsc, proxy, aspectRatio, size, uapiCategory, uapiType, alcyCategory, alcyCompress, bingSource, imgapiZd, imgapiFl, loliapiCategory };
  if (uid) params.uid = uid.split(',').map(s => parseInt(s.trim())).filter(Boolean);

  lastFetch = { source, params };

  setFetchLoading(true);

  try {
    const r = await bridge.apiPost('fetch', params);

    allImages = (r && r.images) || [];
    selectedImages = new Set(allImages.map((_, i) => i));
    renderGrid();

    if (allImages.length > 0) {
      resultsHeader.classList.remove('hidden');
      resultsCount.textContent = allImages.length + ' 张';
      sendPanel.classList.remove('hidden');
      loadGroups();
    } else {
      resultsHeader.classList.add('hidden');
      sendPanel.classList.add('hidden');
      toast('没有找到图片', 'info');
    }
  } catch (e) {
    toast('失败: ' + e.message, 'error');
    resultsHeader.classList.add('hidden');
    sendPanel.classList.add('hidden');
    allImages = [];
    selectedImages = new Set();
    grid.classList.add('hidden');
  } finally {
    setFetchLoading(false);
  }
});

// 全随机：走后端 random=true（服务端 50 选 1，每张独立，图片自带指令）
randomBtn.addEventListener('click', async () => {
  const num = parseInt(document.getElementById('setuNum').value) || 3;
  lastFetch = { source: 'random', params: { random: true, num } };
  setFetchLoading(true);
  try {
    const r = await bridge.apiPost('fetch', { random: true, num });
    allImages = (r && r.images) || [];
    selectedImages = new Set(allImages.map((_, i) => i));
    renderGrid();

    if (allImages.length > 0) {
      resultsHeader.classList.remove('hidden');
      resultsCount.textContent = allImages.length + ' 张';
      sendPanel.classList.remove('hidden');
      loadGroups();
      toast('全随机成功，每张图已附带指令', 'success', 'casino');
    } else {
      resultsHeader.classList.add('hidden');
      sendPanel.classList.add('hidden');
      toast('没有找到图片', 'info');
    }
  } catch (e) {
    toast('全随机失败: ' + e.message, 'error');
    resultsHeader.classList.add('hidden');
    sendPanel.classList.add('hidden');
    allImages = [];
    selectedImages = new Set();
    grid.classList.add('hidden');
  } finally {
    setFetchLoading(false);
  }
});

// 结果网格：每张卡片错峰入场
function renderGrid() {
  if (allImages.length === 0) {
    grid.classList.add('hidden');
    grid.innerHTML = '';
    return;
  }
  grid.classList.remove('hidden');
  let h = '';
  allImages.forEach((img, i) => {
    const c = selectedImages.has(i) ? 'checked' : '';
    const delay = Math.min(i * 60, 360);
    h += `<div class="setu-card ${c ? 'selected' : ''}" data-i="${i}" style="animation:fadeUp .4s cubic-bezier(.22,1,.36,1) both;animation-delay:${delay}ms;">
      <div class="setu-img-wrap">
        <img class="setu-img" src="${img.thumb || img.url}" alt="" loading="lazy"
             referrerpolicy="no-referrer"
             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%23e5e7eb%22 width=%22200%22 height=%22200%22/%3E%3Ctext x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%239ca3af%22 font-size=%2214%22%3E%E5%8A%A0%E8%BD%BD%E5%A4%B1%E8%B4%A5%3C/text%3E%3C/svg%3E'" />
        <div class="setu-overlay">
          <input type="checkbox" class="setu-checkbox" ${c} />
        </div>
      </div>
      <div class="setu-info">
        <div class="setu-info-main">
          <div class="setu-title">${img.title || '无题'}</div>
          <div class="setu-meta">${img.author || ''}</div>
        </div>
        <div class="setu-actions">
          <button class="setu-detail-btn" data-i="${i}" data-act="view" title="查看大图" type="button"><span class="material-icons">open_in_full</span></button>
          <button class="setu-detail-btn" data-i="${i}" title="详细信息" type="button"><span class="material-icons">info</span></button>
        </div>
      </div>
    </div>`;
  });
  grid.innerHTML = h;
  grid.querySelectorAll('.setu-card').forEach(card => {
    card.addEventListener('click', function(e) {
      if (e.target.closest('.setu-checkbox')) return;
      if (e.target.closest('.setu-detail-btn')) return;
      const cb = this.querySelector('.setu-checkbox');
      cb.checked = !cb.checked;
      cb.dispatchEvent(new Event('change', { bubbles: true }));
    });
  });
  grid.querySelectorAll('.setu-checkbox').forEach(cb => {
    cb.addEventListener('change', function() {
      const i = parseInt(this.closest('.setu-card').dataset.i);
      if (this.checked) selectedImages.add(i);
      else selectedImages.delete(i);
      this.closest('.setu-card').classList.toggle('selected', this.checked);
      updateBtn();
    });
  });
  grid.querySelectorAll('.setu-detail-btn[data-act="view"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openImgViewer(allImages[parseInt(btn.dataset.i)]);
    });
  });
  grid.querySelectorAll('.setu-detail-btn:not([data-act="view"])').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      showImgLog(allImages[parseInt(btn.dataset.i)]);
    });
  });
  updateBtn();
}

// ─── 群组 ─────────────────────────

async function loadGroups() {
  loadingState.classList.remove('hidden');
  try {
    const r = await bridge.apiGet('groups', {});
    allGroups = (r && r.groups) || [];
    if (allGroups.length === 0) {
      groupGrid.innerHTML = '<div class="empty-row">没有群</div>';
      loadingState.classList.add('hidden');
      return;
    }
    renderGroups();
    loadingState.classList.add('hidden');
  } catch (e) {
    groupGrid.innerHTML = '<div class="empty-row">加载失败</div>';
    loadingState.classList.add('hidden');
  }
}

// 群列表：错峰入场
function renderGroups() {
  if (allGroups.length === 0) { groupGrid.innerHTML = '<div class="empty-row">暂无群</div>'; return; }
  let h = '';
  allGroups.forEach((g, i) => {
    const id = String(g.id);
    const c = selectedGroups.has(id) ? 'checked' : '';
    const delay = Math.min(i * 30, 240);
    h += `<div class="group-card ${c ? 'selected' : ''}" data-id="${id}" style="animation:fadeUp .35s cubic-bezier(.22,1,.36,1) both;animation-delay:${delay}ms;">
      <input type="checkbox" class="group-checkbox" ${c} />
      <div class="group-avatar">${(g.name || 'G')[0]}</div>
      <div class="group-info">
        <div class="group-name">${g.name || '未知'}</div>
        <div class="group-meta">${id}</div>
      </div>
    </div>`;
  });
  groupGrid.innerHTML = h;
  groupGrid.querySelectorAll('.group-card').forEach(card => {
    card.addEventListener('click', function(e) {
      if (e.target.classList.contains('group-checkbox')) return;
      const cb = this.querySelector('.group-checkbox');
      cb.checked = !cb.checked;
      cb.dispatchEvent(new Event('change', { bubbles: true }));
    });
  });
  groupGrid.querySelectorAll('.group-checkbox').forEach(cb => {
    cb.addEventListener('change', function() {
      const id = this.closest('.group-card').dataset.id;
      if (this.checked) selectedGroups.add(id);
      else selectedGroups.delete(id);
      this.closest('.group-card').classList.toggle('selected', this.checked);
      updateBtn();
    });
  });
  updateBtn();
}

selectAllGroups.addEventListener('change', function() {
  if (this.checked) selectedGroups = new Set(allGroups.map(g => String(g.id)));
  else selectedGroups = new Set();
  renderGroups();
});

function updateBtn() {
  const img = selectedImages.size;
  const grp = selectedGroups.size;
  sendBtn.disabled = img === 0 || grp === 0;
  selectedCount.textContent = `已选 ${grp} 个群 · ${img} 张图`;
}

sendBtn.addEventListener('click', async () => {
  if (selectedGroups.size === 0 || selectedImages.size === 0) return;
  const list = [];
  for (const i of selectedImages) {
    const img = allImages[i];
    list.push({ url: img.url, title: img.title, author: img.author, pid: img.pid, command: img.command || '' });
  }
  sendBtn.disabled = true;
  progressBar.classList.remove('hidden');
  progressFill.style.width = '0%';
  progressText.textContent = '发送中...';
  try {
    const r = await bridge.apiPost('send', { group_ids: Array.from(selectedGroups), images: list });
    progressFill.style.width = '100%';
    progressText.textContent = '完成';
    if (r && r.ok > 0) toast(`发送完成：成功 ${r.ok} 个群` + (r.fail > 0 ? `，失败 ${r.fail} 个` : ''), r.fail > 0 ? 'info' : 'success');
    else toast('发送失败', 'error');
  } catch (e) {
    toast('失败: ' + e.message, 'error');
  } finally {
    sendBtn.disabled = false;
    setTimeout(() => progressBar.classList.add('hidden'), 500);
  }
});

// ─── 配置预设 ────────────────────────────

function getCurrentConfig() {
  return {
    source: document.querySelector('input[name="source"]:checked').value,
    r18: parseInt(document.querySelector('input[name="r18"]:checked')?.value || 0),
    tag: document.getElementById('tagInput')?.value.trim() || '',
    keyword: document.getElementById('keywordInput')?.value.trim() || '',
    uid: document.getElementById('uidInput')?.value.trim() || '',
    excludeAI: document.getElementById('excludeAI')?.checked || false,
    dsc: document.getElementById('dsc')?.checked || false,
    proxy: document.getElementById('proxyInput')?.value.trim() || '',
    aspectRatio: document.getElementById('aspectRatioInput')?.value.trim() || '',
    size: Array.from(document.querySelectorAll('input[name="size"]:checked')).map(cb => cb.value),
    uapiCategory: uapiCatSelect?.value || 'acg',
    uapiType: uapiTypeSelect?.value || '',
    alcyCategory: document.getElementById('alcyCategory')?.value || 'random',
    alcyCompress: document.getElementById('alcyCompress')?.value || '800',
    bingSource: document.querySelector('input[name="bingSource"]:checked')?.value || 'uapi',
    imgapiZd: document.getElementById('imgapiZd')?.value || '',
    imgapiFl: document.getElementById('imgapiFl')?.value || '',
    loliapiCategory: document.getElementById('loliapiCategory')?.value || 'random',
  };
}

async function saveConfig() {
  const name = configName.value.trim();
  if (!name) { toast('请输入配置名', 'error'); return; }
  try {
    await bridge.apiPost('save_config', { name, config: getCurrentConfig() });
    toast(`已保存配置「${name}」`, 'success');
    configName.value = '';
    refreshConfigList();
    refreshAvailablePresets();
  } catch (e) {
    toast(`保存失败: ${e.message}`, 'error');
  }
}

async function deleteConfig() {
  const name = configSelect.value;
  if (!name) return;
  try {
    await bridge.apiPost('delete_config', { name });
    toast(`已删除配置「${name}」`, 'info');
    refreshConfigList();
    refreshAvailablePresets();
  } catch (e) {
    toast(`删除失败: ${e.message}`, 'error');
  }
}

async function loadConfig() {
  const name = configSelect.value;
  if (!name) return;
  try {
    const r = await bridge.apiGet('get_config', { name });
    const c = r.config;
    const srcRadio = document.querySelector(`input[name="source"][value="${c.source}"]`);
    if (srcRadio) { srcRadio.checked = true; srcRadio.dispatchEvent(new Event('change')); }
    const r18Radio = document.querySelector(`input[name="r18"][value="${c.r18}"]`);
    if (r18Radio) r18Radio.checked = true;
    document.getElementById('tagInput').value = c.tag || '';
    document.getElementById('keywordInput').value = c.keyword || '';
    document.getElementById('uidInput').value = c.uid || '';
    document.getElementById('excludeAI').checked = c.excludeAI || false;
    document.getElementById('dsc').checked = c.dsc || false;
    document.getElementById('proxyInput').value = c.proxy || '';
    document.getElementById('aspectRatioInput').value = c.aspectRatio || '';
    document.querySelectorAll('input[name="size"]').forEach(cb => {
      cb.checked = (c.size || ['original']).includes(cb.value);
    });
    if (c.uapiCategory) uapiCatSelect.value = c.uapiCategory;
    if (c.uapiType) uapiTypeSelect.value = c.uapiType;
    if (c.alcyCategory) document.getElementById('alcyCategory').value = c.alcyCategory;
    if (c.alcyCompress) document.getElementById('alcyCompress').value = c.alcyCompress;
    const bingRadio = document.querySelector(`input[name="bingSource"][value="${c.bingSource}"]`);
    if (bingRadio) bingRadio.checked = true;
    if (c.imgapiZd) document.getElementById('imgapiZd').value = c.imgapiZd;
    if (c.imgapiFl) document.getElementById('imgapiFl').value = c.imgapiFl;
    if (c.loliapiCategory) document.getElementById('loliapiCategory').value = c.loliapiCategory;
    toast(`已加载配置「${name}」`, 'info');
  } catch (e) {
    toast(`加载失败: ${e.message}`, 'error');
  }
}

async function refreshConfigList() {
  try {
    const r = await bridge.apiGet('list_configs', {});
    const names = r.names || [];
    configSelect.innerHTML = '<option value="">加载已有配置...</option>';
    names.forEach(n => {
      const opt = document.createElement('option');
      opt.value = n; opt.textContent = n;
      configSelect.appendChild(opt);
    });
  } catch (e) {
    console.error('refresh config list failed:', e);
  }
}

// ─── 指令编辑 ────────────────────────────

// 步骤列表：错峰入场
function renderSteps() {
  if (currentSteps.length === 0) {
    stepList.innerHTML = '<div class="empty-row">暂无步骤，请添加</div>';
    return;
  }
  let h = '';
  currentSteps.forEach((step, i) => {
    const delay = Math.min(i * 40, 200);
    h += `<div class="step-item" style="animation:fadeUp .3s cubic-bezier(.22,1,.36,1) both;animation-delay:${delay}ms;">
      <div class="step-index">${i + 1}</div>
      <div class="step-name">${step}</div>
      <button class="step-btn" data-action="move-up" data-idx="${i}" ${i === 0 ? 'disabled' : ''}><span class="material-icons">arrow_upward</span></button>
      <button class="step-btn" data-action="move-down" data-idx="${i}" ${i === currentSteps.length - 1 ? 'disabled' : ''}><span class="material-icons">arrow_downward</span></button>
      <button class="step-btn danger" data-action="remove" data-idx="${i}"><span class="material-icons">close</span></button>
    </div>`;
  });
  stepList.innerHTML = h;
  stepList.querySelectorAll('[data-action="move-up"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const i = parseInt(btn.dataset.idx);
      if (i > 0) { [currentSteps[i - 1], currentSteps[i]] = [currentSteps[i], currentSteps[i - 1]]; renderSteps(); }
    });
  });
  stepList.querySelectorAll('[data-action="move-down"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const i = parseInt(btn.dataset.idx);
      if (i < currentSteps.length - 1) { [currentSteps[i], currentSteps[i + 1]] = [currentSteps[i + 1], currentSteps[i]]; renderSteps(); }
    });
  });
  stepList.querySelectorAll('[data-action="remove"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const i = parseInt(btn.dataset.idx);
      currentSteps.splice(i, 1);
      renderSteps();
    });
  });
}

async function refreshAvailablePresets() {
  try {
    const r = await bridge.apiGet('list_configs', {});
    const names = r.names || [];
    availablePresets.innerHTML = '<option value="">-- 选择配置预设 --</option>';
    names.forEach(n => {
      const opt = document.createElement('option');
      opt.value = n; opt.textContent = n;
      availablePresets.appendChild(opt);
    });
  } catch (e) {
    console.error('refresh presets failed:', e);
  }
}

async function refreshCmdList() {
  try {
    const r = await bridge.apiGet('list_commands', {});
    const cmds = r.commands || [];
    cmdSelect.innerHTML = '<option value="">选择指令编辑...</option>';
    cmds.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.name; opt.textContent = c.name;
      cmdSelect.appendChild(opt);
    });
  } catch (e) {
    console.error('refresh cmds failed:', e);
  }
}

addStepBtn.addEventListener('click', () => {
  const preset = availablePresets.value;
  if (!preset) { toast('请选择一个配置预设', 'error'); return; }
  currentSteps.push(preset);
  renderSteps();
  availablePresets.value = '';
});

saveCmdBtn.addEventListener('click', async () => {
  const name = cmdName.value.trim();
  if (!name) { toast('请输入指令名', 'error'); return; }
  if (currentSteps.length === 0) { toast('请至少添加一个步骤', 'error'); return; }
  const mode = document.querySelector('input[name="cmdMode"]:checked')?.value || 'random';
  try {
    await bridge.apiPost('save_command', { name, presets: currentSteps, mode });
    toast(`已保存指令「${name}」`, 'success');
    cmdName.value = '';
    cmdName.readOnly = false;
    currentSteps = [];
    renderSteps();
    editingCmdName = '';
    refreshCmdList();
  } catch (e) {
    toast(`保存失败: ${e.message}`, 'error');
  }
});

cmdSelect.addEventListener('change', async () => {
  const name = cmdSelect.value;
  if (!name) return;
  try {
    const r = await bridge.apiGet('get_command', { name });
    const cmd = r.command;
    cmdName.value = cmd.name;
    cmdName.readOnly = true;
    currentSteps = cmd.presets || [];
    renderSteps();
    const modeRadio = document.querySelector(`input[name="cmdMode"][value="${cmd.mode || 'random'}"]`);
    if (modeRadio) modeRadio.checked = true;
    editingCmdName = cmd.name;
  } catch (e) {
    toast(`加载失败: ${e.message}`, 'error');
  }
});

deleteCmdBtn.addEventListener('click', async () => {
  const name = editingCmdName || cmdName.value.trim();
  if (!name) { toast('请选择或输入要删除的指令名', 'error'); return; }
  try {
    await bridge.apiPost('delete_command', { name });
    toast(`已删除指令「${name}」`, 'info');
    cmdName.value = '';
    cmdName.readOnly = false;
    currentSteps = [];
    renderSteps();
    editingCmdName = '';
    refreshCmdList();
  } catch (e) {
    toast(`删除失败: ${e.message}`, 'error');
  }
});

saveConfigBtn.addEventListener('click', saveConfig);
deleteConfigBtn.addEventListener('click', deleteConfig);
configSelect.addEventListener('change', loadConfig);

// ─── 调用记录 ────────────────────────────

// 日志列表：错峰入场
async function loadLogs(page) {
  if (page !== undefined) currentLogPage = page;
  try {
    const r = await bridge.apiGet('llm_logs', { page: currentLogPage, limit: 20 });
    const logs = r.logs || [];
    totalLogs = r.total || 0;
    logsCount.textContent = `共 ${totalLogs} 条`;
    logsPage.textContent = `第 ${currentLogPage} 页`;
    logsPrevBtn.disabled = currentLogPage <= 1;
    logsNextBtn.disabled = currentLogPage * 20 >= totalLogs;

    if (logs.length === 0) {
      logsList.innerHTML = '<div class="empty-row">暂无调用记录</div>';
      return;
    }

    let h = '';
    logs.forEach((log, idx) => {
      const statusClass = log.result === '成功' ? 'success' : 'fail';
      const realIdx = (currentLogPage - 1) * 20 + idx;
      const delay = Math.min(idx * 30, 240);
      h += `<div class="log-item" data-index="${realIdx}" style="cursor:pointer;animation:fadeUp .35s cubic-bezier(.22,1,.36,1) both;animation-delay:${delay}ms;">
        <div class="log-status ${statusClass}"></div>
        <div class="log-info">
          <div class="log-time">${log.time}</div>
          <div class="log-source">${log.source}${log.tag ? ' · ' + log.tag : ''}</div>
          <div class="log-detail">${log.detail || ''}</div>
        </div>
        <div class="log-user">${log.group || ''}</div>
      </div>`;
    });
    logsList.innerHTML = h;

    logsList.querySelectorAll('.log-item').forEach(item => {
      item.addEventListener('click', () => {
        const index = parseInt(item.dataset.index);
        showLogDetail(index);
      });
    });
  } catch (e) {
    logsList.innerHTML = `<div class="empty-row">加载失败: ${e.message}</div>`;
  }
}

refreshLogsBtn.addEventListener('click', () => loadLogs(1));
logsPrevBtn.addEventListener('click', () => { if (currentLogPage > 1) loadLogs(currentLogPage - 1); });
logsNextBtn.addEventListener('click', () => { if (currentLogPage * 20 < totalLogs) loadLogs(currentLogPage + 1); });

// ─── 调用详情弹窗 + 一键复制 ─────────────────

function fallbackCopy(text, done, fail) {
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.top = '-9999px';
    ta.style.left = '-9999px';
    ta.style.opacity = '0';
    document.body.appendChild(ta);

    const selection = document.getSelection();
    const prevRange = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;

    ta.focus();
    ta.select();
    ta.setSelectionRange(0, ta.value.length);

    const ok = document.execCommand('copy');
    document.body.removeChild(ta);

    if (prevRange) {
      selection.removeAllRanges();
      selection.addRange(prevRange);
    }

    if (ok) done(); else fail();
  } catch (e) {
    fail();
  }
}

function copyText(text) {
  const done = () => toast('已复制到剪贴板', 'success');
  const fail = () => toast('复制失败，请手动复制', 'error');

  if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done, fail));
    return;
  }

  fallbackCopy(text, done, fail);
}

// ─── 大图查看器（全屏 · 网页缩放 · rAF 补间 · 左右 cover / 上下自由） ───

let ivScale = 1, ivTx = 0, ivTy = 0;
let ivUrl = '';
let ivMinScale = 0.05;           // 最小缩放（= 左右铺满的比例）
let ivNatW = 800, ivNatH = 600;  // 图片自然尺寸（缓存）
let ivBaseX = 0, ivBaseY = 0;    // 元素居中基准位（缓存）
let ivSW = 0, ivSH = 0;          // 舞台尺寸（缓存）
const ivClamp = (v, a, b) => Math.min(b, Math.max(a, v));

// 测量一次并缓存（含舞台尺寸）
function ivMeasure() {
  ivNatW = imgViewerImg.naturalWidth || 800;
  ivNatH = imgViewerImg.naturalHeight || 600;
  ivSW = imgViewerStage.clientWidth;
  ivSH = imgViewerStage.clientHeight;
  ivBaseX = (ivSW - ivNatW) / 2;
  ivBaseY = (ivSH - ivNatH) / 2;
}

// 位置钳制：仅左右做 cover（必须盖满屏幕宽度，不留左右空隙）；上下自由
function ivClampPos() {
  const W = ivNatW * ivScale;
  const tlX = ivBaseX + ivTx;

  let minX, maxX;
  if (W >= ivSW) {
    minX = ivSW - W;   // 右边缘贴屏幕右
    maxX = 0;          // 左边缘贴屏幕左
  } else {
    minX = maxX = (ivSW - W) / 2;
  }
  ivTx = ivClamp(tlX, minX, maxX) - ivBaseX;
  // 垂直不钳制
}

function ivApply() {
  ivClampPos();
  imgViewerImg.style.transform = `translate(${ivTx}px, ${ivTy}px) scale(${ivScale})`;
  imgViewerZoom.textContent = Math.round(ivScale * 100) + '%';
}

// 左右铺满的目标状态
function ivFitTarget() {
  const s = Math.max(ivSW / ivNatW, 0.05);
  return {
    s: s,
    x: 0 - ivBaseX,
    y: (ivSH - ivNatH * s) / 2 - ivBaseY,
  };
}

// 直接跳到适应（打开/窗口变化时用）
function ivFit() {
  const t = ivFitTarget();
  ivMinScale = t.s;
  ivScale = t.s; ivTx = t.x; ivTy = t.y;
  ivApply();
}

// 以屏幕中心为锚计算缩放后的目标状态（不动当前值）
function ivZoomTargetAtCenter(factor) {
  const px = ivSW / 2, py = ivSH / 2;
  const rectLeft = ivBaseX + ivTx;
  const rectTop = ivBaseY + ivTy;
  const fx = (px - rectLeft) / (ivNatW * ivScale);
  const fy = (py - rectTop) / (ivNatH * ivScale);
  const ns = ivClamp(ivScale * factor, ivMinScale, 8);
  return {
    s: ns,
    x: (px - fx * ivNatW * ns) - ivBaseX,
    y: (py - fy * ivNatH * ns) - ivBaseY,
  };
}

// ─── rAF 补间动画（可被打断重定向，连点不吞动画） ───
let ivTween = null;
function ivStopTween() {
  if (ivTween) { cancelAnimationFrame(ivTween.id); ivTween = null; }
}
function ivTweenTo(target, dur) {
  ivStopTween();
  const from = { s: ivScale, x: ivTx, y: ivTy };
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / dur);
    const e = 1 - Math.pow(1 - t, 3);   // easeOutCubic
    ivScale = from.s + (target.s - from.s) * e;
    ivTx = from.x + (target.x - from.x) * e;
    ivTy = from.y + (target.y - from.y) * e;
    ivApply();
    if (t < 1) { ivTween = { id: requestAnimationFrame(step) }; }
    else { ivTween = null; }
  };
  ivTween = { id: requestAnimationFrame(step) };
}

// 按钮点击弹跳动画
function ivPop(btn) {
  btn.classList.remove('iv-pop');
  void btn.offsetWidth;
  btn.classList.add('iv-pop');
}

// Base64 提示：从左侧 Q 弹弹出，停留后收回
let ivToastTimer = null;
let ivToastRaf = null;
function showBase64Toast(isBase64) {
  clearTimeout(ivToastTimer);
  if (ivToastRaf) cancelAnimationFrame(ivToastRaf);
  imgViewerToast.classList.remove('show');
  if (!isBase64) return;
  // 等浏览器完成显示（display→可见）后再加 show，否则弹入动画会被吞
  ivToastRaf = requestAnimationFrame(() => {
    imgViewerToast.classList.add('show');
    ivToastTimer = setTimeout(() => imgViewerToast.classList.remove('show'), 3500);
  });
}

function openImgViewer(img) {
  if (!img) return;

  // 展示源：优先用已下载的图片本体（base64），保证"大图=小图"
  let src = '';
  if (img.thumb && /^data:image\//i.test(img.thumb)) {
    src = img.thumb;
  } else {
    src = img.source_url || '';
    if (!src && img.url && /^https?:/i.test(img.url)) src = img.url;
    if (!src) src = img.thumb || '';
  }
  imgViewerImg.src = src;

  // Base64 大图才弹出"勿长按查看"提示
  showBase64Toast(/^data:image\//i.test(src));

  // 复制链接：用公开 URL（base64 数据不适合当链接）
  ivUrl = (img.source_url && /^https?:/i.test(img.source_url)) ? img.source_url
        : (img.url && /^https?:/i.test(img.url)) ? img.url
        : '';

  ivStopTween();
  imgViewerImg.onload = () => { ivMeasure(); ivFit(); };
  imgViewerImg.src = src;

  const titleParts = [];
  if (img.title) titleParts.push(`<span>${escHtml(img.title)}</span>`);
  if (img.author) titleParts.push(`<span class="iv-meta"><span class="material-icons iv-meta-icon">person</span>${escHtml(img.author)}</span>`);
  if (img.command) titleParts.push(`<span class="iv-meta"><span class="material-icons iv-meta-icon">terminal</span>指令: ${escHtml(img.command)}</span>`);
  imgViewerTitle.innerHTML = titleParts.join('<span class="iv-meta-sep"> · </span>') || '图片';

  // 先显示弹层，再弹 Base64 提示（否则弹入动画会被吞）
  imgViewerModal.classList.remove('hidden');
  showBase64Toast(/^data:image\//i.test(src));
}

imgViewerClose.addEventListener('click', () => imgViewerModal.classList.add('hidden'));
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !imgViewerModal.classList.contains('hidden')) {
    imgViewerModal.classList.add('hidden');
  }
});

// 窗口尺寸变化时重新测量并适应（查看器打开时）
window.addEventListener('resize', () => {
  if (!imgViewerModal.classList.contains('hidden')) {
    ivMeasure();
    ivFit();
  }
});

// + / - / 适应 按钮：rAF 补间动画（连点不吞动画）
imgViewerZoomIn.addEventListener('click', () => {
  ivPop(imgViewerZoomIn);
  ivTweenTo(ivZoomTargetAtCenter(1.3), 180);
});
imgViewerZoomOut.addEventListener('click', () => {
  ivPop(imgViewerZoomOut);
  ivTweenTo(ivZoomTargetAtCenter(1 / 1.3), 180);
});
imgViewerFit.addEventListener('click', () => {
  ivPop(imgViewerFit);
  ivTweenTo(ivFitTarget(), 220);
});

// 滚轮缩放：以鼠标位置为中心（即时）
imgViewerStage.addEventListener('wheel', (e) => {
  e.preventDefault();
  ivStopTween();
  const px = e.clientX, py = e.clientY;
  const rectLeft = ivBaseX + ivTx;
  const rectTop = ivBaseY + ivTy;
  const fx = (px - rectLeft) / (ivNatW * ivScale);
  const fy = (py - rectTop) / (ivNatH * ivScale);
  const ns = ivClamp(ivScale * (e.deltaY < 0 ? 1.15 : 0.87), ivMinScale, 8);
  ivTx = (px - fx * ivNatW * ns) - ivBaseX;
  ivTy = (py - fy * ivNatH * ns) - ivBaseY;
  ivScale = ns;
  ivApply();
}, { passive: false });

// 指针：单指拖拽 + 双指缩放/平移（网页缩放逻辑）
let ivPointers = new Map();
let ivDragging = false, ivSX = 0, ivSY = 0, ivSTx = 0, ivSTy = 0;
let ivPinchDist = 0, ivPinchMidX = 0, ivPinchMidY = 0;

imgViewerStage.addEventListener('pointerdown', (e) => {
  ivStopTween();
  ivPointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  imgViewerStage.setPointerCapture(e.pointerId);
  if (ivPointers.size === 1) {
    ivDragging = true;
    ivSX = e.clientX; ivSY = e.clientY;
    ivSTx = ivTx; ivSTy = ivTy;
    imgViewerStage.classList.add('dragging');
  } else if (ivPointers.size === 2) {
    ivDragging = false;
    imgViewerStage.classList.remove('dragging');
    const p = [...ivPointers.values()];
    ivPinchDist = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
    ivPinchMidX = (p[0].x + p[1].x) / 2;
    ivPinchMidY = (p[0].y + p[1].y) / 2;
  }
});

imgViewerStage.addEventListener('pointermove', (e) => {
  if (!ivPointers.has(e.pointerId)) return;
  ivPointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (ivPointers.size === 1 && ivDragging) {
    ivTx = ivSTx + (e.clientX - ivSX);
    ivTy = ivSTy + (e.clientY - ivSY);
    ivApply();
  } else if (ivPointers.size === 2) {
    const p = [...ivPointers.values()];
    const dist = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
    const midX = (p[0].x + p[1].x) / 2;
    const midY = (p[0].y + p[1].y) / 2;
    if (ivPinchDist > 0 && dist > 0) {
      // 网页缩放逻辑：以屏幕中心为锚缩放
      const px = ivSW / 2, py = ivSH / 2;
      const rectLeft = ivBaseX + ivTx;
      const rectTop = ivBaseY + ivTy;
      const fx = (px - rectLeft) / (ivNatW * ivScale);
      const fy = (py - rectTop) / (ivNatH * ivScale);
      const ns = ivClamp(ivScale * (dist / ivPinchDist), ivMinScale, 8);
      ivTx = (px - fx * ivNatW * ns) - ivBaseX;
      ivTy = (py - fy * ivNatH * ns) - ivBaseY;
      ivScale = ns;
    }
    ivTx += (midX - ivPinchMidX) / ivScale;
    ivTy += (midY - ivPinchMidY) / ivScale;
    ivPinchDist = dist;
    ivPinchMidX = midX; ivPinchMidY = midY;
    ivApply();
  }
});

function ivEndPointer(e) {
  ivPointers.delete(e.pointerId);
  ivDragging = false;
  imgViewerStage.classList.remove('dragging');
}
imgViewerStage.addEventListener('pointerup', ivEndPointer);
imgViewerStage.addEventListener('pointercancel', ivEndPointer);

// 复制链接
imgViewerCopy.addEventListener('click', () => {
  if (ivUrl) copyText(ivUrl);
});

// ─── 单张图片详情 / 调用记录详情（共用弹窗，统一读后端） ───

// 与后端日志时间格式保持一致
function fmtTime(d) {
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

// 填充详情弹窗（调用记录 与 单张图片 共用）
function fillLogDetail(log) {
  currentLog = log;
  detailTime.textContent = log.time;
  detailUser.textContent = log.user;
  detailGroup.textContent = log.group;
  detailSource.textContent = log.source;
  detailTag.textContent = log.tag || '(无)';
  detailResult.textContent = log.result;
  detailPrompt.textContent = log.prompt || '(无)';
  detailDetail.textContent = log.detail || '(无)';
  detailApi.textContent = log.api || '(无)';
  detailRaw.textContent = log.raw || '(无)';
}

// 单张图片详情：优先读后端真实记录，读不到再本地兜底（格式与后端一致）
async function showImgLog(img) {
  if (!img) return;
  if (typeof img.log_index === 'number') {
    try {
      const r = await bridge.apiGet('llm_log_detail', { index: img.log_index });
      if (r && r.log) {
        fillLogDetail(r.log);
        logDetailModal.classList.remove('hidden');
        return;
      }
    } catch (e) {
      // 记录可能已被上限截断，回退本地构造
    }
  }
  // 本地兜底（与后端日志同款格式）
  const source = img.source || 'random';
  const cmd = img.command || '';
  let u = img.source_url || img.url || '';
  if (u && !/^https?:/i.test(u)) u = '(本地临时文件)';
  fillLogDetail({
    time: fmtTime(new Date()),
    user: 'WebUI',
    group: '-',
    source: source,
    tag: cmd || '(无)',
    result: '成功',
    prompt: JSON.stringify(lastFetch.params || {}),
    detail: '1 张',
    api: img.api || '未知图源',
    raw: JSON.stringify([{ url: u, title: img.title || '', author: img.author || '', pid: img.pid || '' }], null, 2),
  });
  logDetailModal.classList.remove('hidden');
}

async function showLogDetail(index) {
  try {
    const r = await bridge.apiGet('llm_log_detail', { index });
    fillLogDetail(r.log);
    logDetailModal.classList.remove('hidden');
  } catch (e) {
    toast('加载详情失败: ' + e.message, 'error');
  }
}

logCopyBtn.addEventListener('click', () => {
  if (!currentLog) return;
  const log = currentLog;
  const text = [
    '【调用详情】',
    `时间：${log.time || ''}`,
    `用户：${log.user || ''}`,
    `群组：${log.group || ''}`,
    `图源：${log.source || ''}`,
    `指令：${log.tag || '(无)'}`,
    `结果：${log.result || ''}`,
    '',
    `用户消息：\n${log.prompt || '(无)'}`,
    '',
    `详情：\n${log.detail || '(无)'}`,
    '',
    `详细 API：\n${log.api || '(无)'}`,
    '',
    `API 返回结果：\n${log.raw || '(无)'}`,
  ].join('\n');
  copyText(text);
});

logDetailClose.addEventListener('click', () => {
  logDetailModal.classList.add('hidden');
});

logDetailModal.addEventListener('click', (e) => {
  if (e.target === logDetailModal) {
    logDetailModal.classList.add('hidden');
  }
});

toggleSource();
await bridge.ready();