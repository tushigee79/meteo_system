(function () {
  function qs(sel) { return document.querySelector(sel); }

  async function fetchSums(aimagId) {
    const url = "../sums-by-aimag/?aimag_id=" + encodeURIComponent(aimagId || "");
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || [];
  }

  function rebuildSelect(selectEl, items) {
    const current = selectEl.value;
    selectEl.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "---------";
    selectEl.appendChild(empty);

    items.forEach((it) => {
      const opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.name;
      selectEl.appendChild(opt);
    });

    if (current) selectEl.value = current;
  }

  async function onAimagChange() {
    const aimagSel = qs("#id_aimag_ref");
    const sumSel = qs("#id_sum_ref");
    if (!aimagSel || !sumSel) return;

    const aimagId = aimagSel.value;
    const items = await fetchSums(aimagId);
    rebuildSelect(sumSel, items);
  }

  document.addEventListener("DOMContentLoaded", function () {
    const aimagSel = qs("#id_aimag_ref");
    if (aimagSel) {
      aimagSel.addEventListener("change", onAimagChange);
      onAimagChange();
    }
  });
})();