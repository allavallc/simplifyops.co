const page = document.body.dataset.page;
const dateFormatter = new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

const escapeHtml = (value = '') =>
  String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

const safeText = (value) => escapeHtml(value ?? '');

const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : dateFormatter.format(date);
};

const api = async (url, options = {}) => {
  const res = await fetch(url, options);
  if (res.status === 401) {
    window.location.href = '/';
    throw new Error('not signed in');
  }
  return res;
};

const getSession = async () => {
  try {
    const res = await fetch('/auth/me');
    const data = await res.json();
    return data.user || null;
  } catch {
    return null;
  }
};

const pathSegments = () => window.location.pathname.split('/').filter(Boolean);

const currentEmail = () => {
  const segments = pathSegments();
  if (!segments.length || segments[0] !== 'people') return null;
  if (segments[1] === 'new') return null;
  const raw = segments[1];
  return raw ? decodeURIComponent(raw) : null;
};

const isEditRoute = () => window.location.pathname.endsWith('/edit');

const renderHeader = (user) => {
  const header = document.getElementById('site-header');
  if (!header) return;

  const signedIn = Boolean(user);
  const nav = signedIn
    ? `
      <nav class="site-nav">
        <a href="/dashboard">Dashboard</a>
        ${user?.admin ? '<a href="/admin">Admin</a>' : ''}
      </nav>
      <div class="header-user">
        <div class="user-meta">
          <span class="user-name">${safeText(user?.name || user?.email || 'Admin')}</span>
          <span class="user-email">${safeText(user?.email || '')}</span>
        </div>
        <a class="button secondary small" href="/logout">Logout</a>
      </div>
    `
    : `
      <div class="header-user">
        <a class="button primary small" href="/auth/login">Sign in</a>
      </div>
    `;

  header.innerHTML = `
    <div class="site-header-inner">
      <a class="brand" href="${signedIn ? '/dashboard' : '/'}">
        <span class="brand-mark">PW</span>
        <span class="brand-text">
          <strong>People Whitelist</strong>
          <span>Access control</span>
        </span>
      </a>
      ${nav}
    </div>
  `;
};

const renderFooter = () => {
  const footer = document.getElementById('site-footer');
  if (!footer) return;
  footer.innerHTML = `
    <div class="site-footer-inner">
      <span>People Whitelist</span>
      <span>Internal admin tool</span>
      <span>${new Date().getFullYear()}</span>
    </div>
  `;
};

const emptyState = (title, body) => `
  <div class="empty-state">
    <strong>${safeText(title)}</strong>
    <p>${safeText(body)}</p>
  </div>
`;

const summaryCard = (label, value, hint = '') => `
  <article class="summary-card">
    <span>${safeText(label)}</span>
    <strong>${safeText(value)}</strong>
    <small>${safeText(hint)}</small>
  </article>
`;

