(function () {
  function qs(sel) { return document.querySelector(sel); }

  function baseUrl() {
    // .../location/add/ эсвэл .../location/12/change/ -> .../location/
    const p = window.location.pathname;
    return p.replace(/\/add\/$/, "/").replace(/\/\d+\/change\/$/, "/");
  }

  function loadSums(aimagId) {
    const sumSel = qs("#id_sum_ref");
    if (!sumSel) return;

    const url = baseUrl() + "sum-options/?aimag_id=" + encodeURIComponent(aimagId || "");
    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(r => r.json())
      .then(data => {
        const current = sumSel.value;
        sumSel.innerHTML = '<option value="">---------</option>';
        (data.items || []).forEach(it => {
          const opt = document.createElement("option");
          opt.value = it.id;
          opt.textContent = it.text;
          sumSel.appendChild(opt);
        });
        if (current) sumSel.value = current;
      })
      .catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    const aimagSel = qs("#id_aimag_ref");
    if (!aimagSel) return;

    loadSums(aimagSel.value);
    aimagSel.addEventListener("change", function () {
      loadSums(aimagSel.value);
    });
  });
})();
