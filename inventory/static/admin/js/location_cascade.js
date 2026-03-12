(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function clearSelect(selectEl) {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "---------";
    selectEl.appendChild(opt0);
  }

  async function fetchSums(aimagId) {
    if (!window.__deviceSumsUrl) return [];
    const url = new URL(window.__deviceSumsUrl, window.location.origin);
    url.searchParams.set("aimag_id", aimagId || "");

    const res = await fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });

    const data = await res.json();
    return data.sums || data.results || data || [];
  }

  async function reloadSums() {
    const aimagEl = document.getElementById("id_aimag");
    const sumEl = document.getElementById("id_sum");
    if (!aimagEl || !sumEl) return;

    const aimagId = aimagEl.value || "";
    const prev = sumEl.value || "";

    clearSelect(sumEl);
    if (!aimagId) return;

    const rows = await fetchSums(aimagId);

    rows.forEach((it) => {
      const o = document.createElement("option");
      o.value = String(it.id);
      o.textContent = it.name || it.text || ("#" + it.id);
      sumEl.appendChild(o);
    });

    const ok = Array.from(sumEl.options).some((o) => o.value === prev);
    if (ok) sumEl.value = prev;
  }

  ready(function () {
    const aimagEl = document.getElementById("id_aimag");
    const sumEl = document.getElementById("id_sum");
    if (!aimagEl || !sumEl) return;

    aimagEl.addEventListener("change", function () {
      reloadSums().catch(function (err) {
        console.error("reloadSums failed:", err);
      });
    });

    if (aimagEl.value) {
      reloadSums().catch(function (err) {
        console.error("initial reloadSums failed:", err);
      });
    }
  });
})();