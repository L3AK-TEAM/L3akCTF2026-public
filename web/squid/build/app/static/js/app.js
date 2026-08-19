(function () {
  function showAlert(form, kind, msg) {
    var box = form.querySelector('.alert');
    if (!box) { return; }
    box.textContent = msg;
    box.className = 'alert ' + kind + ' show';
  }

  async function postJSON(url, body) {
    var res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(body),
    });
    var data;
    try { data = await res.json(); } catch (e) { data = {}; }
    return { ok: res.ok, status: res.status, data: data };
  }

  function wireForm(selector, handler) {
    var form = document.querySelector(selector);
    if (!form) { return; }
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      handler(form);
    });
  }

  wireForm('#login-form', async function (form) {
    var r = await postJSON('/api/login', {
      username: form.username.value,
      password: form.password.value,
    });
    if (r.ok) { window.location = '/dashboard'; }
    else { showAlert(form, 'err', r.data.error || 'Login failed'); }
  });

  wireForm('#register-form', async function (form) {
    var r = await postJSON('/api/register', {
      username: form.username.value,
      password: form.password.value,
    });
    if (r.ok) { window.location = '/dashboard'; }
    else { showAlert(form, 'err', r.data.error || 'Registration failed'); }
  });

  wireForm('#project-form', async function (form) {
    var r = await postJSON('/api/projects', {
      name: form.name.value,
      language: form.language.value,
    });
    if (r.ok) { window.location = '/projects'; }
    else { showAlert(form, 'err', r.data.error || 'Could not create project'); }
  });

  wireForm('#import-form', async function (form) {
    showAlert(form, 'ok', 'Contacting mirror…');
    var r = await postJSON('/api/manifest', { url: form.url.value });
    if (r.ok) { showAlert(form, 'ok', 'Manifest imported and scheduled.'); }
    else { showAlert(form, 'err', (r.data && r.data.error) || ('Import failed (' + r.status + ')')); }
  });

  document.querySelectorAll('[data-logout]').forEach(function (el) {
    el.addEventListener('click', async function (ev) {
      ev.preventDefault();
      await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
      window.location = '/';
    });
  });
})();
