// State
const state = {
  filters: { search: '', type: '', age: '', subreddit: '', tags: [] },
  page: 1,
  limit: 50,
  selectedIds: new Set(),
  allTags: [],
};

// View routing
function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  if (name === 'setup') loadSetupData();
}

async function init() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('error') === 'auth_failed') {
    const err = document.getElementById('connect-error');
    err.textContent = 'Authentication failed. Please try again.';
    err.style.display = '';
  }

  const res = await fetch('/api/auth/status');
  const data = await res.json();
  if (!data.authenticated) {
    showView('connect');
    return;
  }
  showView('browse');
  await loadTags();
  await loadItems();
  setupEventListeners();
}

// ---- API helpers ----
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ---- Tags ----
async function loadTags() {
  state.allTags = await api('/api/tags');
}

// ---- Items ----
async function loadItems() {
  const p = new URLSearchParams();
  if (state.filters.search) p.set('search', state.filters.search);
  if (state.filters.type) p.set('type', state.filters.type);
  if (state.filters.age) p.set('age', state.filters.age);
  if (state.filters.subreddit) p.set('subreddit', state.filters.subreddit);
  if (state.filters.tags.length) p.set('tags', state.filters.tags.join(','));
  p.set('page', state.page);
  p.set('limit', state.limit);

  const data = await api('/api/items?' + p.toString());
  renderCards(data.items);
  renderStats(data.total, data.page, data.limit);
  renderPagination(data.total, data.page, data.limit);
  renderFilterChips();
  document.getElementById('header-count').textContent =
    data.total.toLocaleString() + ' items';
}

function renderStats(total, page, limit) {
  const start = (page - 1) * limit + 1;
  const end = Math.min(page * limit, total);
  const text = total === 0 ? 'No items' : `${start}–${end} of ${total.toLocaleString()}`;
  document.getElementById('stats-text').textContent = text;
}

function renderPagination(total, page, limit) {
  const pages = Math.ceil(total / limit);
  const html = pages <= 1 ? '' : Array.from({ length: Math.min(pages, 10) }, (_, i) => {
    const n = i + 1;
    return `<button class="btn${n === page ? ' btn-primary' : ''}" onclick="goPage(${n})">${n}</button>`;
  }).join('');
  document.getElementById('pagination-top').innerHTML = html;
  document.getElementById('pagination-bottom').innerHTML = html;
}

function goPage(n) {
  state.page = n;
  state.selectedIds.clear();
  loadItems();
  window.scrollTo(0, 0);
}

// ---- Card rendering ----
function renderCards(items) {
  const list = document.getElementById('cards-list');
  list.innerHTML = items.map(item => cardHTML(item)).join('');
  updateBulkBar();
}

function tagClass(tag) {
  if (tag.name === 'old') return 'tag-old';
  if (tag.source === 'system') return 'tag-system';
  if (tag.source === 'user') return 'tag-user';
  return 'tag-ai';
}

