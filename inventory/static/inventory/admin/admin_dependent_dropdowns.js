(function () {
  function qs(sel) { return document.querySelector(sel); }

  function loadSums(aimagId) {
    const sumSelect = qs("#id_sum_ref");
    if (!sumSelect) return;

    sumSelect.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "---------";
    sumSelect.appendChild(opt0);

    if (!aimagId) return;

    fetch(`/inventory/api/sum-duureg/?aimag_id=${encodeURIComponent(aimagId)}`, { credentials: "same-origin" })
      .then(r => r.json())
      .then(data => {
        if (!data || !data.ok) return;
        (data.items || []).forEach(item => {
          const opt = document.createElement("option");
          opt.value = item.id;
          opt.textContent = item.name;
          sumSelect.appendChild(opt);
        });
      })
      .catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    const aimagSelect = qs("#id_aimag_ref");
    const sumSelect = qs("#id_sum_ref");
    if (!aimagSelect || !sumSelect) return;

    // init
    if (aimagSelect.value) loadSums(aimagSelect.value);

    aimagSelect.addEventListener("change", function () {
      loadSums(aimagSelect.value);
      sumSelect.value = "";
    });
  });
})();
