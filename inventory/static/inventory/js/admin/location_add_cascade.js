// File: D:\meteo_system\inventory\static\inventory\js\admin\location_add_cascade.js
(function () {
  // --- Debug flags (safe) ---
  window.__LOC_ADD_CASCADE_LOADED__ = true;
  console.log("✅ location_add_cascade.js LOADED");

  function $(id) {
    return document.getElementById(id);
  }

  // ✅ /django-admin/inventory/location/add/  ->  /django-admin/inventory/location/
  // ✅ /django-admin/inventory/location/123/change/ -> /django-admin/inventory/location/
  function adminBase() {
    const p = window.location.pathname || "";
    const m = p.match(/^(.*\/inventory\/location\/)/);
    return m ? m[1] : "/django-admin/inventory/location/";
  }

  function setOptions(el, items, keepValue) {
    if (!el) return;

    const prev = keepValue ? (el.value || "") : "";

    // clear
    el.innerHTML = "";
    el.appendChild(new Option("---------", "", true, true));

    // add options
    (items || []).forEach((it) => {
      el.appendChild(new Option(it.text, String(it.id), false, false));
    });

    // restore / reset
    if (keepValue && prev) el.value = prev;
    else el.value = "";

    // select2 refresh (Jazzmin/Select2)
    if (window.jQuery && jQuery.fn.select2) {
      const $el = jQuery(el);
      if ($el.data("select2")) {
        $el.select2("destroy");
        $el.select2({ width: "resolve", allowClear: true });
      }
      $el.trigger("change");
    }
  }

  async function reloadSums(keepValue) {
    const aimagEl = $("id_aimag_ref");
    const sumEl = $("id_sum_ref");

    if (!aimagEl || !sumEl) {
      console.warn("⚠️ location_add_cascade: aimag_ref/sum_ref not found");
      return;
    }

    const aimagId = String(aimagEl.value || "").trim();
    console.log("✅ reloadSums fired, aimag_id =", aimagId);

    if (!aimagId) {
      setOptions(sumEl, [], false);
      return;
    }

    // ✅ matches admin.py endpoint:
    // LocationAdmin.get_urls() -> "sums-by-aimag/"
    // params -> ?aimag_id=<ID>
    const url = adminBase() + "sums-by-aimag/?aimag_id=" + encodeURIComponent(aimagId);

    const r = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });

    if (!r.ok) {
      console.error("❌ sums-by-aimag failed:", r.status, r.statusText);
      setOptions(sumEl, [], false);
      return;
    }

    const data = await r.json();
    const items = data && data.results ? data.results : [];

    console.log("✅ sums loaded:", items.length);
    setOptions(sumEl, items, keepValue);
  }

  // Expose for manual testing in console
  window.reloadLocationSums = reloadSums;

  document.addEventListener("DOMContentLoaded", function () {
    // Prevent map drag/zoom issues if inside admin controls
    // (Not required but harmless)

    // 1) Initial load:
    // - change page: keep existing sum (if any)
    // - add page: will just populate and keep blank
    reloadSums(true).catch(console.error);

    // 2) Native change capture (always works)
    document.addEventListener(
      "change",
      function (e) {
        const t = e.target;
        if (!t) return;
        if (t.id === "id_aimag_ref") reloadSums(false).catch(console.error);
      },
      true
    );

    // 3) Select2 events (Jazzmin/Select2 sometimes doesn't fire native reliably)
    const jqA = window.django?.jQuery || null;
    const jqB = window.jQuery || null;

    function bindWith($$) {
      if (!$$) return;
      $$(document).on(
        "select2:select select2:clear",
        "#id_aimag_ref",
        function () {
          reloadSums(false).catch(console.error);
        }
      );
    }

    bindWith(jqA);
    if (jqB && jqB !== jqA) bindWith(jqB);
  });
})();
