const bridge = window.AstrBotPluginPage;
bridge.pluginName = 'astrbot_plugin_setu_webui';

const fetchBtn = document.getElementById('fetchBtn');
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

const modeBtns = document.querySelectorAll('.mode-btn');
const quickSection = document.getElementById('quickSection');
const blocksSection = document.getElementById('blocksSection');

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

let allImages = [];
let selectedImages = new Set();
let allGroups = [];
let selectedGroups = new Set();
let timer = null;
let currentSteps = [];
let editingCmdName = '';

function toast(msg, type) {
  const map = { success: 'check_circle', error: 'error', info: 'info' };
  resultIcon.textContent = map[type] || 'info';
  resultMessage.textContent = msg;
  resultToast.className = `result-toast ${type}`;
  resultToast.classList.remove('hidden');
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => resultToast.classList.add('hidden'), 2000);
}

// ─── 模式切换 ───────────────────────

modeBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    modeBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const mode = btn.dataset.mode;
    quickSection.classList.toggle('hidden', mode !== 'quick');
    blocksSection.classList.toggle('hidden', mode !== 'blocks');
    if (mode === 'blocks') {
      refreshAvailablePresets();
      refreshCmdList();
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
  document.querySelector('.source-lolicon').classList.toggle('hidden', v !== 'lolicon');
  document.querySelector('.source-uapipro').classList.toggle('hidden', v !== 'uapipro');
  document.querySelector('.source-bing').classList.toggle('hidden', v !== 'bing');
  document.querySelector('.source-imgapi').classList.toggle('hidden', v !== 'imgapi');
  document.querySelector('.source-loliapi').classList.toggle('hidden', v !== 'loliapi');
  document.querySelector('.source-alcy').classList.toggle('hidden', v !== 'alcy');

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

// ─── 获取图片 ─────────────────────

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

  fetchBtn.disabled = true;
  progressBar.classList.remove('hidden');
  progressFill.style.width = '30%';
  progressText.textContent = '获取中...';

  try {
    const r = await bridge.apiPost('fetch', params);
    progressFill.style.width = '100%';
    progressText.textContent = '完成';

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
    fetchBtn.disabled = false;
    setTimeout(() => progressBar.classList.add('hidden'), 500);
  }
});

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
    h += `<div class="setu-card ${c ? 'selected' : ''}" data-i="${i}">
      <div class="setu-img-wrap">
        <img class="setu-img" src="${img.thumb || img.url}" alt="" loading="lazy"
             referrerpolicy="no-referrer"
             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%23e5e7eb%22 width=%22200%22 height=%22200%22/%3E%3Ctext x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%239ca3af%22 font-size=%2214%22%3E%E5%8A%A0%E8%BD%BD%E5%A4%B1%E8%B4%A5%3C/text%3E%3C/svg%3E'" />
        <div class="setu-overlay">
          <input type="checkbox" class="setu-checkbox" ${c} />
        </div>
      </div>
      <div class="setu-info">
        <div class="setu-title">${img.title || '无题'}</div>
        <div class="setu-meta">${img.author || ''}</div>
      </div>
    </div>`;
  });
  grid.innerHTML = h;
  grid.querySelectorAll('.setu-card').forEach(card => {
    card.addEventListener('click', function(e) {
      if (e.target.closest('.setu-checkbox')) return;
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

function renderGroups() {
  if (allGroups.length === 0) { groupGrid.innerHTML = '<div class="empty-row">暂无群</div>'; return; }
  let h = '';
  allGroups.forEach(g => {
    const id = String(g.id);
    const c = selectedGroups.has(id) ? 'checked' : '';
    h += `<div class="group-card ${c ? 'selected' : ''}" data-id="${id}">
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
    list.push({ url: img.url, title: img.title, author: img.author, pid: img.pid });
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

function renderSteps() {
  if (currentSteps.length === 0) {
    stepList.innerHTML = '<div class="empty-row">暂无步骤，请添加</div>';
    return;
  }
  let h = '';
  currentSteps.forEach((step, i) => {
    h += `<div class="step-item">
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

toggleSource();
await bridge.ready();