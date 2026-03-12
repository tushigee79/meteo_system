(function () {
  // Enable Aimag -> Sum/District dependent dropdown on the Location changelist.
  // Uses LocationAdmin.get_urls(): "sums-by-aimag/" returning JSON {sums:[{id,name}]}.

  function findSelectByNameHints(hints) {
    const selects = Array.from(document.querySelectorAll('select'));
    for (const s of selects) {
      const name = (s.getAttribute('name') || '').toLowerCase();
      if (!name) continue;
      const ok = hints.every(h => name.includes(h));
      if (ok) return s;
    }
    return null;
  }

  // Common Django admin filter parameter names.
  const aimagSel =
    findSelectByNameHints(['aimag']) ||
    findSelectByNameHints(['aimag_ref']) ||
    document.getElementById('aimagFilter') ||
    document.getElementById('aimag') ||
    null;

  const sumSel =
    findSelectByNameHints(['sum']) ||
    findSelectByNameHints(['sumduureg']) ||
    findSelectByNameHints(['sum_ref']) ||
    document.getElementById('sumFilter') ||
    document.getElementById('sum') ||
    null;

  if (!aimagSel || !sumSel) {
    // Nothing to do.
    return;
  }

  function getEndpointUrl() {
    // Works for /django-admin/inventory/location/
    const base = window.location.pathname.replace(/\/*$/, '/');
    return base + 'sums-by-aimag/';
  }

  async function refreshSums() {
    const aimagId = (aimagSel.value || '').trim();

    // Keep the currently selected sum so we can restore it if it still exists.
    const current = (sumSel.value || '').trim();

    // Clear existing options except the first one.
    const keepFirst = sumSel.options.length ? sumSel.options[0].cloneNode(true) : null;
    sumSel.innerHTML = '';
    if (keepFirst) sumSel.appendChild(keepFirst);

    if (!aimagId) {
      // No aimag selected -> keep default empty list
      return;
    }

    const url = new URL(getEndpointUrl(), window.location.origin);
    url.searchParams.set('aimag_id', aimagId);

    try {
      const res = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!res.ok) return;
      const data = await res.json();
      const sums = Array.isArray(data?.sums) ? data.sums : [];

      for (const item of sums) {
        const opt = document.createElement('option');
        opt.value = String(item.id);
        opt.textContent = String(item.name || item.text || item.label || item.id);
        sumSel.appendChild(opt);
      }

      // Restore selection if still present
      if (current) {
        const exists = Array.from(sumSel.options).some(o => String(o.value) === String(current));
        if (exists) sumSel.value = current;
      }
    } catch (e) {
      // Silent fail
    }
  }

  // Update sums when aimag changes.
  aimagSel.addEventListener('change', function () {
    refreshSums();

    // If these selects live inside a GET form, you may want auto-submit.
    const form = aimagSel.closest('form');
    if (form && form.method && form.method.toLowerCase() === 'get') {
      // Do NOT auto-submit immediately; give the sum list time to update.
      // The user can still press the built-in "Хайлт" button.
    }
  });

  // Initial population.
  refreshSums();
})();