function timeAgo(ts) {
  const days = Math.floor((Date.now() / 1000 - ts) / 86400);
  if (days < 1) return 'today';
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

function cardHTML(item) {
  const isOld = item.tags.some(t => t.name === 'old');
  const tagChips = item.tags.map(t =>
    `<span class="tag ${tagClass(t)}" onclick="addTagFilter('${escHtml(t.name)}')">${escHtml(t.name)}</span>`
  ).join('');
  const checked = state.selectedIds.has(item.id) ? 'checked' : '';
  return `
    <div class="card" id="card-${item.id}">
      <div class="card-check">
        <input type="checkbox" ${checked} onchange="toggleSelect('${item.id}', this.checked)">
      </div>
      <div class="card-body">
        <div class="card-meta">
          <span>r/${escHtml(item.subreddit)}</span>
          <span>·</span>
          <span>${timeAgo(item.saved_at)}</span>
          ${item.type === 'comment' ? '<span class="badge badge-comment">comment</span>' : ''}
          ${isOld ? '<span class="badge badge-old">old</span>' : ''}
          ${item.ai_status === 'error' ? '<span class="badge badge-error">AI error</span>' : ''}
        </div>
        ${item.type === 'comment' && item.title
          ? `<div style="font-size:.75rem;color:var(--text2);margin-bottom:.2rem;font-style:italic;">on: "${escHtml(item.title)}"</div>`
          : `<div class="card-title"><a href="${escHtml(item.permalink)}" target="_blank" rel="noopener">${escHtml(item.title || '(no title)')}</a></div>`
        }
        ${item.summary ? `<div class="card-summary">${escHtml(item.summary)}</div>` : ''}
        <div class="card-tags">
          ${tagChips}
          <button class="tag-add-btn" onclick="openTagInput('${item.id}')">+ tag</button>
          <div id="tag-input-${item.id}" class="tag-input-wrap" style="display:none;"></div>
        </div>
      </div>
      <div class="card-score">&#x2191; ${item.score.toLocaleString()}</div>
    </div>`;
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ---- Tag input ----
function openTagInput(itemId) {
  const wrap = document.getElementById('tag-input-' + itemId);
  wrap.style.display = 'inline-block';
  wrap.innerHTML = `
    <input class="tag-input" id="taginput-${itemId}" placeholder="add tag…" autocomplete="off"
      oninput="showTagSuggestions('${itemId}', this.value)"
      onkeydown="tagInputKey(event, '${itemId}')">
    <div class="tag-suggestions" id="tagsugg-${itemId}" style="display:none;"></div>`;
  document.getElementById('taginput-' + itemId).focus();
}

function showTagSuggestions(itemId, value) {
  const sugg = document.getElementById('tagsugg-' + itemId);
  if (!value.trim()) { sugg.style.display = 'none'; return; }
  const matches = state.allTags.filter(t => t.name.includes(value.toLowerCase())).slice(0, 6);
  const exactMatch = matches.some(t => t.name === value.toLowerCase());
  sugg.innerHTML = matches.map(t =>
    `<div class="tag-suggestion" onclick="applyTag('${itemId}', '${escHtml(t.name)}')">${escHtml(t.name)}</div>`
  ).join('') + (!exactMatch && value
    ? `<div class="tag-suggestion tag-suggestion-new" onclick="applyTag('${itemId}', '${escHtml(value.toLowerCase())}')">+ create "${escHtml(value.toLowerCase())}"</div>`
    : '');
  sugg.style.display = matches.length || value ? 'block' : 'none';
}

async function tagInputKey(e, itemId) {
  if (e.key === 'Enter') {
    const val = document.getElementById('taginput-' + itemId).value.trim();
    if (val) await applyTag(itemId, val);
  } else if (e.key === 'Escape') {
    document.getElementById('tag-input-' + itemId).style.display = 'none';
  }
}

async function applyTag(itemId, tagName) {
  // Step 1: create or get existing tag (returns id)
  const tag = await api('/api/tags', { method: 'POST', body: { name: tagName } });
  // Step 2: assign tag to item using its integer id
  await api(`/api/items/${itemId}/tags`, { method: 'POST', body: { tag_id: tag.id } });
  document.getElementById('tag-input-' + itemId).style.display = 'none';
  await loadTags();
  await loadItems();
}

// ---- Filters ----
function addTagFilter(name) {
  if (!state.filters.tags.includes(name)) {
    state.filters.tags.push(name);
    state.page = 1;
    loadItems();
  }
}

function renderFilterChips() {
  const container = document.getElementById('filter-chips');
  const chips = [];
  if (state.filters.type) chips.push({ label: state.filters.type, clear: () => { state.filters.type = ''; } });
  if (state.filters.age) chips.push({ label: 'old', clear: () => { state.filters.age = ''; } });
  if (state.filters.subreddit) chips.push({ label: 'r/' + state.filters.subreddit, clear: () => { state.filters.subreddit = ''; } });
  state.filters.tags.forEach(t => chips.push({ label: t, clear: () => {
    state.filters.tags = state.filters.tags.filter(x => x !== t);
  }}));
  container.innerHTML = chips.map((c, i) =>
    `<span class="chip">${escHtml(c.label)} <span class="chip-remove" onclick="clearChip(${i})">×</span></span>`
  ).join('');
  window._chipClearFns = chips.map(c => c.clear);
}

function clearChip(i) {
  window._chipClearFns[i]();
  state.page = 1;
  loadItems();
}

// ---- Bulk select ----
function toggleSelect(id, checked) {
  if (checked) state.selectedIds.add(id);
  else state.selectedIds.delete(id);
  updateBulkBar();
}

function updateBulkBar() {
  const bar = document.getElementById('bulk-bar');
  const count = state.selectedIds.size;
  document.getElementById('bulk-count').textContent = count + ' item' + (count !== 1 ? 's' : '') + ' selected';
  bar.classList.toggle('hidden', count === 0);
}

// ---- Event listeners ----
function setupEventListeners() {
  let searchTimer;
  document.getElementById('search-input').addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.filters.search = e.target.value;
      state.page = 1;
      loadItems();
    }, 300);
  });

  document.getElementById('btn-sync').addEventListener('click', async () => {
    const btn = document.getElementById('btn-sync');
    btn.textContent = '↻ Syncing…';
    btn.disabled = true;
    try {
      await api('/api/sync/trigger', { method: 'POST' });
      await loadItems();
    } catch (e) {
      alert('Sync failed: ' + e.message);
    } finally {
      btn.textContent = '↻ Sync';
      btn.disabled = false;
    }
  });

  document.getElementById('btn-bulk-unsave').addEventListener('click', async () => {
    const ids = Array.from(state.selectedIds);
    if (!confirm(`Unsave ${ids.length} item(s) from Reddit? This cannot be undone.`)) return;
    await api('/api/items/bulk-unsave', { method: 'POST', body: { ids } });
    state.selectedIds.clear();
    await loadItems();
  });

  document.getElementById('btn-bulk-clear').addEventListener('click', () => {
    state.selectedIds.clear();
    document.querySelectorAll('.card-check input').forEach(cb => cb.checked = false);
    updateBulkBar();
  });

  document.getElementById('btn-filter-type').addEventListener('click', () => {
    const val = prompt('Filter by type (post / comment / leave blank to clear):');
    state.filters.type = val && ['post', 'comment'].includes(val) ? val : '';
    state.page = 1;
    loadItems();
  });

  document.getElementById('btn-filter-age').addEventListener('click', () => {
    state.filters.age = state.filters.age === 'old' ? '' : 'old';
    state.page = 1;
    loadItems();
  });

  document.getElementById('btn-filter-subreddit').addEventListener('click', () => {
    const val = prompt('Filter by subreddit name (or blank to clear):');
    state.filters.subreddit = val ? val.replace(/^r\//, '') : '';
    state.page = 1;
    loadItems();
  });
}

