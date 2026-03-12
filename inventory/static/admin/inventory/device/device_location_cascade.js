(function () {
  function $(sel) {
    return document.querySelector(sel);
  }

  function adminBasePath() {
    // /django-admin/inventory/device/add/
    // /django-admin/inventory/device/123/change/
    // -> /django-admin/inventory/device/
    return window.location.pathname
      .replace(/\/add\/?$/, "/")
      .replace(/\/\d+\/change\/?$/, "/");
  }

  function init() {
    const aimagEl = $("#id_aimag");
    const sumEl = $("#id_sumduureg");
    const locEl = $("#id_location");
    if (!aimagEl || !sumEl || !locEl) return;

    function clearSelect(el) {
      el.innerHTML = "";
      const o = document.createElement("option");
      o.value = "";
      o.textContent = "---------";
      el.appendChild(o);
    }

    async function loadSums() {
      clearSelect(sumEl);
      clearSelect(locEl);

      const aimagId = aimagEl.value;
      if (!aimagId) return;

      const url =
        adminBasePath() +
        "sums-by-aimag/?aimag_id=" +
        encodeURIComponent(aimagId);

      const r = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await r.json();

      (data.results || []).forEach((it) => {
        const o = document.createElement("option");
        o.value = it.id;
        o.textContent = it.text;
        sumEl.appendChild(o);
      });

      sumEl.dispatchEvent(new Event("change", { bubbles: true }));
    }

    async function loadLocations() {
      clearSelect(locEl);

      const sumId = sumEl.value;
      if (!sumId) return;

      const url =
        adminBasePath() +
        "locations-by-sum/?sum_id=" +
        encodeURIComponent(sumId);

      const r = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await r.json();

      (data.results || []).forEach((it) => {
        const o = document.createElement("option");
        o.value = it.id;
        o.textContent = it.text;
        locEl.appendChild(o);
      });

      locEl.dispatchEvent(new Event("change", { bubbles: true }));
    }

    aimagEl.addEventListener("change", () => loadSums().catch(() => {}));
    sumEl.addEventListener("change", () => loadLocations().catch(() => {}));

    // initial
    if (aimagEl.value) loadSums().catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", init);
})();
