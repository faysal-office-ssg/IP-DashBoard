const API_BASE = 'http://localhost:8000';
const state = {
  devices: [],
  summary: { total_devices: 0, online_count: 0, offline_count: 0, unknown_count: 0 },
  filter: 'all',
  search: '',
  lastUpdated: null,
  refreshTimer: null,
  editDeviceId: null,
};

const elements = {
  summaryTotal: document.getElementById('summary-total'),
  summaryOnline: document.getElementById('summary-online'),
  summaryOffline: document.getElementById('summary-offline'),
  summaryUnknown: document.getElementById('summary-unknown'),
  lastUpdated: document.getElementById('last-updated'),
  autoRefreshIndicator: document.getElementById('auto-refresh-indicator'),
  refreshButton: document.getElementById('refresh-btn'),
  addDeviceButton: document.getElementById('add-device-btn'),
  alertBanner: document.getElementById('offline-alert'),
  tableBody: document.getElementById('device-table-body'),
  searchInput: document.getElementById('search-input'),
  statusFilter: document.getElementById('status-filter'),
  deviceModal: document.getElementById('device-modal'),
  modalTitle: document.getElementById('device-modal-title'),
  deviceForm: document.getElementById('device-form'),
  formStatus: document.getElementById('form-status'),
  deleteConfirmModal: document.getElementById('delete-confirm-modal'),
  deleteConfirmText: document.getElementById('delete-device-name'),
  deleteDeviceId: document.getElementById('delete-device-id'),
};

function formatDateTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function formatMs(value) {
  if (value === null || value === undefined || value === '') return '—';
  return `${value} ms`;
}

function showError(message) {
  elements.formStatus.textContent = message;
}

function showTableLoading() {
  elements.tableBody.innerHTML = `
    <tr>
      <td colspan="10" class="loading-state">Loading devices...</td>
    </tr>
  `;
}

function updateSummary() {
  elements.summaryTotal.textContent = state.summary.total_devices;
  elements.summaryOnline.textContent = state.summary.online_count;
  elements.summaryOffline.textContent = state.summary.offline_count;
  elements.summaryUnknown.textContent = state.summary.unknown_count;

  const offlineCount = Number(state.summary.offline_count || 0);
  elements.alertBanner.classList.toggle('show', offlineCount > 0);
  elements.alertBanner.innerHTML = `
    <span class="alert-badge">!</span>
    <span>${offlineCount} device${offlineCount === 1 ? '' : 's'} offline and being monitored.</span>
  `;
}

function renderTable() {
  const filtered = state.devices.filter((device) => {
    const matchesFilter = state.filter === 'all' || device.status === state.filter;
    const searchText = state.search.trim().toLowerCase();
    const matchesSearch =
      !searchText ||
      [
        device.device_name,
        device.user_name,
        device.ip_address,
        device.location_or_point,
      ]
        .join(' ')
        .toLowerCase()
        .includes(searchText);
    return matchesFilter && matchesSearch;
  });

  if (!filtered.length) {
    elements.tableBody.innerHTML = `
      <tr>
        <td colspan="10" class="empty-state">No devices match the current filters.</td>
      </tr>
    `;
    return;
  }

  elements.tableBody.innerHTML = filtered
    .map((device) => {
      const rows = [
        '<tr class="',
        device.status === 'offline' ? 'offline-row' : '',
        '" data-device-id="',
        device.id,
        '">',
        '<td><span class="status-pill ',
        device.status,
        '"><span class="status-dot ',
        device.status,
        '"></span>',
        device.status,
        '</span></td>',
        '<td><div class="device-name">',
        escapeHtml(device.device_name),
        '</div><div class="meta">ID #',
        device.id,
        '</div></td>',
        '<td>',
        escapeHtml(device.user_name),
        '</td>',
        '<td><strong>',
        escapeHtml(device.ip_address),
        '</strong></td>',
        '<td>',
        escapeHtml(device.location_or_point),
        '</td>',
        '<td>',
        formatMs(device.last_response_ms),
        '</td>',
        '<td>',
        formatDateTime(device.last_ping_at),
        '</td>',
        '<td>',
        formatDateTime(device.down_since),
        '</td>',
        '<td>',
        '<div class="action-group">',
        '<button type="button" class="primary" data-action="ping" data-id="',
        device.id,
        '">Ping</button>',
        '<button type="button" data-action="edit" data-id="',
        device.id,
        '">Edit</button>',
        '<button type="button" class="danger" data-action="delete" data-id="',
        device.id,
        '">Delete</button>',
        '</div>',
        '</td>',
      ];
      return rows.join('');
    })
    .join('');
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function fetchJson(url, options = {}) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload.detail || 'Request failed';
    throw new Error(message);
  }

  return payload;
}

async function loadSummary() {
  try {
    const summary = await fetchJson('/api/dashboard/summary');
    state.summary = summary;
    updateSummary();
  } catch (error) {
    console.error('Summary load failed', error);
  }
}

async function loadDevices() {
  try {
    showTableLoading();
    const devices = await fetchJson('/api/devices');
    state.devices = devices;
    renderTable();
    state.lastUpdated = new Date();
    elements.lastUpdated.textContent = formatDateTime(state.lastUpdated);
    elements.autoRefreshIndicator.textContent = 'Auto-refresh: On';
  } catch (error) {
    elements.tableBody.innerHTML = `
      <tr>
        <td colspan="10" class="empty-state">Unable to load devices. ${escapeHtml(error.message)}</td>
      </tr>
    `;
  }
}