// ---- Setup view ----
async function loadSetupData() {
  const [auth, syncStatus, aiStats, settingsData] = await Promise.all([
    api('/api/auth/status'),
    api('/api/sync/status'),
    api('/api/settings/ai-stats'),
    api('/api/settings'),
  ]);

  document.getElementById('setup-auth-status').textContent = auth.authenticated ? 'Connected' : 'Not connected';
  document.getElementById('setup-username').textContent = auth.username || '—';

  if (syncStatus.last_sync) {
    document.getElementById('setup-last-sync').textContent = new Date(syncStatus.last_sync.started_at * 1000).toLocaleString();
    document.getElementById('setup-sync-status').textContent = syncStatus.last_sync.status;
  }

  document.getElementById('setup-ai-done').textContent = aiStats.done;
  document.getElementById('setup-ai-pending').textContent = aiStats.pending;
  document.getElementById('setup-ai-error').textContent = aiStats.error;
  if (aiStats.total > 0) {
    document.getElementById('setup-ai-progress').style.width = (aiStats.done / aiStats.total * 100).toFixed(1) + '%';
  }

  document.getElementById('settings-interval').value = settingsData.sync_interval_hours;

  document.getElementById('btn-setup-sync').onclick = async () => {
    try {
      await api('/api/sync/trigger', { method: 'POST' });
      alert('Sync started.');
      loadSetupData();
    } catch (e) { alert('Error: ' + e.message); }
  };

  document.getElementById('btn-save-settings').onclick = async () => {
    const hours = parseInt(document.getElementById('settings-interval').value, 10);
    if (!hours || hours < 1) { alert('Interval must be at least 1 hour.'); return; }
    await api('/api/settings', { method: 'PATCH', body: { sync_interval_hours: hours } });
    alert('Saved.');
  };
}

// ---- Boot ----
init();
