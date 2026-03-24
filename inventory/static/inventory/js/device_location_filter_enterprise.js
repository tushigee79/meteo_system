(function () {
  "use strict";

  function findFieldByLabelText(labelText) {
    const labels = Array.from(document.querySelectorAll("label"));
    const lab = labels.find(l => (l.textContent || "").trim().startsWith(labelText));
    if (!lab) return null;
    const forId = lab.getAttribute("for");
    if (forId) return document.getElementById(forId);
    // fallback: nearest input/select
    return lab.closest(".form-group, .form-row, .row")?.querySelector("input, select, textarea") || null;
  }

  function pick(ids) {
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) return el;
    }
    return null;
  }

  // 1) try by known ids
  let aimagEl = pick(["id_admin_aimag", "id_aimag_ref", "id_aimag"]);
  let sumEl   = pick(["id_admin_sum", "id_sum_ref", "id_sum"]);
  let locEl   = pick(["id_location"]);

  // 2) fallback by label text (Mongolian UI)
  if (!aimagEl) aimagEl = findFieldByLabelText("Аймаг");
  if (!sumEl)   sumEl   = findFieldByLabelText("Сум");
  if (!locEl)   locEl   = findFieldByLabelText("Байршил");

  // loc must be a select
  if (locEl && locEl.tagName !== "SELECT") {
    // if it was some wrapper, try nearest select
    locEl = locEl.closest(".form-group, .form-row, .row")?.querySelector("select") || locEl;
  }

  if (!aimagEl || !sumEl || !locEl) {
    console.warn("device_location_filter: required elements not found", {
      aimag: !!aimagEl,
      sum: !!sumEl,
      loc: !!locEl
    });
    return;
  }

  async function fetchJson(url) {
    const r = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  }

  function setOptions(selectEl, items) {
    selectEl.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "---------";
    selectEl.appendChild(opt0);

    (items || []).forEach(it => {
      const o = document.createElement("option");
      o.value = String(it.id);
      o.textContent = it.name;
      selectEl.appendChild(o);
    });
  }

  async function loadSums() {
    const urls = window.device_admin_urls.loadSums || {};
    if (!urls.loadSums) return;
    if (!aimagEl.value) { setOptions(sumEl, []); setOptions(locEl, []); return; }
    const data = await fetchJson(`${urls.loadSums}?aimag_id=${encodeURIComponent(aimagEl.value)}`);
    setOptions(sumEl, data.results || []);
  }

  async function loadLocations() {
    const urls = window.device_admin_urls.locationOptions || {};
    if (!urls.locationOptions) return;

    const params = new URLSearchParams();
    if (aimagEl.value) params.set("aimag_id", aimagEl.value);
    if (sumEl.value) params.set("sum_id", sumEl.value);

    const data = await fetchJson(`${urls.locationOptions}?${params.toString()}`);
    setOptions(locEl, data.results || []);
  }

  // bind events (works for select + raw_id hidden too)
  let lastA = aimagEl.value;
  let lastS = sumEl.value;

  setInterval(async () => {
    if (aimagEl.value !== lastA) {
      lastA = aimagEl.value;
      await loadSums();
      await loadLocations();
    }
    if (sumEl.value !== lastS) {
      lastS = sumEl.value;
      await loadLocations();
    }
  }, 300);

  // first load
  loadSums().then(loadLocations).catch(e => console.warn(e));
})();