async function refreshDashboard() {
  await Promise.all([loadSummary(), loadDevices()]);
}

function startAutoRefresh() {
  if (state.refreshTimer) {
    clearInterval(state.refreshTimer);
  }
  state.refreshTimer = setInterval(() => {
    refreshDashboard();
  }, 5000);
}

function openDeviceModal(device = null) {
  elements.formStatus.textContent = '';
  elements.deviceForm.reset();
  state.editDeviceId = device ? device.id : null;

  if (device) {
    elements.modalTitle.textContent = 'Edit Device';
    document.getElementById('device-name').value = device.device_name;
    document.getElementById('user-name').value = device.user_name;
    document.getElementById('ip-address').value = device.ip_address;
    document.getElementById('location').value = device.location_or_point;
    document.getElementById('notes').value = device.notes || '';
    document.getElementById('is-active').checked = !!device.is_active;
  } else {
    elements.modalTitle.textContent = 'Add Device';
    document.getElementById('device-name').value = '';
    document.getElementById('user-name').value = '';
    document.getElementById('ip-address').value = '';
    document.getElementById('location').value = '';
    document.getElementById('notes').value = '';
    document.getElementById('is-active').checked = true;
  }

  elements.deviceModal.classList.add('open');
}

function closeDeviceModal() {
  elements.deviceModal.classList.remove('open');
  state.editDeviceId = null;
  elements.deviceForm.reset();
  elements.formStatus.textContent = '';
}

function openDeleteModal(deviceId, deviceName) {
  elements.deleteDeviceId.value = deviceId;
  elements.deleteConfirmText.textContent = deviceName;
  elements.deleteConfirmModal.classList.add('open');
}

function closeDeleteModal() {
  elements.deleteConfirmModal.classList.remove('open');
  elements.deleteDeviceId.value = '';
}

async function submitDeviceForm(event) {
  event.preventDefault();
  const payload = {
    device_name: document.getElementById('device-name').value.trim(),
    user_name: document.getElementById('user-name').value.trim(),
    ip_address: document.getElementById('ip-address').value.trim(),
    location_or_point: document.getElementById('location').value.trim(),
    notes: document.getElementById('notes').value.trim(),
    is_active: document.getElementById('is-active').checked,
  };

  if (!payload.device_name || !payload.user_name || !payload.ip_address || !payload.location_or_point) {
    showError('Please complete all required fields.');
    return;
  }

  try {
    if (state.editDeviceId) {
      await fetchJson(`/api/devices/${state.editDeviceId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
    } else {
      await fetchJson('/api/devices', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    }
    closeDeviceModal();
    await refreshDashboard();
  } catch (error) {
    showError(error.message);
  }
}

async function deleteDevice() {
  const deviceId = Number(elements.deleteDeviceId.value);
  if (!deviceId) return;

  try {
    await fetchJson(`/api/devices/${deviceId}`, { method: 'DELETE' });
    closeDeleteModal();
    await refreshDashboard();
  } catch (error) {
    console.error(error);
    closeDeleteModal();
    alert(error.message || 'Unable to delete device.');
  }
}

async function pingDevice(deviceId) {
  const button = document.querySelector(`[data-action="ping"][data-id="${deviceId}"]`);
  if (button) {
    button.disabled = true;
    button.textContent = 'Pinging...';
  }

  try {
    await fetchJson(`/api/devices/${deviceId}/ping`, { method: 'POST' });
    await refreshDashboard();
  } catch (error) {
    alert(error.message || 'Ping failed');
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = 'Ping';
    }
  }
}

function bindEvents() {
  elements.refreshButton.addEventListener('click', refreshDashboard);
  elements.addDeviceButton.addEventListener('click', () => openDeviceModal());
  elements.searchInput.addEventListener('input', (event) => {
    state.search = event.target.value;
    renderTable();
  });
  elements.statusFilter.addEventListener('change', (event) => {
    state.filter = event.target.value;
    renderTable();
  });
  elements.deviceForm.addEventListener('submit', submitDeviceForm);
  elements.deviceModal.addEventListener('click', (event) => {
    if (event.target === elements.deviceModal) {
      closeDeviceModal();
    }
  });
  elements.deleteConfirmModal.addEventListener('click', (event) => {
    if (event.target === elements.deleteConfirmModal) {
      closeDeleteModal();
    }
  });
  document.getElementById('cancel-device').addEventListener('click', closeDeviceModal);
  document.getElementById('cancel-delete').addEventListener('click', closeDeleteModal);
  document.getElementById('confirm-delete').addEventListener('click', deleteDevice);

  document.addEventListener('click', (event) => {
    const actionButton = event.target.closest('[data-action]');
    if (!actionButton) return;

    const deviceId = Number(actionButton.dataset.id);
    const action = actionButton.dataset.action;

    const device = state.devices.find((item) => item.id === deviceId);
    if (!device) return;

    if (action === 'ping') pingDevice(deviceId);
    if (action === 'edit') openDeviceModal(device);
    if (action === 'delete') openDeleteModal(deviceId, device.device_name);
  });
}

async function init() {
  bindEvents();
  await refreshDashboard();
  startAutoRefresh();
}

init();
