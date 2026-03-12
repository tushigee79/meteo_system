// inventory/static/inventory/admin/dependent_subcategory.js
(function () {
  function $(id) {
    return document.getElementById(id);
  }

  function getFieldIdByName(name) {
    // Django admin default id: id_<fieldname>
    return "id_" + name;
  }

  function setOptions(selectEl, options) {
    if (!selectEl) return;
    const current = selectEl.value;

    // clear
    while (selectEl.firstChild) selectEl.removeChild(selectEl.firstChild);

    // keep empty option
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = "---------";
    selectEl.appendChild(emptyOpt);

    options.forEach((opt) => {
      const o = document.createElement("option");
      o.value = opt;
      o.textContent = opt;
      selectEl.appendChild(o);
    });

    // try restore previous value if still exists
    const still = options.includes(current);
    selectEl.value = still ? current : "";
  }

  async function fetchSubcategories(category) {
    const url = window.__instrumentcatalog_subcat_url;
    if (!url) return [];
    const u = new URL(url, window.location.origin);
    u.searchParams.set("category", category || "");
    const r = await fetch(u.toString(), { credentials: "same-origin" });
    if (!r.ok) return [];
    const data = await r.json();
    return data.options || [];
  }

  async function onCategoryChange() {
    const catEl = $(getFieldIdByName("category"));
    const subEl = $(getFieldIdByName("subcategory"));
    if (!catEl || !subEl) return;

    const category = (catEl.value || "").trim();
    const options = await fetchSubcategories(category);
    setOptions(subEl, options);
  }

  document.addEventListener("DOMContentLoaded", function () {
    const catEl = $(getFieldIdByName("category"));
    const subEl = $(getFieldIdByName("subcategory"));
    if (!catEl || !subEl) return;

    // endpoint URL-г template-ээр inject хийнэ
    // (доорх template хэсгийг үз)
    catEl.addEventListener("change", onCategoryChange);

    // initial load (edit form дээр)
    onCategoryChange();
  });
})();
