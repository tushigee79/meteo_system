(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  async function fetchSums(aimagId) {
    const url = new URL(
      window.location.origin + "/django-admin/inventory/location/sums-by-aimag/"
    );
    url.searchParams.set("aimag_id", aimagId || "");
    const res = await fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    return res.json();
  }

  function clearSelect(selectEl) {
    selectEl.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "---------";
    selectEl.appendChild(opt0);
  }

  async function reloadSums() {
    const aimagEl = document.getElementById("id_aimag_ref");
    const sumEl = document.getElementById("id_sum_ref");
    if (!aimagEl || !sumEl) return;

    const aimagId = aimagEl.value || "";
    const prev = sumEl.value || "";

    clearSelect(sumEl);
    if (!aimagId) return;

    const data = await fetchSums(aimagId);

    (data.results || []).forEach((it) => {
      const o = document.createElement("option");
      o.value = String(it.id);
      o.textContent = it.text;
      sumEl.appendChild(o);
    });

    // өмнө нь сонгосон sum байвал буцааж тавина
    const ok = [...sumEl.options].some((o) => o.value === prev);
    if (ok) sumEl.value = prev;
  }

  ready(function () {
    const aimagEl = document.getElementById("id_aimag_ref");
    const sumEl = document.getElementById("id_sum_ref");
    if (!aimagEl || !sumEl) return;

    aimagEl.addEventListener("change", function () {
      reloadSums().catch(function () {});
    });

    // edit form дээр автоматаар ачаалуулах
    if (aimagEl.value) reloadSums().catch(function () {});
  });
})();
