/**
 * Shared utilities for the search page modules.
 * Exposed under `window.SearchPage.Utils`.
 */
(function (global) {
  function escapeHtml(str) {
    const el = document.createElement('span');
    el.textContent = str || '';
    return el.innerHTML;
  }

  async function postJson(endpoint, payload, csrfToken) {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken || '',
      },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || 'Request failed');
    }
    return resp;
  }

  function showModal(el) {
    if (!el) return;
    if (global.bootstrap?.Modal) {
      const instance = global.bootstrap.Modal.getInstance(el) || new global.bootstrap.Modal(el);
      instance.show();
      return;
    }
    el.classList.add('show');
    el.style.display = 'block';
    el.removeAttribute('aria-hidden');
  }

  function getResultsRegion(container, regionId) {
    return container?.querySelector(`#${regionId}`) || null;
  }

  function replaceResultsRegion(container, regionId, html) {
    const region = getResultsRegion(container, regionId);
    if (!region) return;
    region.innerHTML = html || '';
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.Utils = {
    escapeHtml,
    postJson,
    showModal,
    getResultsRegion,
    replaceResultsRegion,
  };
})(typeof window !== 'undefined' ? window : this);
