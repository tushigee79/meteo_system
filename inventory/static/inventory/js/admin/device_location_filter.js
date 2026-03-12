/* inventory/js/admin/device_location_filter.js
   Device add/change form: Aimag -> Sum/Duureg -> Location cascade (admin only).
   Depends on window.__DEVICE_LOCATION_FILTER_API_BASE__ (injected via templates/admin/base_site.html).
*/
(function () {
  "use strict";

  // Only run on Device add/change pages
  var path = window.location.pathname || "";
  if (!/\/django-admin\/inventory\/device\/(add|\d+\/change)\/$/.test(path)) return;

  var API_BASE = (window.__DEVICE_LOCATION_FILTER_API_BASE__ || "").toString();
  if (!API_BASE) {
    console.error("[device_location_filter] Missing window.__DEVICE_LOCATION_FILTER_API_BASE__");
    return;
  }
  function apiUrl(p) { return API_BASE + p; }

  function $(id) { return document.getElementById(id); }

  // Field IDs (you already render these in admin.py / form)
  var elAimag = $("id__aimag_filter") || $("id_aimag") || $("id_aimag_ref") || $("id_aimag_ref_id");
  var elSum = $("id__sum_filter") || $("id_sum") || $("id_sum_ref") || $("id_sumduureg") || $("id_sum_ref_id");
  var elLoc = $("id_location") || $("id_location_id");

  if (!elAimag || !elSum || !elLoc) {
    console.warn("[device_location_filter] Required selects not found:", { elAimag: !!elAimag, elSum: !!elSum, elLoc: !!elLoc });
    return;
  }

  function clearSelect(sel, placeholder) {
    while (sel.options.length) sel.remove(0);
    var opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder || "---------";
    sel.appendChild(opt);
    sel.value = "";
  }

  function fillSelect(sel, items, placeholder) {
    clearSelect(sel, placeholder);
    (items || []).forEach(function (it) {
      var opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.text;
      sel.appendChild(opt);
    });
  }

  async function fetchJson(url) {
    var res = await fetch(url, { credentials: "same-origin", headers: { "Accept": "application/json" } });
    var ct = (res.headers.get("content-type") || "");
    if (!res.ok) throw new Error("HTTP " + res.status + " for " + url);
    if (ct.indexOf("application/json") === -1) {
      var t = await res.text();
      throw new Error("Not JSON from " + url + " (content-type=" + ct + "): " + t.slice(0, 40));
    }
    return await res.json();
  }

  async function loadAimagOptions() {
    var data = await fetchJson(apiUrl("aimag-options/"));
    fillSelect(elAimag, data.results || [], "— Аймаг сонгох —");
    if (data.locked_aimag_id) {
      elAimag.value = String(data.locked_aimag_id);
      elAimag.disabled = true;
    }
  }

  async function loadSumsForAimag(aimagId, keepSelected) {
    clearSelect(elSum, "— Сум/Дүүрэг сонгох —");
    clearSelect(elLoc, "— Байршил сонгох —");
    if (!aimagId) return;

    var data = await fetchJson(apiUrl("sums-by-aimag/?aimag_id=" + encodeURIComponent(aimagId)));
    fillSelect(elSum, data.results || [], "— Сум/Дүүрэг сонгох —");

    if (keepSelected && keepSelected.value) {
      var v = keepSelected.value;
      var exists = Array.prototype.some.call(elSum.options, function (o) { return o.value === v; });
      if (exists) elSum.value = v;
    }
  }

  async function loadLocationsForSum(sumId, keepSelected) {
    clearSelect(elLoc, "— Байршил сонгох —");
    if (!sumId) return;

    var data = await fetchJson(apiUrl("locations-by-sum/?sum_id=" + encodeURIComponent(sumId)));
    fillSelect(elLoc, data.results || [], "— Байршил сонгох —");

    if (keepSelected && keepSelected.value) {
      var v = keepSelected.value;
      var exists = Array.prototype.some.call(elLoc.options, function (o) { return o.value === v; });
      if (exists) elLoc.value = v;
    }
  }

  elAimag.addEventListener("change", function () {
    loadSumsForAimag(elAimag.value || "", null).catch(function (e) {
      console.error("[device_location_filter] sums load failed:", e);
    });
  });

  elSum.addEventListener("change", function () {
    loadLocationsForSum(elSum.value || "", null).catch(function (e) {
      console.error("[device_location_filter] locations load failed:", e);
    });
  });

  (async function boot() {
    try {
      var prevSum = { value: elSum.value || "" };
      var prevLoc = { value: elLoc.value || "" };

      await loadAimagOptions();

      await loadSumsForAimag(elAimag.value || "", prevSum);

      await loadLocationsForSum(elSum.value || "", prevLoc);
    } catch (e) {
      console.error("[device_location_filter] boot failed:", e);
    }
  })();
})();