const peopleRows = (rows) => {
  if (!rows.length) {
    return `<div class="table-empty">No people yet.</div>`;
  }

  return `
    <table class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Telegram ID</th>
          <th>Phone</th>
          <th>Admin</th>
          <th>Status</th>
          <th>Updated</th>
          <th class="actions-col">Actions</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                <td data-label="Name">${safeText(row.person_name)}</td>
                <td data-label="Email">${safeText(row.person_email)}</td>
                <td data-label="Telegram ID">${safeText(row.telegram_id || '—')}</td>
                <td data-label="Phone">${safeText(row.phone_country_code || '')}${row.phone_country_code && row.phone_number ? ' ' : ''}${safeText(row.phone_number || '—')}</td>
                <td data-label="Admin">${row.admin ? '<span class="status-pill admin">admin</span>' : '—'}</td>
                <td data-label="Status"><span class="status-pill ${safeText(row.status)}">${safeText(row.status)}</span></td>
                <td data-label="Updated">${safeText(formatDate(row.updated_at))}</td>
                <td data-label="Actions" class="row-actions">
                  <a href="/people/${encodeURIComponent(row.person_email)}" class="button secondary tiny">View</a>
                  <a href="/people/${encodeURIComponent(row.person_email)}/edit" class="button secondary tiny">Edit</a>
                  <button class="button danger tiny" data-delete-person="${safeText(row.person_email)}">Delete</button>
                </td>
              </tr>
            `
          )
          .join('')}
      </tbody>
    </table>
  `;
};

const auditRows = (rows) => {
  if (!rows.length) return emptyState('No audit entries yet.', 'Changes will appear here.');

  return `
    <div class="stack-list">
      ${rows
        .map(
          (row) => `
            <div class="stack-item">
              <div>
                <strong>${safeText(row.action)}</strong>
                <p>${safeText(row.actor_email || 'system')} · ${safeText(row.subject_email || '—')}</p>
              </div>
              <time>${safeText(formatDate(row.created_at))}</time>
            </div>
          `
        )
        .join('')}
    </div>
  `;
};

const peopleCards = (rows) => {
  if (!rows.length) return emptyState('No people yet.', 'Use Add person to create the first entry.');

  return `
    <div class="stack-list">
      ${rows
        .slice(0, 6)
        .map(
          (row) => `
            <div class="stack-item">
              <div>
                <strong>${safeText(row.person_name)}</strong>
                <p>${safeText(row.person_email)}</p>
              </div>
              <div class="stack-item-badges">
                ${row.admin ? '<span class="status-pill admin">admin</span>' : ''}
                <span class="status-pill ${safeText(row.status)}">${safeText(row.status)}</span>
              </div>
            </div>
          `
        )
        .join('')}
    </div>
  `;
};

const renderDashboard = async () => {
  const summary = document.getElementById('dashboard-summary');
  const people = document.getElementById('dashboard-people');
  const audit = document.getElementById('dashboard-audit');
  const res = await api('/api/admin/dashboard');
  const data = await res.json();

  const allowed = data.people.filter((row) => row.status === 'allowed').length;
  const blocked = data.people.filter((row) => row.status === 'blocked').length;
  const admins = data.people.filter((row) => row.admin).length;

  if (summary) {
    summary.innerHTML = [
      summaryCard('People total', data.people.length, 'All people records'),
      summaryCard('Allowed', allowed, 'Currently approved'),
      summaryCard('Blocked', blocked, 'Currently denied'),
      summaryCard('Admins', admins, 'People with admin access'),
    ].join('');
  }

  if (people) people.innerHTML = peopleCards(data.people);
  if (audit) audit.innerHTML = auditRows(data.audit);
};

const renderProfilePage = async () => {
  const form = document.getElementById('profile-form');
  if (!form) return;

  const res = await api('/auth/profile');
  if (!res.ok) {
    window.alert('Could not load your profile.');
    return;
  }

  const person = await res.json();
  const emailInput = form.querySelector('input[name="person_email"]');
  const telegramIdEl = document.getElementById('profile-telegram-id');
  const telegramUsernameEl = document.getElementById('profile-telegram-username');
  const telegramLastSeenEl = document.getElementById('profile-telegram-last-seen');
  if (form.person_name) form.person_name.value = person.person_name || '';
  if (emailInput) emailInput.value = person.person_email || '';
  if (form.telegram_id) form.telegram_id.value = person.telegram_id || '';
  if (form.phone_country_code) form.phone_country_code.value = person.phone_country_code || '';
  if (form.phone_number) form.phone_number.value = person.phone_number || '';
  if (form.notes) form.notes.value = person.notes || '';
  if (telegramIdEl) telegramIdEl.textContent = person.telegram_id || '—';
  if (telegramUsernameEl) telegramUsernameEl.textContent = person.telegram_username ? `@${person.telegram_username}` : '—';
  if (telegramLastSeenEl) telegramLastSeenEl.textContent = person.telegram_last_seen_at ? formatDate(person.telegram_last_seen_at) : '—';

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.person_name = String(payload.person_name || '').trim();
    payload.telegram_id = String(payload.telegram_id || '').trim();
    payload.phone_country_code = String(payload.phone_country_code || '').trim();
    payload.phone_number = String(payload.phone_number || '').trim();
    payload.notes = String(payload.notes || '').trim();

    const save = await api('/auth/profile', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!save.ok) {
      window.alert('Could not save your profile.');
      return;
    }

    window.location.href = '/dashboard';
  });

  // Job preferences section
  const jobPrefsForm = document.getElementById('job-prefs-form');
  if (jobPrefsForm) {
    const prefsRes = await api('/auth/job-preferences');
    if (prefsRes.ok) {
      const prefs = await prefsRes.json();
      if (jobPrefsForm.keywords) jobPrefsForm.keywords.value = (prefs.keywords || []).join(', ');
      if (jobPrefsForm.min_budget) jobPrefsForm.min_budget.value = prefs.min_budget || '';
      if (jobPrefsForm.job_type) jobPrefsForm.job_type.value = prefs.job_type || 'any';
      if (jobPrefsForm.remote_only) jobPrefsForm.remote_only.checked = Boolean(prefs.remote_only);
      if (jobPrefsForm.no_agencies) jobPrefsForm.no_agencies.checked = Boolean(prefs.no_agencies);
      if (jobPrefsForm.extra_instructions) jobPrefsForm.extra_instructions.value = prefs.extra_instructions || '';
    }
    jobPrefsForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        keywords: String(jobPrefsForm.keywords?.value || '').split(',').map(s => s.trim()).filter(Boolean),
        min_budget: jobPrefsForm.min_budget?.value ? Number(jobPrefsForm.min_budget.value) : null,
        job_type: jobPrefsForm.job_type?.value || 'any',
        remote_only: jobPrefsForm.remote_only?.checked ?? true,
        no_agencies: jobPrefsForm.no_agencies?.checked ?? true,
        extra_instructions: jobPrefsForm.extra_instructions?.value || '',
      };
      const r = await api('/auth/job-preferences', {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (r.ok) {
        const saved = document.getElementById('job-prefs-saved');
        if (saved) { saved.style.display = ''; setTimeout(() => saved.style.display = 'none', 2000); }
      }
    });
  }

  // CV section
  const cvStatus = document.getElementById('cv-status');
  const cvDownloadBtn = document.getElementById('cv-download-btn');
  const cvDeleteBtn = document.getElementById('cv-delete-btn');
  const cvForm = document.getElementById('cv-form');

  const loadCvStatus = async () => {
    const r = await api('/auth/cv');
    if (!r.ok) return;
    const data = await r.json();
    if (data.uploaded) {
      cvStatus.innerHTML = `<strong>${safeText(data.filename)}</strong> uploaded ${formatDate(data.uploaded_at)}`;
      if (cvDownloadBtn) cvDownloadBtn.style.display = '';
      if (cvDeleteBtn) cvDeleteBtn.style.display = '';
    } else {
      cvStatus.textContent = 'No CV uploaded yet.';
      if (cvDownloadBtn) cvDownloadBtn.style.display = 'none';
      if (cvDeleteBtn) cvDeleteBtn.style.display = 'none';
    }
  };

  await loadCvStatus();

  cvForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('cv-input');
    if (!input?.files?.length) return;
    const fd = new FormData();
    fd.append('cv', input.files[0]);
    const r = await fetch('/auth/cv', { method: 'POST', body: fd });
    if (r.ok) { input.value = ''; await loadCvStatus(); }
    else window.alert('Upload failed.');
  });

  cvDeleteBtn?.addEventListener('click', async () => {
    if (!window.confirm('Remove your CV?')) return;
    const r = await api('/auth/cv', { method: 'DELETE' });
    if (r.ok) await loadCvStatus();
  });
};

const renderPeopleIndex = async () => {
  const container = document.getElementById('people-table');
  const search = document.getElementById('people-search');
  const res = await api('/api/people');
  const data = await res.json();

  let rows = data;

  const draw = () => {
    const query = (search?.value || '').trim().toLowerCase();
    const filtered = !query
      ? rows
      : rows.filter((row) =>
          [
            row.person_name,
            row.person_email,
            row.telegram_id,
            row.phone_country_code,
            row.phone_number,
            row.status,
            row.notes,
            row.admin ? 'admin' : '',
          ].some((value) =>
            String(value || '').toLowerCase().includes(query)
          )
        );
    if (container) container.innerHTML = peopleRows(filtered);

    document.querySelectorAll('[data-delete-person]').forEach((button) => {
      button.addEventListener('click', async () => {
        const email = button.getAttribute('data-delete-person');
        if (!email) return;
        const ok = window.confirm(`Delete ${email}?`);
        if (!ok) return;
        const del = await api(`/api/people/${encodeURIComponent(email)}`, { method: 'DELETE' });
        if (!del.ok) {
          window.alert('Could not delete that person.');
          return;
        }
        rows = rows.filter((row) => row.person_email !== email);
        draw();
      });
    });
  };

  search?.addEventListener('input', draw);
  draw();
};

const renderPersonView = async () => {
  const container = document.getElementById('person-view');
  const email = currentEmail();
  const editLink = document.getElementById('edit-person-link');
  if (!email) {
    if (container) container.innerHTML = emptyState('No person selected.', 'Go back to the people list.');
    return;
  }

  const res = await api(`/api/people/${encodeURIComponent(email)}`);
  if (!res.ok) {
    if (container) container.innerHTML = emptyState('Person not found.', 'That whitelist entry does not exist.');
    return;
  }

  const person = await res.json();
  if (editLink) editLink.href = `/people/${encodeURIComponent(person.person_email)}/edit`;

  if (container) {
    container.innerHTML = `
      <div class="detail-grid">
        <div class="detail-card">
          <span>Name</span>
          <strong>${safeText(person.person_name)}</strong>
        </div>
        <div class="detail-card">
          <span>Email</span>
          <strong>${safeText(person.person_email)}</strong>
        </div>
        <div class="detail-card">
          <span>Telegram ID</span>
          <strong>${safeText(person.telegram_id || '—')}</strong>
        </div>
        <div class="detail-card">
          <span>Phone</span>
          <strong>${safeText((person.phone_country_code || '') + (person.phone_country_code && person.phone_number ? ' ' : '') + (person.phone_number || '—'))}</strong>
        </div>
        <div class="detail-card">
          <span>Authority</span>
          <strong><span class="status-pill ${safeText(person.authority || 'member')}">${safeText(person.authority || 'member')}</span></strong>
        </div>
        <div class="detail-card">
          <span>Can converse</span>
          <strong>${person.can_converse ? 'Yes' : '<span class="status-pill blocked">No</span>'}</strong>
        </div>
        <div class="detail-card">
          <span>Can influence memory</span>
          <strong>${person.can_influence ? 'Yes' : 'No'}</strong>
        </div>
        <div class="detail-card">
          <span>Status</span>
          <strong><span class="status-pill ${safeText(person.status)}">${safeText(person.status)}</span></strong>
        </div>
        <div class="detail-card">
          <span>Admin UI access</span>
          <strong>${person.admin ? '<span class="status-pill admin">admin</span>' : '—'}</strong>
        </div>
        <div class="detail-card">
          <span>Created</span>
          <strong>${safeText(formatDate(person.created_at))}</strong>
        </div>
        <div class="detail-card">
          <span>Updated</span>
          <strong>${safeText(formatDate(person.updated_at))}</strong>
        </div>
        <div class="detail-card full">
          <span>Notes</span>
          <strong>${safeText(person.notes || '—')}</strong>
        </div>
      </div>
      <div class="actions detail-actions">
        <a class="button primary" href="/people/${encodeURIComponent(person.person_email)}/edit">Edit person</a>
        <button class="button danger" id="delete-person-button">Delete person</button>
      </div>
    `;

    document.getElementById('delete-person-button')?.addEventListener('click', async () => {
      const ok = window.confirm(`Delete ${person.person_email}?`);
      if (!ok) return;
      const del = await api(`/api/people/${encodeURIComponent(person.person_email)}`, { method: 'DELETE' });
      if (del.ok) {
        window.location.href = '/people';
      } else {
        window.alert('Could not delete that person.');
      }
    });
  }
};

const renderPersonForm = async () => {
  const form = document.getElementById('person-form');
  if (!form) return;

  const title = document.getElementById('person-form-title');
  const lede = document.getElementById('person-form-lede');
  const email = currentEmail();
  const editMode = isEditRoute();
  const emailInput = form.querySelector('input[name="person_email"]');

  if (editMode && title) title.textContent = 'Edit person';
  if (editMode && lede) lede.textContent = 'Update the whitelist entry and save the changes.';

  if (editMode && email) {
    const res = await api(`/api/people/${encodeURIComponent(email)}`);
    if (res.ok) {
      const person = await res.json();
      form.person_name.value = person.person_name || '';
      form.person_email.value = person.person_email || '';
      form.telegram_id.value = person.telegram_id || '';
      form.phone_country_code.value = person.phone_country_code || '';
      form.phone_number.value = person.phone_number || '';
      form.status.value = person.status || 'allowed';
      if (form.authority) form.authority.value = person.authority || 'member';
      form.notes.value = person.notes || '';
      const adminInput = form.querySelector('input[name="admin"]');
      if (adminInput) adminInput.checked = Boolean(person.admin);
      const canConverseInput = form.querySelector('input[name="can_converse"]');
      if (canConverseInput) canConverseInput.checked = person.can_converse !== false;
      const canInfluenceInput = form.querySelector('input[name="can_influence"]');
      if (canInfluenceInput) canInfluenceInput.checked = person.can_influence !== false;
    }
  }

  if (!editMode) {
    form.status.value = 'allowed';
  }

  if (emailInput) {
    emailInput.readOnly = false;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.person_email = String(payload.person_email || '').trim().toLowerCase();
    payload.person_name = String(payload.person_name || '').trim();
    payload.telegram_id = String(payload.telegram_id || '').trim();
    payload.phone_country_code = String(payload.phone_country_code || '').trim();
    payload.phone_number = String(payload.phone_number || '').trim();
    payload.notes = String(payload.notes || '').trim();
    payload.status = String(payload.status || 'allowed');
    payload.admin = Boolean(form.querySelector('input[name="admin"]')?.checked);
    payload.authority = form.authority?.value || 'member';
    payload.can_converse = Boolean(form.querySelector('input[name="can_converse"]')?.checked);
    payload.can_influence = Boolean(form.querySelector('input[name="can_influence"]')?.checked);

    const target = editMode && email ? `/api/people/${encodeURIComponent(email)}` : '/api/people';
    const method = editMode ? 'PATCH' : 'POST';

    const res = await api(target, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      window.alert('Could not save that person.');
      return;
    }

    const saved = await res.json();
    window.location.href = `/people/${encodeURIComponent(saved.person_email)}`;
  });
};

const initLogout = async () => {
  try {
    await fetch('/auth/logout', { method: 'POST' });
  } finally {
    window.location.href = '/';
  }
};

const initLogin = async (user) => {
  const actions = document.querySelector('.actions');
  const warning = document.getElementById('login-warning');
  if (!actions) return;

  try {
    const res = await fetch('/auth/config');
    const config = await res.json();
    const currentHost = window.location.host;
    const redirectHost = (() => {
      try {
        return new URL(config.redirectUri).host;
      } catch {
        return '';
      }
    })();

    if (warning && currentHost && redirectHost && currentHost !== redirectHost) {
      warning.classList.remove('hidden');
      warning.innerHTML = `Google login is currently configured to return to <strong>${safeText(
        redirectHost
      )}</strong>, but this page is running on <strong>${safeText(currentHost)}</strong>. Those must match for sign-in to complete.`;
    }
  } catch {
    if (warning) warning.remove();
  }

  if (!user) return;
  actions.innerHTML = `
    <a class="button primary" href="/dashboard">Go to dashboard</a>
    <a class="button secondary" href="/logout">Logout</a>
  `;
};

const init = async () => {
  const user = await getSession();
  renderHeader(user);
  renderFooter();

  if (page === 'login') {
    await initLogin(user);
  }

  if (page === 'dashboard') {
    // landing page only
  }

  if (page === 'profile') {
    await renderProfilePage();
  }

  if (page === 'people-index') {
    await renderPeopleIndex();
  }

  if (page === 'person-view') {
    await renderPersonView();
  }

  if (page === 'person-form') {
    await renderPersonForm();
  }

  if (page === 'logout') {
    await initLogout();
  }

  if (page === 'integrations') {
    await renderIntegrations();
  }

  if (page === 'inbox') {
    await renderInbox();
  }

  if (page === 'activity') {
    await renderActivityLog();
  }

  if (page === 'activity-detail') {
    await renderActivityDetail();
  }
};

// ---------------------------------------------------------------------------
// Inbox page
// ---------------------------------------------------------------------------

async function renderInbox() {
  const content = document.getElementById('inbox-content');
  const filterBtns = document.querySelectorAll('.filter-btn');
  let currentFilter = 'pending';

  async function load(filter) {
    content.innerHTML = '<p>Loading…</p>';
    const res = await api(`/api/inbox?status=${encodeURIComponent(filter)}`);
    if (!res.ok) { content.innerHTML = '<p>Failed to load.</p>'; return; }
    const rows = await res.json();

    if (!rows.length) {
      content.innerHTML = `<div class="empty-state">No ${filter === 'all' ? '' : filter + ' '}requests.</div>`;
      return;
    }

    const tableRows = rows.map(r => {
      const isPending = r.status === 'pending' || r.status === 'ignored';
      const actions = isPending ? `
        <button class="button primary small" data-action="approve" data-id="${r.id}">Approve</button>
        <button class="button secondary small" data-action="reject" data-id="${r.id}">Reject</button>
        ${r.status === 'pending' ? `<button class="button secondary small" data-action="ignore" data-id="${r.id}">Ignore</button>` : ''}
      ` : '';

      return `<tr id="row-${r.id}">
        <td>
          <div class="sender-name">${safeText(r.from_name || r.from_id)}</div>
          <div class="sender-id">${safeText(r.from_id)}</div>
        </td>
        <td><span class="channel-pill">${safeText(r.channel)}</span></td>
        <td><div class="message-preview">${safeText(r.message_preview)}${r.message_length > 300 ? '…' : ''}</div></td>
        <td>${formatDate(r.created_at)}</td>
        <td><span class="status-badge ${r.status}">${r.status}</span></td>
        <td><div class="row-actions">${actions}</div></td>
      </tr>`;
    }).join('');

    content.innerHTML = `
      <table class="inbox-table">
        <thead><tr>
          <th>Sender</th><th>Channel</th><th>Message</th><th>Time</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody>${tableRows}</tbody>
      </table>`;

    content.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const { action, id } = btn.dataset;
        btn.disabled = true;
        const res = await api(`/api/inbox/${id}/${action}`, { method: 'POST' });
        if (res.ok) {
          await load(currentFilter);
        } else {
          btn.disabled = false;
          alert('Action failed — check the console.');
        }
      });
    });
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      load(currentFilter);
    });
  });

  await load(currentFilter);
}

// ---------------------------------------------------------------------------
// Integrations admin page
// ---------------------------------------------------------------------------

async function renderIntegrations() {
  const grid = document.getElementById('integrations-grid');
  const authContainer = document.getElementById('auth-banner-container');

  const res = await api('/api/integrations');
  if (!res.ok) { grid.innerHTML = '<p>Failed to load integrations.</p>'; return; }
  const data = await res.json();

  // Auth banner
  const auth = data.auth || {};
  let bannerClass = 'disconnected';
  let bannerText = '⚠️ Not connected — James cannot access your Google account.';
  let bannerAction = `<a class="button primary small" href="/auth/google/connect">Connect Google Account</a>`;

  if (auth.connected && !auth.expired) {
    bannerClass = 'connected';
    bannerText = `✅ Connected${auth.updated_at ? ' · Last authorized ' + formatDate(auth.updated_at) : ''}`;
    bannerAction = `
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <a class="button secondary small" href="/auth/google/connect">Re-authorize</a>
        <button class="button secondary small" id="disconnect-btn">Disconnect</button>
      </div>`;
  } else if (auth.connected && auth.expired) {
    bannerClass = 'expired';
    bannerText = '🔄 Token expired — re-authorization needed.';
    bannerAction = `<a class="button primary small" href="/auth/google/connect">Re-authorize</a>`;
  }

  authContainer.innerHTML = `
    <div class="auth-banner ${bannerClass}">
      <span class="auth-status-text">${bannerText}</span>
      ${bannerAction}
    </div>`;

  document.getElementById('disconnect-btn')?.addEventListener('click', async () => {
    await api('/auth/google/disconnect', { method: 'DELETE' });
    await renderIntegrations();
  });

  // Service cards
  grid.innerHTML = data.services.map(svc => {
    let scopePill = '';
    if (!svc.scope) {
      scopePill = `<span class="scope-pill no-scope">No OAuth scope required</span>`;
    } else if (!auth.connected) {
      scopePill = `<span class="scope-pill unauthorized">Not authorized</span>`;
    } else if (svc.scope_authorized) {
      scopePill = `<span class="scope-pill authorized">✓ Authorized</span>`;
    } else {
      scopePill = `<span class="scope-pill unauthorized">⚠ Not in token — re-authorize</span>`;
    }

    return `
      <div class="integration-card ${svc.enabled ? 'enabled' : ''}" id="card-${svc.id}">
        <div class="integration-header">
          <div class="integration-label">
            <span class="integration-icon">${svc.icon}</span>
            <span>${safeText(svc.label)}</span>
          </div>
          <label class="toggle-switch" title="Toggle ${safeText(svc.label)}">
            <input type="checkbox" ${svc.enabled ? 'checked' : ''} data-service="${svc.id}" class="service-toggle" />
            <span class="toggle-track"></span>
          </label>
        </div>
        ${scopePill}
      </div>`;
  }).join('');

  grid.querySelectorAll('.service-toggle').forEach(toggle => {
    toggle.addEventListener('change', async (e) => {
      const serviceId = e.target.dataset.service;
      e.target.disabled = true;
      const res = await api(`/api/integrations/${serviceId}/toggle`, { method: 'POST' });
      if (res.ok) {
        const updated = await res.json();
        const card = document.getElementById(`card-${serviceId}`);
        if (card) card.classList.toggle('enabled', updated.enabled);
        e.target.checked = updated.enabled;
      } else {
        e.target.checked = !e.target.checked;
      }
      e.target.disabled = false;
    });
  });
}

init();

// ---------------------------------------------------------------------------
// Activity Log
// ---------------------------------------------------------------------------

const STATUS_LABELS = {
  ready: 'Ready',
  processing: 'Processing',
  reply_ready: 'Reply ready',
  completed: 'Completed',
  failed_retryable: 'Retrying',
  failed_needs_review: 'Needs review',
  waiting_for_confirmation: 'Waiting',
};

function statusPill(status) {
  const label = STATUS_LABELS[status] || status;
  return `<span class="status-pill ${safeText(status)}">${safeText(label)}</span>`;
}

async function renderActivityLog() {
  const content = document.getElementById('activity-content');
  const filterBtns = document.querySelectorAll('.filter-btn');
  let currentFilter = 'all';

  async function load(filter) {
    content.innerHTML = '<p>Loading…</p>';
    const res = await api(`/api/activity?status=${encodeURIComponent(filter)}&limit=100`);
    if (!res.ok) { content.innerHTML = '<p>Failed to load activity.</p>'; return; }
    const rows = await res.json();

    if (!rows.length) {
      content.innerHTML = '<p class="empty-state">No requests found.</p>';
      return;
    }

    content.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>When</th>
            <th>From</th>
            <th>Message</th>
            <th>Status</th>
            <th>Attempts</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td class="nowrap">${safeText(formatDate(r.created_at))}</td>
              <td class="nowrap">${safeText(r.from_name || r.from_id)}</td>
              <td class="truncate">${safeText(r.message_preview || '—')}</td>
              <td class="nowrap">${statusPill(r.status)}</td>
              <td>${safeText(String(r.attempt_count))}</td>
              <td><a class="button secondary tiny" href="/admin/activity/${safeText(String(r.id))}">Detail</a></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      await load(currentFilter);
    });
  });

  await load(currentFilter);
}

async function renderActivityDetail() {
  const content = document.getElementById('activity-detail-content');
  const id = window.location.pathname.split('/').pop();
  if (!id) { content.innerHTML = '<p>No ID.</p>'; return; }

  const res = await api(`/api/activity/${encodeURIComponent(id)}`);
  if (!res.ok) { content.innerHTML = '<p>Request not found.</p>'; return; }
  const r = await res.json();

  content.innerHTML = `
    <div class="detail-grid">
      <div class="detail-card">
        <span>Status</span>
        <strong>${statusPill(r.status)}</strong>
      </div>
      <div class="detail-card">
        <span>Channel / Sender</span>
        <strong>${safeText(r.channel)} / ${safeText(r.from_name || r.from_id)}</strong>
      </div>
      <div class="detail-card">
        <span>Attempts</span>
        <strong>${safeText(String(r.attempt_count))}</strong>
      </div>
      <div class="detail-card">
        <span>Received</span>
        <strong>${safeText(formatDate(r.requested_at))}</strong>
      </div>
      <div class="detail-card">
        <span>Updated</span>
        <strong>${safeText(formatDate(r.updated_at))}</strong>
      </div>
      <div class="detail-card">
        <span>Request ID</span>
        <strong class="mono">${safeText(r.request_id)}</strong>
      </div>
      ${r.error_summary ? `
      <div class="detail-card full">
        <span>Error</span>
        <strong class="error-text">${safeText(r.error_summary)}</strong>
      </div>` : ''}
      <div class="detail-card full">
        <span>Message</span>
        <pre class="content-pre">${safeText(r.message_text || '—')}</pre>
      </div>
      <div class="detail-card full">
        <span>Reply</span>
        <pre class="content-pre">${safeText(r.reply_text || '—')}</pre>
      </div>
    </div>
  `;
}
