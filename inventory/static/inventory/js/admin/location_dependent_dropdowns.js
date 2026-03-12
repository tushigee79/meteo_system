(function () {
  function qs(sel) {
    return document.querySelector(sel);
  }

  function clearSelect(selectEl, placeholder) {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder || "---------";
    selectEl.appendChild(opt0);
  }

  function loadSums(aimagId) {
    const sumSelect = qs("#id_sum_ref");
    if (!sumSelect) return;

    clearSelect(sumSelect, "---------");

    if (!aimagId) return;

    fetch(`/inventory/api/sum-duureg/?aimag_id=${encodeURIComponent(aimagId)}`, {
      credentials: "same-origin",
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data || !data.ok) return;

        (data.items || []).forEach((item) => {
          const opt = document.createElement("option");
          opt.value = item.id;
          opt.textContent = item.name;
          sumSelect.appendChild(opt);
        });
      })
      .catch(() => {
        // алдаа гарсан ч admin эвдэхгүй
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const aimagSelect = qs("#id_aimag_ref");
    const sumSelect = qs("#id_sum_ref");

    if (!aimagSelect || !sumSelect) return;

    // Edit form дээр анхны утгаар дүүргэх
    if (aimagSelect.value) {
      loadSums(aimagSelect.value);
    }

    aimagSelect.addEventListener("change", function () {
      loadSums(aimagSelect.value);
      sumSelect.value = "";
    });
  });
})();
