(function () {
  "use strict";

  const aimagEl = document.getElementById("id_aimag_ref");
  const sumEl = document.getElementById("id_sum_ref");

  if (!aimagEl || !sumEl) return;

  async function fetchJson(url) {
    const r = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  }

  function setOptions(selectEl, items, keepValue) {
    const current = keepValue ? selectEl.value : "";
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

    if (keepValue && current) selectEl.value = current;
  }

  async function loadSums() {
    const aimagId = aimagEl.value;
    if (!aimagId) {
      setOptions(sumEl, [], false);
      return;
    }

    const base =
      window.location_admin_urls?.sumsUrl || "load-sums/";

    const data = await fetchJson(
      `${base}?aimag_id=${encodeURIComponent(aimagId)}`
    );

    setOptions(sumEl, data.results || [], true);
  }

  aimagEl.addEventListener("change", () => {
    loadSums().catch(e => console.warn(e));
  });

  document.addEventListener("DOMContentLoaded", () => {
    loadSums().catch(e => console.warn(e));
  });
})();