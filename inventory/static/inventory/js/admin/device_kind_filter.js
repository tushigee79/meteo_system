(function () {
  "use strict";

  console.log("✅ device_kind_filter.js LOADED");

  function $(id) { return document.getElementById(id); }

  function adminBase() {
    // /django-admin/inventory/device/add/  ->  /django-admin/inventory/device/
    const p = window.location.pathname;
    const m = p.match(/^(.*\/inventory\/device\/)/);
    return m ? m[1] : "/django-admin/inventory/device/";
  }

  function toggleOtherName(kind) {
    const otherEl =
      $("id_other_name") ||
      $("id_other_instrument_name") ||
      $("id_other_instrument");

    // catalog field нэр танайд өөр байж магадгүй: id_catalog_item / id_instrument_catalog / id_catalog
    const catEl =
      $("id_catalog_item") ||
      $("id_instrument_catalog") ||
      $("id_catalog") ||
      $("id_catalog_ref");

    if (!otherEl) return;

    const row =
      otherEl.closest(".form-row") ||
      otherEl.closest(".fieldBox") ||
      otherEl.parentElement;

    const show =
      String(kind || "").toUpperCase() === "OTHER" ||
      (!catEl || !catEl.value);

    if (row) row.style.display = show ? "" : "none";

    if (show) otherEl.setAttribute("required", "required");
    else otherEl.removeAttribute("required");
  }

  function refreshSelect2(el) {
    if (!el || !window.jQuery) return;
    const $el = window.jQuery(el);

    // Jazzmin/select2 marker
    const isSelect2 = $el.hasClass("select2-hidden-accessible") || !!$el.data("select2");
    if (!isSelect2) return;

    try { $el.trigger("change.select2"); } catch (e) {}
    try { $el.select2("destroy"); } catch (e) {}
    try { $el.select2(); } catch (e) {}
  }

  function setOptions(el, items) {
    if (!el) return;

    const prev = el.value;

    el.innerHTML = "";
    el.appendChild(new Option("---------", ""));

    (items || []).forEach(it => {
      el.appendChild(new Option(it.text, String(it.id)));
    });

    // restore if possible
    if (prev && Array.from(el.options).some(o => o.value === String(prev))) el.value = prev;
    else el.value = "";

    refreshSelect2(el);
  }

  async function reloadCatalog() {
  const kindEl = $("id_kind");

  // catalog field нэр танайд өөр байж магадгүй
  const catEl =
    $("id_catalog_item") ||
    $("id_instrument_catalog") ||
    $("id_catalog") ||
    $("id_catalog_ref");

  if (!kindEl || !catEl) {
    console.warn("⚠️ kind/catalog element not found", { kindEl: !!kindEl, catEl: !!catEl });
    return;
  }

  const kind = (kindEl.value || "").trim().toUpperCase();
  console.log("✅ reloadCatalog fired, kind =", kind);

  // kind сонгоогүй бол хоослоод гарна
  if (!kind) {
    setOptions(catEl, []);
    toggleOtherName(kind);
    return;
  }

  const url = adminBase() + "catalog-by-kind/?kind=" + encodeURIComponent(kind);

  let resp;
  try {
    resp = await fetch(url, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
  } catch (e) {
    console.error("catalog-by-kind fetch network error", e);
    return;
  }

  // 302/login эсвэл 403 зэрэг
  if (!resp.ok) {
    console.error("catalog-by-kind HTTP error", resp.status);
    return;
  }

  // HTML ирээд JSON parse унагахыг хамгаална
  const ct = (resp.headers.get("content-type") || "").toLowerCase();
  if (!ct.includes("application/json")) {
    const preview = (await resp.text()).slice(0, 200);
    console.error("catalog-by-kind NOT JSON. content-type=", ct, "preview=", preview);
    return;
  }

  let data;
  try {
    data = await resp.json();
  } catch (e) {
    console.error("catalog-by-kind JSON parse error", e);
    return;
  }

  // {results:[...]} хэлбэрийг хамгаална
  let results = [];
  if (Array.isArray(data)) results = data;
  else if (data && Array.isArray(data.results)) results = data.results;
  else if (data && data.results && typeof data.results === "object") results = Object.values(data.results);

  console.log("✅ catalog loaded:", kind, "items:", (results || []).length);

  setOptions(catEl, results || []);
  toggleOtherName(kind);
}



  // expose for debug
  window.reloadCatalog = reloadCatalog;

  document.addEventListener("DOMContentLoaded", function () {
    const kindEl = $("id_kind");
    const catEl =
      $("id_catalog_item") ||
      $("id_instrument_catalog") ||
      $("id_catalog") ||
      $("id_catalog_ref");

    if (catEl) {
      catEl.addEventListener("change", function () {
        toggleOtherName(kindEl ? kindEl.value : "");
      });
    }

       document.addEventListener("change", function (e) {
      if (e.target && e.target.id === "id_kind") {
        reloadCatalog().catch(console.error);
      }
    }, true);

    // Select2 events (django.jQuery эсвэл window.jQuery)
    const jqA = window.django?.jQuery || null;
    const jqB = window.jQuery || null;

    function bindWith($$) {
      if (!$$) return;
      $$(document).on(
        "select2:select select2:clear",
        "#id_kind",
        () => reloadCatalog().catch(console.error)
      );
    }

    bindWith(jqA);
    if (jqB && jqB !== jqA) bindWith(jqB);

    // initial load (edit form)
    reloadCatalog().catch(console.error);
  });
})();