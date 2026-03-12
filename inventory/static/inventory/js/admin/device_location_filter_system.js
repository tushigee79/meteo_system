(function () {
  "use strict";
  console.log("✅ device_location_filter_system.js LOADED");

  function getJQ() {
    if (window.jQuery) return window.jQuery;
    if (window.django && window.django.jQuery) return window.django.jQuery;
    return null;
  }

  const systemSelect = document.getElementById("id_system");
  const locationSelect = document.getElementById("id_location");
  const kindSelect = document.getElementById("id_kind");

  if (!systemSelect || !locationSelect) {
    console.warn("❌ system/location select NOT found", { systemSelect, locationSelect });
    return;
  }

  function refreshSelect2(el) {
    const jq = getJQ();
    if (!el || !jq) return;
    const $el = jq(el);
    if ($el.data && $el.data("select2")) {
      try { $el.trigger("change.select2"); } catch (e) {}
    }
  }

  function clearSelect(sel) {
    sel.innerHTML = '<option value="">---------</option>';
    refreshSelect2(sel);
  }

  function fillSelect(sel, items) {
    const prev = sel.value;
    clearSelect(sel);

    (items || []).forEach(item => {
      const opt = document.createElement("option");
      opt.value = String(item.id);
      opt.textContent = item.text;
      sel.appendChild(opt);
    });

    // restore if possible
    if (prev && Array.from(sel.options).some(o => o.value === String(prev))) {
      sel.value = prev;
    }
    refreshSelect2(sel);
  }

  function toAbs(baseMaybeRelative) {
    if (/^https?:\/\//i.test(baseMaybeRelative)) return baseMaybeRelative;
    if (baseMaybeRelative.startsWith("/")) return baseMaybeRelative;
    return new URL(baseMaybeRelative, window.location.href).toString();
  }

  async function safeJsonFetch(url) {
    const resp = await fetch(url, { credentials: "same-origin" });
    if (!resp.ok) {
      console.error("Fetch failed:", url, resp.status);
      return null;
    }
    const ct = (resp.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) {
      const preview = (await resp.text()).slice(0, 200);
      console.error("NOT JSON:", url, "ct=", ct, "preview=", preview);
      return null;
    }
    return await resp.json();
  }

  async function loadLocations() {
    const systemId = (systemSelect.value || "").trim();
    const kind = ((kindSelect && kindSelect.value) ? kindSelect.value : "").trim().toUpperCase();

    clearSelect(locationSelect);
    if (!systemId) return;

    const base = window.__deviceLocUrl || "/ajax/location-options/";
    const abs = toAbs(base);

    const qs =
      "system_id=" + encodeURIComponent(systemId) +
      "&kind=" + encodeURIComponent(kind);

    const url = abs + (abs.includes("?") ? "&" : "?") + qs;

    const data = await safeJsonFetch(url);
    if (!data) return;

    fillSelect(locationSelect, data.results || []);
  }

  // normal change
  systemSelect.addEventListener("change", loadLocations);
  if (kindSelect) kindSelect.addEventListener("change", loadLocations);

  // select2 events
  const jq = getJQ();
  if (jq) {
    try {
      jq(systemSelect).on("select2:select select2:clear", loadLocations);
      if (kindSelect) jq(kindSelect).on("select2:select select2:clear", loadLocations);
    } catch (e) {}
  }

  // initial hydrate (edit page)
  if (systemSelect.value) loadLocations();
})();